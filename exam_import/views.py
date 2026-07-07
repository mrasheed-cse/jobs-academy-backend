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
