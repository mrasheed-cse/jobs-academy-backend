"""
Views for AI-powered word import workflow.
"""
import threading
import openpyxl
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import WordImportJob, Word, Sense, BanglaMeaning, Definition, ExampleSentence
from .word_importer import process_word_import
import os


def IsAdminOrTeacher(user):
    return user.is_staff or user.is_superuser


class WordImportStartView(APIView):
    """POST /api/word-import/start/
    Upload Excel file with words, start AI generation in background.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not IsAdminOrTeacher(request.user):
            return Response({'detail': 'Permission denied'}, status=403)

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided'}, status=400)

        # Read words from Excel
        try:
            wb = openpyxl.load_workbook(BytesIO(file.read()))
            ws = wb.active
            words = []
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if cell and str(cell).strip():
                        words.append(str(cell).strip())
            # Remove header if it looks like one
            if words and words[0].lower() in ('word', 'words', 'english word', 'english'):
                words = words[1:]
        except Exception as e:
            return Response({'detail': f'Excel read error: {e}'}, status=400)

        if not words:
            return Response({'detail': 'No words found in file'}, status=400)

        # Create job
        job = WordImportJob.objects.create(total_words=len(words))

        # Start background thread
        api_key = os.environ.get('OPENROUTER_API_KEY', '')
        thread = threading.Thread(
            target=process_word_import,
            args=(job.pk, words, api_key),
            daemon=True
        )
        thread.start()

        return Response({
            'job_id': job.pk,
            'total_words': len(words),
            'words_preview': words[:5],
        })


class WordImportStatusView(APIView):
    """GET /api/word-import/{job_id}/status/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_object_or_404(WordImportJob, pk=job_id)
        words_to_process = job.total_words - job.skipped_words
        progress = round((job.processed_words / words_to_process * 100)) if words_to_process > 0 else 100

        return Response({
            'job_id':           job.pk,
            'status':           job.status,
            'total_attempted':  job.total_words,
            'skipped_duplicates': job.skipped_words,
            'words_to_process': words_to_process,
            'processed_words':  job.processed_words,
            'failed_words':     job.failed_words,
            'progress_percent': progress,
            'current_word':     job.current_word,
            'skipped_list':     job.skipped_log.split(', ') if job.skipped_log else [],
        })


class PendingWordsView(APIView):
    """GET /api/word-import/pending/
    List all pending words for admin review.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not IsAdminOrTeacher(request.user):
            return Response({'detail': 'Permission denied'}, status=403)

        words = Word.objects.filter(status='pending').prefetch_related(
            'senses__bangla_meanings',
            'senses__definitions',
            'senses__examples__translations',
        ).order_by('text')

        data = []
        for w in words:
            sense = w.senses.first()
            data.append({
                'id': w.pk,
                'text': w.text,
                'phonetic_uk': w.phonetic_uk,
                'phonetic_us': w.phonetic_us,
                'part_of_speech': w.part_of_speech.name if w.part_of_speech else '',
                'word_level': w.word_level,
                'status': w.status,
                'short_definition': sense.short_definition if sense else '',
                'bangla_meaning': sense.bangla_meanings.first().meaning if sense and sense.bangla_meanings.exists() else '',
                'synonyms': sense.synonyms if sense else '',
                'example_sentence': sense.examples.first().sentence if sense and sense.examples.exists() else '',
                'example_bangla': sense.examples.first().translations.first().translated_text if sense and sense.examples.exists() and sense.examples.first().translations.exists() else '',
            })

        return Response({'words': data, 'total': len(data)})


class WordApproveView(APIView):
    """POST /api/word-import/words/{word_id}/approve/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, word_id):
        if not IsAdminOrTeacher(request.user):
            return Response({'detail': 'Permission denied'}, status=403)
        word = get_object_or_404(Word, pk=word_id)
        word.status = 'approved'
        word.save(update_fields=['status'])
        return Response({'id': word.pk, 'status': 'approved'})


class WordRejectView(APIView):
    """POST /api/word-import/words/{word_id}/reject/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, word_id):
        if not IsAdminOrTeacher(request.user):
            return Response({'detail': 'Permission denied'}, status=403)
        word = get_object_or_404(Word, pk=word_id)
        word.status = 'rejected'
        word.save(update_fields=['status'])
        return Response({'id': word.pk, 'status': 'rejected'})


class WordBulkApproveView(APIView):
    """POST /api/word-import/bulk-approve/
    Body: {"word_ids": [1,2,3]} or {"all": true}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not IsAdminOrTeacher(request.user):
            return Response({'detail': 'Permission denied'}, status=403)

        if request.data.get('all'):
            count = Word.objects.filter(status='pending').update(status='approved')
        else:
            ids = request.data.get('word_ids', [])
            count = Word.objects.filter(pk__in=ids, status='pending').update(status='approved')

        return Response({'approved': count})


class WordEditView(APIView):
    """PATCH /api/word-import/words/{word_id}/
    Edit word fields: phonetic, short_definition, bangla_meaning, example, example_bangla
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, word_id):
        if not IsAdminOrTeacher(request.user):
            return Response({'detail': 'Permission denied'}, status=403)

        word = get_object_or_404(Word, pk=word_id)
        d = request.data

        if 'phonetic_uk' in d:
            word.phonetic_uk = d['phonetic_uk']
        if 'phonetic_us' in d:
            word.phonetic_us = d['phonetic_us']
        if 'word_level' in d:
            word.word_level = d['word_level']
        word.save()

        sense = word.senses.first()
        if sense:
            if 'short_definition' in d:
                sense.short_definition = d['short_definition']
            if 'synonyms' in d:
                sense.synonyms = d['synonyms']
            sense.save()

            bm = sense.bangla_meanings.first()
            if bm and 'bangla_meaning' in d:
                bm.meaning = d['bangla_meaning']
                bm.save()

            ex = sense.examples.first()
            if ex:
                if 'example_sentence' in d:
                    ex.sentence = d['example_sentence']
                    ex.save()
                t = ex.translations.first()
                if t and 'example_bangla' in d:
                    t.translated_text = d['example_bangla']
                    t.save()

        return Response({'id': word.pk, 'status': 'updated'})
