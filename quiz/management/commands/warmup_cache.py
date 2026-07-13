from django.core.management.base import BaseCommand
from django.core.cache import cache
from quiz.models import PastExam, PastExamQuestion

class Command(BaseCommand):
    help = 'Warm up question cache for all published exams'

    def handle(self, *args, **kwargs):
        exams = PastExam.objects.filter(is_published=True)
        for exam in exams:
            cache_key = f'past_exam_questions_{exam.pk}'
            if cache.get(cache_key):
                self.stdout.write(f'Skip exam {exam.pk} (already cached)')
                continue
            peqs = (PastExamQuestion.objects
                    .filter(exam=exam)
                    .select_related('question')
                    .prefetch_related('question__options')
                    .order_by('order', 'pk'))
            questions = []
            for peq in peqs:
                q = peq.question
                questions.append({
                    'id': q.pk, 'text': q.text or '',
                    'image': q.image.url if q.image else None,
                    'marks': peq.points or 1,
                    'options': [{'id': o.pk, 'text': o.text, 'image': None}
                                for o in q.options.all()],
                })
            data = {
                'id': exam.pk, 'title': exam.title,
                'duration': exam.duration or 60,
                'negative_mark': exam.negative_mark,
                'total_questions': len(questions),
                'questions': questions,
            }
            cache.set(cache_key, data, 3600)
            self.stdout.write(f'Cached exam {exam.pk}: {len(questions)} questions')
        self.stdout.write('Cache warmup complete')
