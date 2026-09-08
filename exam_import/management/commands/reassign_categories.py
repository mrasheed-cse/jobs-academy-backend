"""
Management command to reassign categories for existing questions using Gemini.
Usage: python manage.py reassign_categories --exam_id=25
       python manage.py reassign_categories --all
"""
import time
import requests
import os
from django.core.management.base import BaseCommand
from quiz.models import PastExam, PastExamQuestion, Question, Subject, Category


def get_category_from_gemini(question_text, options, api_key):
    """Ask Gemini to categorize a question."""
    if not question_text:
        return None

    opts_str = ' | '.join([f"{k}: {v}" for k, v in options.items() if v])
    prompt = f"""Categorize this Bengali exam question into one of these categories:
বাংলা ভাষা ও সাহিত্য, ইংরেজি ভাষা ও সাহিত্য, গণিত, সাধারণ জ্ঞান,
বাংলাদেশ বিষয়াবলী, আন্তর্জাতিক বিষয়াবলী, বিজ্ঞান ও প্রযুক্তি,
কম্পিউটার ও তথ্যপ্রযুক্তি, ভূগোল, পদার্থবিজ্ঞান, রসায়ন, জীববিজ্ঞান

Question: {question_text}
Options: {opts_str}

Reply with ONLY the category name in Bengali, nothing else."""

    resp = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': 'google/gemini-2.5-flash',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 50,
            'temperature': 0.1,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content'].strip()


class Command(BaseCommand):
    help = 'Reassign categories for existing questions using Gemini'

    def add_arguments(self, parser):
        parser.add_argument('--exam_id', type=int, help='Specific exam ID')
        parser.add_argument('--all', action='store_true', help='All exams')

    def handle(self, *args, **options):
        api_key = os.environ.get('OPENROUTER_API_KEY', '')
        if not api_key:
            from django.conf import settings
            api_key = getattr(settings, 'OPENROUTER_API_KEY', '')

        if options['exam_id']:
            exams = PastExam.objects.filter(pk=options['exam_id'])
        elif options['all']:
            exams = PastExam.objects.all()
        else:
            self.stdout.write('Provide --exam_id or --all')
            return

        total_updated = 0
        for exam in exams:
            self.stdout.write(f'Processing: {exam.title[:50]}')
            peqs = PastExamQuestion.objects.filter(exam=exam).select_related(
                'question', 'question__subject'
            ).prefetch_related('question__options')

            for peq in peqs:
                q = peq.question
                if not q.text:
                    continue
                opts = {(o.text or '')[:2]: o.text or '' for o in q.options.all() if o.text}
                try:
                    category = get_category_from_gemini(q.text, opts, api_key)
                    if category:
                        subj, _ = Subject.objects.get_or_create(name=category)
                        cat, _ = Category.objects.get_or_create(name=category)
                        q.subject = subj
                        q.category = cat
                        q.save(update_fields=['subject', 'category'])
                        total_updated += 1
                        self.stdout.write(f'  Q{peq.order}: {category}')
                    time.sleep(0.5)  # avoid rate limits
                except Exception as e:
                    self.stdout.write(f'  Q{peq.order} error: {e}')

        self.stdout.write(f'Done. Updated {total_updated} questions.')
