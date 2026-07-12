import os
import uuid
from pathlib import Path

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from .models import ImportJob
from .processor import start_background


class IsAdminOrTeacher(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        role = getattr(request.user, 'role', None)
        return role in ('admin', 'teacher') or request.user.is_staff


class StartImportView(APIView):
    """POST /api/exam-import/start/
    Accepts multipart form with exam metadata + image files.
    Saves images to temp folder, starts background processing thread.
    Returns {job_id} immediately.
    """
    parser_classes  = [MultiPartParser, FormParser]
    permission_classes = [IsAdminOrTeacher]

    def post(self, request):
        # Validate required fields
        required = ['exam_title', 'org_name', 'position_name', 'exam_year']
        for field in required:
            if not request.data.get(field):
                return Response({'detail': f'{field} is required'}, status=400)

        images = request.FILES.getlist('images')
        if not images:
            return Response({'detail': 'At least one image file is required'}, status=400)

        api_key = os.environ.get('OPENROUTER_API_KEY', '')
        if not api_key:
            return Response({'detail': 'OPENROUTER_API_KEY not configured on server'}, status=503)

        # Create ImportJob
        job = ImportJob.objects.create(
            exam_title    = request.data['exam_title'].strip(),
            org_name      = request.data['org_name'].strip(),
            position_name = request.data['position_name'].strip(),
            exam_year     = int(request.data['exam_year']),
            subject_name  = request.data.get('subject_name', 'General Knowledge').strip(),
            marks_per_q   = int(request.data.get('marks_per_q', 1)),
            negative_mark = float(request.data.get('negative_mark', 0.25)),
            total_pages   = len(images),
        )

        # Save uploaded images to temp folder
        tmp_dir = Path(settings.MEDIA_ROOT) / 'exam_import_tmp' / str(job.pk)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []
        for img in images:
            ext = Path(img.name).suffix.lower() or '.jpg'
            filename = f'{uuid.uuid4().hex}{ext}'
            dest = tmp_dir / filename
            with open(dest, 'wb') as f:
                for chunk in img.chunks():
                    f.write(chunk)
            image_paths.append(str(dest))

        # Sort by original filename so pages are processed in order
        image_paths.sort()

        model = request.data.get('model', 'google/gemini-2.5-flash')

        # Start background thread
        start_background(job.pk, image_paths, api_key, model)

        return Response({
            'job_id':      job.pk,
            'total_pages': len(images),
            'status':      'processing',
        }, status=202)


class ImportStatusView(APIView):
    """GET /api/exam-import/{job_id}/status/
    Returns current progress of an import job.
    """
    permission_classes = [IsAdminOrTeacher]

    def get(self, request, job_id):
        try:
            job = ImportJob.objects.get(pk=job_id)
        except ImportJob.DoesNotExist:
            return Response({'detail': 'Job not found'}, status=404)

        data = {
            'job_id':          job.pk,
            'status':          job.status,
            'progress':        job.progress_percent,
            'total_pages':     job.total_pages,
            'processed_pages': job.processed_pages,
            'questions_found': job.questions_found,
            'current_page':    job.current_page,
            'error_log':       job.error_log,
        }

        if job.status == 'done' and job.past_exam:
            data['past_exam_id']    = job.past_exam.pk
            data['past_exam_title'] = job.past_exam.title

        return Response(data)


class PastExamListAdminView(APIView):
    """GET /api/exam-import/exams/
    Returns all past exams for admin management.
    """
    permission_classes = [IsAdminOrTeacher]

    def get(self, request):
        from quiz.models import PastExam, PastExamQuestion
        exams = PastExam.objects.select_related(
            'organization', 'position'
        ).order_by('-exam_date')

        data = [{
            'id':              e.pk,
            'title':           e.title,
            'organization':    e.organization.name if e.organization else '',
            'position':        e.position.name if e.position else '',
            'exam_date':       str(e.exam_date),
            'total_questions': e.total_questions,
            'is_published':    e.is_published,
            'negative_mark':   e.negative_mark,
        } for e in exams]

        return Response(data)

    def delete(self, request):
        """DELETE /api/exam-import/exams/?id=X"""
        from quiz.models import PastExam
        exam_id = request.query_params.get('id')
        if not exam_id:
            return Response({'detail': 'id required'}, status=400)
        PastExam.objects.filter(pk=exam_id).delete()
        return Response({'detail': 'Deleted'})


class PastExamDetailView(APIView):
    """GET /api/exam-import/exams/{id}/questions/
    Returns all questions for a past exam (for admin review or student attempt).
    """

    def get(self, request, exam_id):
        from quiz.models import PastExam, PastExamQuestion, QuestionOption

        try:
            exam = PastExam.objects.select_related(
                'organization', 'position', 'exam_type'
            ).get(pk=exam_id)
        except PastExam.DoesNotExist:
            return Response({'detail': 'Exam not found'}, status=404)

        peqs = (PastExamQuestion.objects
                .filter(exam=exam)
                .select_related('question', 'question__subject')
                .order_by('order', 'pk'))

        questions = []
        for peq in peqs:
            q = peq.question
            opts = QuestionOption.objects.filter(question=q)
            show_correct = request.query_params.get('show_answers') == '1'
            questions.append({
                'id':           q.pk,
                'order':        peq.order,
                'text':         q.text,
                'subject':      q.subject.name if q.subject else '',
                'marks':        peq.points,
                'options': [{
                    'id':         o.pk,
                    'text':       o.text,
                    'is_correct': o.is_correct if show_correct else None,
                } for o in opts],
            })

        return Response({
            'id':              exam.pk,
            'title':           exam.title,
            'organization':    exam.organization.name if exam.organization else '',
            'position':        exam.position.name if exam.position else '',
            'exam_date':       str(exam.exam_date),
            'duration':        exam.duration or 60,
            'total_questions': exam.total_questions,
            'pass_mark':       exam.pass_mark,
            'negative_mark':   exam.negative_mark,
            'is_published':    exam.is_published,
            'questions':       questions,
        })


class FixMathNotationView(APIView):
    """POST /api/exam-import/fix-math/ — fixes common math OCR errors in existing questions"""
    permission_classes = [IsAdminOrTeacher]

    def post(self, request):
        import re
        from quiz.models import Question, QuestionOption
        fixed_q = fixed_o = 0

        def fix(text):
            if not text: return text, False
            orig = text
            text = re.sub(r'log(\d)\s*\*\s*', r'log\1 ', text)
            text = re.sub(r'\b2n\s*Cr\b', '²ⁿCᵣ', text)
            return text, text != orig

        for q in Question.objects.all():
            t, changed = fix(q.text)
            if changed: q.text = t; q.save(update_fields=['text']); fixed_q += 1
        for o in QuestionOption.objects.all():
            t, changed = fix(o.text)
            if changed: o.text = t; o.save(update_fields=['text']); fixed_o += 1

        return Response({'questions_fixed': fixed_q, 'options_fixed': fixed_o})


# ── Question Editor Views ──────────────────────────────────────────────────────

class ExamQuestionsAdminView(APIView):
    """GET /api/exam-import/exams/{exam_id}/manage/
    Returns all questions for an exam for admin review/editing.
    Includes full option details, correct answer, status.
    """
    permission_classes = [IsAdminOrTeacher]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, exam_id):
        from quiz.models import PastExam, PastExamQuestion, QuestionOption
        from rest_framework.parsers import JSONParser
        try:
            exam = PastExam.objects.get(pk=exam_id)
        except PastExam.DoesNotExist:
            return Response({'detail': 'Exam not found'}, status=404)

        peqs = (PastExamQuestion.objects
                .filter(exam=exam)
                .select_related('question', 'question__subject')
                .order_by('order', 'pk'))

        questions = []
        for peq in peqs:
            q = peq.question
            opts = QuestionOption.objects.filter(question=q)
            questions.append({
                'peq_id':   peq.pk,
                'order':    peq.order,
                'id':       q.pk,
                'text':     q.text,
                'image':    request.build_absolute_uri(q.image.url) if q.image else None,
                'marks':    peq.points,
                'subject':  q.subject.name if q.subject else '',
                'status':   q.status,
                'options': [{
                    'id':         o.pk,
                    'text':       o.text,
                    'image':      request.build_absolute_uri(o.image.url) if o.image else None,
                    'is_correct': o.is_correct,
                } for o in opts],
            })

        return Response({
            'id':              exam.pk,
            'title':           exam.title,
            'is_published':    exam.is_published,
            'total_questions': exam.total_questions,
            'questions':       questions,
        })


class QuestionEditView(APIView):
    """PATCH /api/exam-import/questions/{question_id}/
    Edit a question's text, image, status.
    """
    permission_classes = [IsAdminOrTeacher]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, question_id):
        from quiz.models import Question
        try:
            q = Question.objects.get(pk=question_id)
        except Question.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)

        if 'text' in request.data:
            q.text = request.data['text']
        if 'status' in request.data:
            q.status = request.data['status']
        if 'image' in request.FILES:
            q.image = request.FILES['image']
        if 'remove_image' in request.data and request.data['remove_image'] == 'true':
            q.image = None

        q.save()
        return Response({
            'id': q.pk, 'text': q.text, 'status': q.status,
            'image': request.build_absolute_uri(q.image.url) if q.image else None,
        })

    def delete(self, request, question_id):
        from quiz.models import Question, PastExamQuestion
        try:
            q = Question.objects.get(pk=question_id)
        except Question.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        PastExamQuestion.objects.filter(question=q).delete()
        q.delete()
        return Response({'detail': 'Deleted'})


class OptionEditView(APIView):
    """PATCH /api/exam-import/options/{option_id}/
    Edit an option's text, image, correct status.
    """
    permission_classes = [IsAdminOrTeacher]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, option_id):
        from quiz.models import QuestionOption
        try:
            opt = QuestionOption.objects.get(pk=option_id)
        except QuestionOption.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)

        if 'text' in request.data:
            opt.text = request.data['text']
        if 'is_correct' in request.data:
            val = request.data['is_correct']
            opt.is_correct = val in ('true', '1', True, 'True')
            # If marking as correct, unmark all others for this question
            if opt.is_correct:
                QuestionOption.objects.filter(
                    question=opt.question
                ).exclude(pk=opt.pk).update(is_correct=False)
        if 'image' in request.FILES:
            opt.image = request.FILES['image']
        if 'remove_image' in request.data and request.data['remove_image'] == 'true':
            opt.image = None

        opt.save()
        return Response({
            'id': opt.pk, 'text': opt.text, 'is_correct': opt.is_correct,
            'image': request.build_absolute_uri(opt.image.url) if opt.image else None,
        })


class ExamPublishView(APIView):
    """POST /api/exam-import/exams/{exam_id}/publish/
    Toggle exam published status.
    """
    permission_classes = [IsAdminOrTeacher]

    def post(self, request, exam_id):
        from quiz.models import PastExam
        try:
            exam = PastExam.objects.get(pk=exam_id)
        except PastExam.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)

        action = request.data.get('action', 'publish')
        exam.is_published = (action == 'publish')
        exam.save(update_fields=['is_published'])

        return Response({
            'id':           exam.pk,
            'is_published': exam.is_published,
            'message':      'প্রকাশিত হয়েছে' if exam.is_published else 'অপ্রকাশিত হয়েছে',
        })
