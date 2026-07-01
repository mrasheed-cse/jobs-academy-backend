from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Max
from .models import *
from .serializers import *
from rest_framework.permissions import IsAuthenticated
class BestAttemptsView(APIView):
    def get(self, request, *args, **kwargs):
        exam_id = request.GET.get('exam_id')
        if not exam_id:
            return Response({'error': 'Exam ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        best_attempts_data = (
            ExamAttempt.objects.filter(exam_id=exam_id)
            .values('user_id', 'user__username')
            .annotate(
                max_score=Max('total_correct_answers'),
                best_attempt_id=Max('id')
            )
            .order_by('-max_score')
        )

        # Fetch full details of the best attempts
        best_attempt_ids = [attempt['best_attempt_id'] for attempt in best_attempts_data]
        best_attempts = ExamAttempt.objects.filter(id__in=best_attempt_ids).select_related('user', 'exam')

        # Serialize the data
        serializer = ExamAttemptSerializer(best_attempts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserAttemptsView(APIView):
    def get(self, request, *args, **kwargs):
        exam_id = request.GET.get('exam_id')
        user_id = request.GET.get('user_id')

        if not exam_id or not user_id:
            return Response(
                {'error': 'Exam ID and User ID are required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        attempts = ExamAttempt.objects.filter(exam_id=exam_id, user_id=user_id).order_by('-attempt_time')
        attempt_data = attempts.values(
            'id',
            'attempt_time',
            'total_questions',
            'answered',
            'total_correct_answers',
            'wrong_answers',
            'pass_mark'
        )

        return Response(list(attempt_data), status=status.HTTP_200_OK)


## past attempts
class BestPastExamAttemptsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        past_exam_id = self.request.query_params.get('past_exam_id')
        if not past_exam_id:
            return Response({'error': 'Past Exam ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Get best scores per user for the given past_exam
        best_attempts_data = (
            PastExamAttempt.objects.filter(past_exam_id=past_exam_id)
            .values('user_id', 'user__username')
            .annotate(
                max_score=Max('score'),
                best_attempt_id=Max('id')  # If scores tie, pick latest by ID
            )
            .order_by('-max_score')
        )
        
        

        # Step 2: Fetch the full best attempts by their IDs
        best_attempt_ids = [attempt['best_attempt_id'] for attempt in best_attempts_data]
        best_attempts = PastExamAttempt.objects.filter(id__in=best_attempt_ids).select_related('user', 'past_exam')

        # Step 3: Serialize and return
        serializer = PastExamAttemptSerializer(best_attempts, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
class UserPastExamAttemptsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        past_exam_id = self.request.query_params.get('past_exam_id')
        user_id = self.request.query_params.get('user_id')

        if not past_exam_id or not user_id:
            return Response(
                {'error': 'Past Exam ID and User ID are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        attempts = PastExamAttempt.objects.filter(
            past_exam_id=past_exam_id,
            user_id=user_id
        ).order_by('-attempt_time')

        attempt_data = list(attempts.values(
            'id',
            'attempt_time',
            'total_questions',
            'answered_questions',
            'correct_answers',
            'wrong_answers',
            'score'
        ))

        # Get pass_mark from the first matching PastExamAttempt object
        pass_mark = None
        if attempts.exists():
            pass_mark = attempts.first().past_exam.pass_mark

        # Add pass_mark to each attempt
        for attempt in attempt_data:
            attempt['pass_mark'] = pass_mark

        return Response(attempt_data, status=status.HTTP_200_OK)
    
    

class PastExamLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, exam_id, *args, **kwargs):
        past_exam_id = exam_id

        if not past_exam_id:
            return Response({'error': 'Past Exam ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get best attempt per user
        best_attempts_data = (
            PastExamAttempt.objects.filter(past_exam_id=past_exam_id)
            .values('user_id', 'user__username')
            .annotate(
                top_score=Max('score'),
                best_attempt_id=Max('id')  # used to fetch full attempt data
            )
            .order_by('-top_score')
        )
        print("hellow world")
        # Fetch full data of best attempts
        best_attempt_ids = [entry['best_attempt_id'] for entry in best_attempts_data]
        best_attempts = PastExamAttempt.objects.filter(id__in=best_attempt_ids).select_related('user')

        leaderboard = []
        for rank, attempt in enumerate(best_attempts.order_by('-score'), start=1):
            leaderboard.append({
                'user_id': attempt.user.id,
                'user': attempt.user.username,
                'total_questions': attempt.total_questions,
                'score': attempt.score,
            })

        return Response(leaderboard, status=status.HTTP_200_OK)
