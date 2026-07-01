from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import *
from .serializers import StatusSerializer, ExamSerializer
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminOrReadOnly, IsAdmin
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
User = get_user_model()


class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    # permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def perform_create(self, serializer):
        exam = get_object_or_404(Exam, pk=self.request.data.get('exam_id'))
        status_obj = serializer.save(exam=exam, status='draft')  # Exam starts in draft mode
        return Response(StatusSerializer(status_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrReadOnly])
    def draft_exams(self, request):
        """Retrieve draft exams for the current user."""
        user = request.user
        draft_exams = Status.objects.filter(status='draft', exam__created_by=user)
        serializer = self.get_serializer(draft_exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrReadOnly], authentication_classes = [JWTAuthentication])
    def submit_to_admin(self, request, pk=None):
        """Submit exam to admin for review"""
        status_obj = self.get_object()
        if status_obj.status == 'draft':
            status_obj.status = 'submitted_to_admin'
            status_obj.save()
            return Response({'detail': 'Exam submitted to admin for review'}, status=status.HTTP_200_OK)
        return Response({'detail': 'Exam must be in draft status to submit to admin'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def submitted_to_admin(self, request):
        print("hello")
        """List all exams with status 'submitted_to_admin'"""
        submitted_exams = Status.objects.filter(status='submitted_to_admin')
        serializer = self.get_serializer(submitted_exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrReadOnly], authentication_classes = [JWTAuthentication])
    def assign_reviewer(self, request, pk=None):
        print(request)
        """Admin assigns a teacher (reviewer) to review the exam"""
        status_obj = self.get_object()
        if status_obj.status == 'submitted_to_admin':
            reviewer_id = request.data.get('reviewer_id')
            reviewer = get_object_or_404(User, pk=reviewer_id)

            # Assign reviewer and change status to under_review
            status_obj.status = 'under_review'
            status_obj.reviewed_by = reviewer
            status_obj.save()

            return Response({'detail': f'Exam assigned to {reviewer.username} for review'}, status=status.HTTP_200_OK)
        return Response({'detail': 'Exam must be submitted to admin to assign a reviewer'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_assigned_exams(self, request):
        """Teacher views the exams assigned to them for review."""
        if request.user.role != 'teacher':
            return Response({'detail': 'Only teachers can access this page'}, status=status.HTTP_403_FORBIDDEN)

        # Fetch exams where the current user is assigned as the reviewer
        assigned_exams = Status.objects.filter(reviewed_by=request.user, status='under_review')
        serializer = self.get_serializer(assigned_exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], authentication_classes = [JWTAuthentication])
    def submit_to_admin_from_reviewer(self, request, pk=None):
        """Reviewer submits the reviewed exam back to the admin, including question remarks."""
        # Fetch the status object using pk (which is the status ID)
        status_obj = self.get_object()  # Assuming you have a StatusModel
        # print(status_obj.status)
        # Check if the exam is under review and the reviewer is the current user
        if status_obj.status == 'under_review' and status_obj.reviewed_by == request.user:
            exam_obj = status_obj.exam  # Assuming the status model has a ForeignKey to the Exam model
            # print("hellow worold")
            count = 0
            # Process questions data
            questions_data = request.data.get('questions', [])
            for question_data in questions_data:
                count +=1 
                # print(count)
                question_id = question_data.get('question_id')

                status_value = question_data.get('status')
                remarks = question_data.get('remarks', '')

                # Fetch the question by ID within the exam
                try:
                    question = Question.objects.get(id=question_id)
                    
                except Question.DoesNotExist:
                    return Response({'detail': f'Question with ID {question_id} not found.'}, status=status.HTTP_400_BAD_REQUEST)

                # Update question status and remarks
                question.status = status_value
                question.remarks = remarks
                question.save()
            
            # Update the exam status to 'reviewed'
            status_obj.status = 'reviewed'
            status_obj.save()

            return Response({'detail': 'Reviewed exam submitted to admin'}, status=status.HTTP_200_OK)

        return Response({'detail': 'Only the assigned reviewer can submit the exam'}, status=status.HTTP_400_BAD_REQUEST)

    # @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    # def return_to_creator(self, request, pk=None):
    #     """Return exam to the creator for modifications"""
    #     status_obj = self.get_object()
    #     if status_obj.status == 'under_review':
    #         status_obj.status = 'returned_to_creator'
    #         status_obj.save()
    #         return Response({'detail': 'Exam returned to creator for modifications'}, status=status.HTTP_200_OK)
    #     return Response({'detail': 'Exam must be under review to return to creator'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def publish_exam(self, request, pk=None):
        """Admin publishes the exam"""
        status_obj = self.get_object()
        if status_obj.status == 'reviewed':
            status_obj.status = 'published'
            status_obj.save()

            # Publish the exam
            exam = status_obj.exam
            exam.published = True  # Assuming you have a 'published' field in your Exam model
            exam.save()

            return Response({'detail': 'Exam has been published'}, status=status.HTTP_200_OK)
        return Response({'detail': 'Exam must be reviewed before publishing'}, status=status.HTTP_400_BAD_REQUEST)

    
    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def reviewed_exams(self, request):
        """Get all exams that have been reviewed"""
        reviewed_statuses = Status.objects.filter(status='reviewed')  # Filter by 'reviewed' status
        serializer = self.get_serializer(reviewed_statuses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def all_status(self, request):
        """List all exam statuses for admin or teacher"""
        statuses = Status.objects.all()
        serializer = self.get_serializer(statuses, many=True)
        return Response(serializer.data)

