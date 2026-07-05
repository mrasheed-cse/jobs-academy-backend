"""
Django management command: import_exam_images
=============================================
Scans exam question paper images using Google Gemini Vision API
(FREE tier: 1500 requests/day, no credit card required) and imports
questions into the database automatically.

Handles: MCQ, mathematical equations, physics formulas,
         chemistry reactions, Bengali text, mixed content.

Setup (one time):
    1. Go to https://aistudio.google.com/app/apikey
    2. Click "Create API Key" — free, no credit card
    3. Add to .env: GEMINI_API_KEY=your-key-here
    4. pip install google-generativeai pillow

Usage:
    python manage.py import_exam_images \\
        --images /path/to/exam/images/ \\
        --exam "Bangladesh Bank AD 2023" \\
        --org "Bangladesh Bank" \\
        --position "Assistant Director" \\
        --year 2023 \\
        --subject "General Knowledge" \\
        --marks 1 \\
        --dry-run

Options:
    --dry-run       Preview without saving to DB
    --delay 2       Seconds between API calls (default 2, free tier safe)
    --negative 0.25 Negative marks per wrong answer
    --model         Gemini model (default: gemini-1.5-flash — fastest & free)
"""

import os
import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Import exam questions from images using Gemini Vision (free)'

    def add_arguments(self, parser):
        parser.add_argument('--images',   required=True, help='Folder with exam images')
        parser.add_argument('--exam',     required=True, help='Exam title')
        parser.add_argument('--org',      required=True, help='Organization name')
        parser.add_argument('--position', required=True, help='Position name')
        parser.add_argument('--year',     required=True, type=int)
        parser.add_argument('--subject',  default='General Knowledge')
        parser.add_argument('--marks',    default=1, type=int)
        parser.add_argument('--negative', default=0.25, type=float)
        parser.add_argument('--dry-run',  action='store_true')
        parser.add_argument('--delay',    default=2.0, type=float,
                            help='Delay between API calls in seconds (default 2)')
        parser.add_argument('--model',    default='gemini-1.5-flash',
                            help='Gemini model name (default: gemini-1.5-flash)')

    def handle(self, *args, **options):
        images_dir = Path(options['images'])
        if not images_dir.exists():
            raise CommandError(f'Directory not found: {images_dir}')

        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            raise CommandError(
                'GEMINI_API_KEY not set.\n'
                '  1. Go to https://aistudio.google.com/app/apikey\n'
                '  2. Create a free API key (no credit card)\n'
                '  3. Add GEMINI_API_KEY=your-key to your .env file\n'
                '  4. Restart daphne: systemctl restart daphne.service'
            )

        exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
        image_files = sorted(
            f for f in images_dir.iterdir()
            if f.is_file() and f.suffix.lower() in exts
        )

        if not image_files:
            raise CommandError(f'No image files found in {images_dir}')

        self.stdout.write(self.style.SUCCESS(
            f'\n{"─"*60}\n'
            f'  Exam Import Engine — Gemini Vision (Free)\n'
            f'{"─"*60}\n'
            f'  Images:   {len(image_files)}\n'
            f'  Exam:     {options["exam"]}\n'
            f'  Model:    {options["model"]}\n'
            f'  Dry run:  {"YES (no DB changes)" if options["dry_run"] else "NO (will save)"}\n'
            f'{"─"*60}\n'
        ))

        all_questions = []
        errors = []

        for i, img_path in enumerate(image_files, 1):
            self.stdout.write(
                f'[{i:3}/{len(image_files)}] {img_path.name} ... ',
                ending=''
            )
            self.stdout.flush()

            try:
                questions = self.scan_image(img_path, api_key, options['model'])
                self.stdout.write(
                    self.style.SUCCESS(f'{len(questions)} question(s)')
                )
                for q in questions:
                    preview = q['text'][:65] + ('…' if len(q['text']) > 65 else '')
                    correct = f'  → Correct: {q["correct_option"]}' if q.get('correct_option') else ''
                    self.stdout.write(f'        Q{q["number"]}: {preview}{correct}')
                all_questions.extend(questions)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ERROR: {e}'))
                errors.append((img_path.name, str(e)))

            # Respect free tier rate limits (15 requests/min for Flash)
            if i < len(image_files):
                time.sleep(options['delay'])

        self.stdout.write(f'\n{"─"*60}')
        self.stdout.write(f'Total questions extracted: {len(all_questions)}')
        if errors:
            self.stdout.write(self.style.ERROR(f'Errors on {len(errors)} image(s):'))
            for name, err in errors:
                self.stdout.write(self.style.ERROR(f'  {name}: {err}'))

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n─── DRY RUN: NOT saving to database ───'))
            self._print_questions(all_questions)
            return

        if not all_questions:
            self.stdout.write(self.style.ERROR('\nNo questions to import.'))
            return

        self.stdout.write('\nSaving to database...')
        stats = self.save_to_db(all_questions, options)
        self.stdout.write(self.style.SUCCESS(
            f'\n{"─"*60}\n'
            f'  ✓ Import Complete!\n'
            f'  Exam:              {stats["exam"]}\n'
            f'  Questions created: {stats["q_new"]}\n'
            f'  Questions skipped: {stats["q_skip"]} (duplicates)\n'
            f'  Options created:   {stats["opts"]}\n'
            f'{"─"*60}\n'
        ))

    # ── Gemini Vision scan ────────────────────────────────────────────────────

    def scan_image(self, img_path: Path, api_key: str, model_name: str) -> list:
        try:
            import google.generativeai as genai
        except ImportError:
            raise CommandError(
                'google-generativeai not installed.\n'
                'Run: pip install google-generativeai pillow'
            )

        from PIL import Image

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        img = Image.open(img_path)

        prompt = """You are an expert exam question extractor with perfect accuracy.

Extract ALL multiple-choice questions from this exam paper image.

CRITICAL RULES — follow exactly:
1. Extract EVERY question visible. Do not skip any.
2. Preserve text 100% accurately including Bengali script.
3. Mathematical notation:
   - Superscripts: x² → x^2, x³ → x^3
   - Subscripts: H₂O → H2O, CO₂ → CO2, H₂SO₄ → H2SO4
   - Square root: √x → sqrt(x), √(a+b) → sqrt(a+b)
   - Fractions: ½ → 1/2, ¾ → 3/4
   - Greek letters: π → pi, α → alpha, β → beta, θ → theta, λ → lambda, σ → sigma, Σ → Sigma, Δ → Delta, μ → mu, Ω → Omega
   - Operators: × → *, ÷ → /, ≥ → >=, ≤ → <=, ≠ → !=, ≈ → approx, ∞ → infinity
   - Integrals: ∫f(x)dx → integral(f(x)dx)
   - Chemistry arrows: → → ->, ⇌ → <->
4. If correct answer is marked (circled/ticked/highlighted/bold): record it.
5. If diagram present: write [Diagram: brief description] in question text.
6. Options may be A/B/C/D or ক/খ/গ/ঘ or i/ii/iii/iv — always output as A/B/C/D.
7. Include partial questions if visible.

Output ONLY this JSON structure, nothing else:
{
  "questions": [
    {
      "number": 1,
      "text": "Complete question text here",
      "options": {
        "A": "first option",
        "B": "second option",
        "C": "third option",
        "D": "fourth option"
      },
      "correct_option": "C",
      "subject_hint": "math/physics/chemistry/biology/english/bangla/gk/ict"
    }
  ]
}

correct_option is null if not marked. subject_hint helps categorize.
If no questions visible: {"questions": []}"""

        response = model.generate_content([prompt, img])
        raw = response.text.strip()

        # Strip markdown fences if present
        if '```' in raw:
            for part in raw.split('```'):
                part = part.strip().lstrip('json').strip()
                if part.startswith('{'):
                    raw = part
                    break

        # Find JSON object in response
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError(f'No JSON found in response: {raw[:200]}')
        raw = raw[start:end]

        data = json.loads(raw)
        questions = []
        for q in data.get('questions', []):
            text = (q.get('text') or '').strip()
            if not text:
                continue
            # Normalize options — handle missing options gracefully
            opts = {}
            raw_opts = q.get('options', {})
            if isinstance(raw_opts, dict):
                for k, v in raw_opts.items():
                    key = k.strip().upper()
                    if key in ('A', 'B', 'C', 'D') and v:
                        opts[key] = str(v).strip()
            questions.append({
                'number':         q.get('number', len(questions) + 1),
                'text':           text,
                'options':        opts,
                'correct_option': (q.get('correct_option') or '').strip().upper() or None,
                'subject_hint':   q.get('subject_hint', ''),
            })

        return questions

    # ── Database save ─────────────────────────────────────────────────────────

    @transaction.atomic
    def save_to_db(self, questions: list, opts: dict) -> dict:
        from quiz.models import (
            Question, QuestionOption, Category, Subject,
            Organization, Position, ExamType,
            PastExam, PastExamQuestion,
        )

        org,       _ = Organization.objects.get_or_create(name=opts['org'])
        position,  _ = Position.objects.get_or_create(name=opts['position'])
        exam_type, _ = ExamType.objects.get_or_create(name='MCQ')

        # Subject map from Gemini hints
        subject_name_map = {
            'math':      'Mathematics',
            'physics':   'Physics',
            'chemistry': 'Chemistry',
            'biology':   'Biology',
            'english':   'English',
            'bangla':    'Bengali',
            'gk':        'General Knowledge',
            'ict':       'ICT',
        }
        default_subject, _ = Subject.objects.get_or_create(name=opts['subject'])
        default_category, _ = Category.objects.get_or_create(name=opts['subject'])

        # PastExam
        past_exam, created = PastExam.objects.get_or_create(
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
        if not created:
            self.stdout.write(self.style.WARNING(
                f'  PastExam "{opts["exam"]}" exists — appending questions'
            ))

        q_new = q_skip = opt_count = 0

        for q_data in questions:
            text = q_data['text']

            # Deduplicate
            if Question.objects.filter(text=text).exists():
                self.stdout.write(
                    self.style.WARNING(f'  Duplicate skip: {text[:55]}…')
                )
                q_skip += 1
                continue

            # Determine subject from Gemini hint
            hint = q_data.get('subject_hint', '').lower()
            subj_name = subject_name_map.get(hint, opts['subject'])
            subject,  _ = Subject.objects.get_or_create(name=subj_name)
            category, _ = Category.objects.get_or_create(name=subj_name)

            # Create Question
            question = Question.objects.create(
                text=text,
                marks=opts['marks'],
                category=category,
                subject=subject,
                difficulty_level=2,
                status='approved',
            )
            q_new += 1

            # Create options
            for key in ('A', 'B', 'C', 'D'):
                opt_text = q_data['options'].get(key, '').strip()
                if not opt_text:
                    continue
                QuestionOption.objects.create(
                    question=question,
                    text=opt_text,
                    is_correct=(key == q_data.get('correct_option')),
                )
                opt_count += 1

            # Link to PastExam
            PastExamQuestion.objects.create(
                exam=past_exam,
                question=question,
                order=q_data['number'],
                points=float(opts['marks']),
            )

        # Update total count
        total = PastExamQuestion.objects.filter(exam=past_exam).count()
        past_exam.total_questions = total
        past_exam.save(update_fields=['total_questions'])

        return {
            'exam':   opts['exam'],
            'q_new':  q_new,
            'q_skip': q_skip,
            'opts':   opt_count,
        }

    def _print_questions(self, questions):
        for q in questions:
            self.stdout.write(f'\n  Q{q["number"]}: {q["text"]}')
            for k in ('A', 'B', 'C', 'D'):
                v = q['options'].get(k)
                if v:
                    mark = '✓' if k == q.get('correct_option') else ' '
                    self.stdout.write(f'    [{mark}] {k}. {v}')
            if q.get('subject_hint'):
                self.stdout.write(f'    Subject: {q["subject_hint"]}')
