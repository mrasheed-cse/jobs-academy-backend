"""
Background processor — runs in a daemon thread.
Processes uploaded exam images one by one, updates ImportJob progress,
and saves extracted questions to the database.
"""

import os
import json
import base64
import threading
from pathlib import Path
from datetime import datetime

import requests
from django.db import transaction


def process_job(job_id: int, image_paths: list[str], api_key: str, model: str):
    """Entry point — called in a background thread."""
    # Import inside function to avoid app-not-ready issues
    from exam_import.models import ImportJob

    job = ImportJob.objects.get(pk=job_id)
    job.status = 'processing'
    job.total_pages = len(image_paths)
    job.save(update_fields=['status', 'total_pages'])

    errors = []
    all_questions = []

    for i, img_path in enumerate(image_paths):
        filename = Path(img_path).name
        job.current_page = filename
        job.save(update_fields=['current_page'])

        try:
            questions = scan_image(img_path, api_key, model)
            all_questions.extend(questions)
            job.questions_found = len(all_questions)
            job.processed_pages = i + 1
            job.save(update_fields=['questions_found', 'processed_pages'])
        except Exception as e:
            errors.append(f'{filename}: {e}')
            job.processed_pages = i + 1
            job.error_log = '\n'.join(errors)
            job.save(update_fields=['processed_pages', 'error_log'])

    # Save to DB
    try:
        opts = {
            'exam':     job.exam_title,
            'org':      job.org_name,
            'position': job.position_name,
            'year':     job.exam_year,
            'subject':  job.subject_name,
            'marks':    job.marks_per_q,
            'negative': job.negative_mark,
        }
        past_exam = save_questions(all_questions, opts)
        job.past_exam = past_exam
        job.status = 'done'
    except Exception as e:
        errors.append(f'DB save error: {e}')
        job.error_log = '\n'.join(errors)
        job.status = 'failed'

    job.finished_at = datetime.now()
    job.save(update_fields=['past_exam', 'status', 'finished_at', 'error_log'])

    # Cleanup temp images
    for img_path in image_paths:
        try:
            os.remove(img_path)
        except Exception:
            pass


def scan_image(img_path: str, api_key: str, model: str) -> list:
    ext_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
               '.png': 'image/png', '.webp': 'image/webp', '.bmp': 'image/png'}
    mime = ext_map.get(Path(img_path).suffix.lower(), 'image/jpeg')

    with open(img_path, 'rb') as f:
        img_b64 = base64.standard_b64encode(f.read()).decode()

    prompt = """Extract ALL multiple-choice questions from this exam paper image.

RULES:
1. Extract every question — do not skip any.
2. Preserve Bengali text 100% exactly as written.
3. MATHEMATICAL NOTATION — read with extreme care:

   FRACTIONS — Read mixed numbers carefully:
   - "1 2/3" (one and two-thirds) → write: 1 2/3
   - "2 4/7" (two and four-sevenths) → write: 2 4/7
   - "3 3/8" (three and three-eighths) → write: 3 3/8
   - "5/6" means five-sixths → write: 5/6

   DEGREE SYMBOL — NEVER drop the ° symbol:
   - ১৮০° → write: ১৮০°, ২৭০° → write: ২৭০°, 360° → write: 360°

   LOGARITHMS — Read the base carefully:
   - log₂√2 = log BASE 2 of √2 → write: log₂(√2), NOT "log2 * √2"
   - The subscript after log is the BASE, not a multiplier

   COMBINATIONS/PERMUTATIONS:
   - ²ⁿCᵣ = ²ⁿCᵣ₊₂ → write with Unicode superscript/subscript exactly

   OTHER: x² → x², H₂O → H₂O, √x → √x, π → π, × → ×, ÷ → ÷

4. If correct answer is marked (ans.A / circled / ticked / bold) — record it.
5. Options a/b/c/d or ক/খ/গ/ঘ → always output as A/B/C/D.
6. For diagrams write [Diagram: description] in question text.
7. CRITICAL: Every option MUST have text. Never return null or empty string.

Output ONLY this JSON, no explanation, no markdown:
{"questions":[{"number":1,"text":"question text","options":{"A":"opt a","B":"opt b","C":"opt c","D":"opt d"},"correct_option":"C","subject_hint":"gk"}]}
subject_hint: math/physics/chemistry/biology/english/bangla/gk/ict
correct_option is null if not marked.
If no questions: {"questions":[]}"""

    resp = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://jobs.academy',
            'X-Title': 'Jobs Academy',
        },
        json={
            'model': model,
            'max_tokens': 4096,
            'messages': [{'role': 'user', 'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{img_b64}'}},
                {'type': 'text', 'text': prompt},
            ]}],
        },
        timeout=90,
    )

    if resp.status_code != 200:
        raise ValueError(f'API {resp.status_code}: {resp.text[:200]}')

    raw = resp.json()['choices'][0]['message']['content'].strip()
    if '```' in raw:
        for part in raw.split('```'):
            part = part.strip().lstrip('json').strip()
            if part.startswith('{'):
                raw = part
                break

    s, e = raw.find('{'), raw.rfind('}') + 1
    if s == -1:
        raise ValueError(f'No JSON in response: {raw[:200]}')

    data = json.loads(raw[s:e])
    questions = []
    for q in data.get('questions', []):
        text = (q.get('text') or '').strip()
        if not text:
            continue
        opts = {
            k.strip().upper(): str(v).strip()
            for k, v in (q.get('options') or {}).items()
            if k.strip().upper() in ('A', 'B', 'C', 'D') and v
        }
        questions.append({
            'number':         q.get('number', len(questions) + 1),
            'text':           text,
            'options':        opts,
            'correct_option': (q.get('correct_option') or '').strip().upper() or None,
            'subject_hint':   q.get('subject_hint', 'gk'),
        })
    return questions


@transaction.atomic
def save_questions(questions: list, opts: dict):
    from quiz.models import (
        Question, QuestionOption, Category, Subject,
        Organization, Position, ExamType,
        PastExam, PastExamQuestion,
    )

    org,       _ = Organization.objects.get_or_create(name=opts['org'])
    position,  _ = Position.objects.get_or_create(name=opts['position'])
    exam_type, _ = ExamType.objects.get_or_create(name='MCQ')

    subject_map = {
        'math': 'Mathematics', 'physics': 'Physics', 'chemistry': 'Chemistry',
        'biology': 'Biology', 'english': 'English', 'bangla': 'Bengali',
        'gk': 'General Knowledge', 'ict': 'ICT',
    }

    past_exam, _ = PastExam.objects.get_or_create(
        title=opts['exam'],
        defaults={
            'organization':    org,
            'position':        position,
            'exam_type':       exam_type,
            'exam_date':       f"{opts['year']}-01-01",
            'duration':        60,
            'total_questions': len(questions),
            'pass_mark':       50,
            'negative_mark':   opts['negative'],
            'is_published':    True,
        },
    )

    for q_data in questions:
        text = q_data['text']
        if Question.objects.filter(text=text).exists():
            continue

        subj_name = subject_map.get(q_data.get('subject_hint', 'gk').lower(), opts['subject'])
        subj, _ = Subject.objects.get_or_create(name=subj_name)
        cat,  _ = Category.objects.get_or_create(name=subj_name)

        question = Question.objects.create(
            text=text, marks=opts['marks'], category=cat,
            subject=subj, difficulty_level=2, status='approved',
        )

        for key in ('A', 'B', 'C', 'D'):
            opt_text = q_data['options'].get(key, '').strip()
            if not opt_text:
                continue
            QuestionOption.objects.create(
                question=question, text=opt_text,
                is_correct=(key == q_data.get('correct_option')),
            )

        PastExamQuestion.objects.create(
            exam=past_exam, question=question,
            order=q_data['number'], points=float(opts['marks']),
        )

    past_exam.total_questions = PastExamQuestion.objects.filter(exam=past_exam).count()
    past_exam.save(update_fields=['total_questions'])
    return past_exam


def start_background(job_id: int, image_paths: list, api_key: str, model: str):
    t = threading.Thread(
        target=process_job,
        args=(job_id, image_paths, api_key, model),
        daemon=True,
    )
    t.start()
