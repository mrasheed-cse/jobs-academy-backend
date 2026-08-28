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
        # Sort by extracted question number
        all_questions.sort(key=lambda q: int(q.get('number', 0)) if str(q.get('number', 0)).isdigit() else 0)
        # Renumber sequentially to fix any gaps/duplicates from extraction
        for i, q in enumerate(all_questions, 1):
            if not str(q.get('number', 0)).isdigit() or int(q.get('number', 0)) == 0:
                q['number'] = i
        # Format explanations with Gemini for proper math notation
        for q in all_questions:
            if q.get('explanation'):
                q['explanation'] = format_explanation(q['explanation'], api_key)
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
    """Send image directly to Gemini via OpenRouter for OCR + question extraction."""
    ext_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
               '.png': 'image/png', '.webp': 'image/webp', '.bmp': 'image/png'}
    mime = ext_map.get(Path(img_path).suffix.lower(), 'image/jpeg')
    with open(img_path, 'rb') as f:
        img_b64 = base64.standard_b64encode(f.read()).decode()

    prompt = """Extract ALL multiple-choice questions from this exam paper image.
RULES:
1. Extract EVERY question — do not skip any, including বানান/spelling questions.
2. Use the EXACT question number printed in the image — do NOT renumber.
3. Preserve Bengali text 100% exactly as written.
4. MATHEMATICAL NOTATION: x² → x², H₂O → H₂O, √x → √x, ১৮০° → ১৮০°
5. Options ক/খ/গ/ঘ or a/b/c/d → always output as A/B/C/D.
6. CORRECT ANSWER DETECTION — look carefully for these:
   a) A separate answer column on the RIGHT SIDE of the page showing "১০ ঘ" or "10 D" format
   b) Circled or ticked option in the question
   c) Bold or underlined option
   d) "Ans:" or "উত্তর:" label next to an option
   Map the answer: ক=A, খ=B, গ=C, ঘ=D
7. EXPLANATION — extract the explanation text (ব্যাখ্যা) for each question if present.
   The explanation usually appears below the options, labeled ব্যাখ্যা or in a box.
   Extract it exactly as written in Bengali.
8. Every option MUST have text. Never return null or empty string.
9. CATEGORY — identify the exact subject/topic category from the question content.
   বাংলা ভাষা ও সাহিত্য, ইংরেজি ভাষা ও সাহিত্য, গণিত, সাধারণ জ্ঞান,
   বাংলাদেশ বিষয়াবলী, আন্তর্জাতিক বিষয়াবলী, বিজ্ঞান ও প্রযুক্তি,
   কম্পিউটার ও তথ্যপ্রযুক্তি, ভূগোল, পদার্থবিজ্ঞান, রসায়ন, জীববিজ্ঞান
   If unsure, use the closest matching category.
Output ONLY this JSON, no explanation, no markdown:
{"questions":[{"number":14,"text":"question text","options":{"A":"opt a","B":"opt b","C":"opt c","D":"opt d"},"correct_option":"A","subject_hint":"বাংলা ভাষা ও সাহিত্য","explanation":"ব্যাখ্যা টেক্সট এখানে"}]}
If no explanation exists for a question, use null for explanation field.
If no questions found: {"questions":[]}"""

    for attempt in range(3):
        try:
            resp = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://jobs.academy',
                },
                json={
                    'model': model,
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{img_b64}'}},
                            {'type': 'text', 'text': prompt},
                        ],
                    }],
                    'max_tokens': 4096,
                },
                timeout=120,
            )
            if resp.status_code == 429:
                import time; time.sleep(15); continue
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content'].strip()
            content = content.replace('```json', '').replace('```', '').strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                content = content[start:end]
            data = json.loads(content)
            return data.get('questions', [])
        except Exception as e:
            if attempt < 2:
                import time; time.sleep(10); continue
            raise
    return []


def format_explanation(raw_explanation: str, api_key: str) -> str:
    """Post-process raw explanation text with Gemini for proper math formatting."""
    if not raw_explanation or len(raw_explanation.strip()) < 10:
        return raw_explanation

    prompt = f"""This is a raw Bengali explanation extracted from a scanned exam paper.
Format it properly with clear mathematical notation.

RULES:
1. Keep Bengali text exactly as is
2. Format fractions clearly: ১/২, ৩/৪
3. Format powers/exponents: ২², ৩³
4. Format equations on separate lines
5. Use × for multiplication, ÷ for division
6. Replace .: with ∴
7. Make it readable and well-structured
8. Do NOT add any new information

RAW TEXT:
{raw_explanation}

Return ONLY the formatted text, nothing else."""

    try:
        resp = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'google/gemini-2.5-flash',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 500,
                'temperature': 0.1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except Exception:
        return raw_explanation  # fallback to raw if formatting fails


def save_questions(questions: list, opts: dict):
    from quiz.models import (
        Question, QuestionOption, Category, Subject,
        Organization, Position, ExamType,
        PastExam, PastExamQuestion,
    )

    org,       _ = Organization.objects.get_or_create(name=opts['org'])
    position,  _ = Position.objects.get_or_create(name=opts['position'])
    exam_type, _ = ExamType.objects.get_or_create(name=opts['org'])

    subject_map = {
        'math':        'গণিত',
        'physics':     'পদার্থবিজ্ঞান',
        'chemistry':   'রসায়ন',
        'biology':     'জীববিজ্ঞান',
        'english':     'ইংরেজি ভাষা ও সাহিত্য',
        'bangla':      'বাংলা ভাষা ও সাহিত্য',
        'gk':          'সাধারণ জ্ঞান',
        'ict':         'কম্পিউটার ও তথ্যপ্রযুক্তি',
        'geography':   'ভূগোল',
        'mathematics': 'গণিত',
        'bengali':     'বাংলা ভাষা ও সাহিত্য',
        'general knowledge': 'সাধারণ জ্ঞান',
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

    for seq_num, q_data in enumerate(questions, 1):
        text = q_data['text']
        if not text or not text.strip():
            continue
        raw_hint = q_data.get('subject_hint', '') or ''
        # Try legacy code first, then use the hint directly as category name
        subj_name = subject_map.get(raw_hint.lower(), raw_hint) or opts['subject'] or 'সাধারণ জ্ঞান'
        subj, _ = Subject.objects.get_or_create(name=subj_name)
        cat,  _ = Category.objects.get_or_create(name=subj_name)
        # Get or create the question (don't skip existing ones)
        question, created = Question.objects.get_or_create(
            text=text,
            defaults={'marks': opts['marks'], 'category': cat,
                      'subject': subj, 'difficulty_level': 2, 'status': 'approved'}
        )
        if created:
            for key in ('A', 'B', 'C', 'D'):
                opt_text = q_data['options'].get(key, '').strip()
                if not opt_text:
                    continue
                QuestionOption.objects.create(
                    question=question, text=opt_text,
                    is_correct=(key == q_data.get('correct_option')),
                )
        # Always link to this past exam (avoid duplicate links)
        if not PastExamQuestion.objects.filter(exam=past_exam, question=question).exists():
            PastExamQuestion.objects.create(
                exam=past_exam, question=question,
                order=q_data.get('number', 0),
                points=float(opts['marks']),
                explanation=q_data.get('explanation') or '',
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
