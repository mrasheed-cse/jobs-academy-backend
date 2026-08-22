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


def ocr_extract_text(img_path: str, ocr_key: str) -> str:
    """Step 1: Extract raw text from image using OCR.Space."""
    with open(img_path, 'rb') as f:
        img_data = f.read()
    ext = Path(img_path).suffix.lower()
    mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.webp': 'image/webp', '.bmp': 'image/png'}
    mime = mime_map.get(ext, 'image/jpeg')
    files = {'file': (Path(img_path).name, img_data, mime)}
    data = {
        'apikey': ocr_key,
        'language': 'eng',
        'isOverlayRequired': 'false',
        'filetype': ext.lstrip('.').upper(),
        'detectOrientation': 'true',
        'scale': 'true',
        'OCREngine': '2',
    }
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.post('https://api.ocr.space/parse/image',
                                 files=files, data=data, timeout=60)
            if resp.status_code in (502, 503, 429):
                _time.sleep(15 * (attempt + 1))
                continue
            resp.raise_for_status()
            result = resp.json()
            if result.get('IsErroredOnProcessing'):
                raise Exception(f"OCR error: {result.get('ErrorMessage')}")
            parsed = result.get('ParsedResults', [])
            if not parsed:
                return ''
            return parsed[0].get('ParsedText', '')
        except requests.exceptions.RequestException as e:
            if attempt < 2:
                _time.sleep(15)
                continue
            raise
    return ''


def parse_text_to_questions(raw_text: str, llm_key: str, model: str) -> list:
    """Step 2: Parse raw OCR text into structured questions using LLM."""
    if not raw_text.strip():
        return []
    prompt = f"""The following is raw OCR text extracted from a Bengali exam paper.
Extract ALL multiple-choice questions from this text.

RULES:
1. Extract every question — do not skip any.
2. Preserve Bengali text 100% exactly as written.
3. Options ক/খ/গ/ঘ or a/b/c/d → output as A/B/C/D.
4. If correct answer is marked → record it, otherwise null.
5. Every option MUST have text. Never return null or empty string.
6. subject_hint: math/physics/chemistry/biology/english/bangla/gk/ict

Output ONLY this JSON, no explanation, no markdown:
{{"questions":[{{"number":1,"text":"question text","options":{{"A":"opt a","B":"opt b","C":"opt c","D":"opt d"}},"correct_option":"C","subject_hint":"gk"}}]}}

If no questions found: {{"questions":[]}}

RAW TEXT:
{raw_text[:4000]}"""

    for attempt in range(3):
        try:
            resp = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {llm_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 4000,
                    'temperature': 0.1,
                },
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
            if 'choices' not in result:
                import time; time.sleep(10); continue
            content = result['choices'][0]['message']['content']
            if not content or not content.strip():
                import time; time.sleep(10); continue
            content = content.strip()
            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            # Find JSON object
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                content = content[start:end]
            data = json.loads(content)
            return data.get('questions', [])
        except (json.JSONDecodeError, KeyError):
            import time; time.sleep(10)
            continue
        except Exception:
            raise
    return []


def scan_image(img_path: str, api_key: str, model: str) -> list:
    """Two-step OCR: OCR.Space for text extraction + LLM for parsing."""
    import os
    ocr_key = os.environ.get('OCR_SPACE_API_KEY', 'K87965802988957')
    llm_key = api_key  # OpenRouter key for LLM parsing

    # Step 1: Extract text with OCR.Space
    raw_text = ocr_extract_text(img_path, ocr_key)

    # Step 2: Parse text into structured questions
    questions = parse_text_to_questions(raw_text, llm_key, model)
    return questions


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
