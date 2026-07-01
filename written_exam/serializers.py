from rest_framework import serializers
from .models import *
from quiz.models import Subject
from quiz.serializers import *
# Subject Serializer (Assuming minimal usage)
from quiz.models import Subject, ExamType, Organization, Department, Position
from users.serializers import *
class SubWrittenQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubWrittenQuestion
        fields = [
            'id', 'parent_question', 'text', 'image', 'answer_text',
            'answer_image', 'is_image', 'number', 'marks', 'created_at',
            'explanation_text', 'explanation_image'  # Add these two fields
        ]
        read_only_fields = ['created_at']

class PassageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passage
        fields = [
            'id', 'title', 'text', 'image', 'is_image', 'subject', 'created_at'
        ]
        read_only_fields = ['created_at']

class WrittenQuestionSerializer(serializers.ModelSerializer):
    # Nested serializer for sub_questions if you want them in the WrittenQuestion detail view
    sub_questions = SubWrittenQuestionSerializer(many=True, read_only=True)
    # Nested serializer for passage if you want passage details
    passage = PassageSerializer(read_only=True)
    
    # To display just the ID of the subject, or use SubjectSerializer if full details are needed
    subject = SubjectSerializer(read_only=True) 

    class Meta:
        model = WrittenQuestion
        fields = [
            'id', 'written_exam', 'subject', 'passage', 'question_text',
            'question_image', 'answer_text', 'answer_image', 'is_image',
            'question_number', 'has_sub_questions', 'marks', 'created_at',
            'explanation_text', 'explanation_image', # Add these two fields
            'sub_questions' # Include the nested sub-questions
        ]
        read_only_fields = ['created_at']


class WrittenExamSerializer(serializers.ModelSerializer):
    # Nested serializer for questions if you want them in the WrittenExam detail view
    questions = WrittenQuestionSerializer(many=True, read_only=True)
    subject = SubjectSerializer(read_only=True) # Display subject details

    class Meta:
        model = WrittenExam
        fields = [
            'id', 'root_exam', 'subject', 'total_questions', 'total_marks',
            'created_at', 'updated_at', 'questions' # Include the nested questions
        ]
        read_only_fields = ['created_at', 'updated_at']

class RootExamSerializer(serializers.ModelSerializer):
    # Nested serializers for related objects to display their details
    exam_type = ExamTypeSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    subjects = SubjectSerializer(many=True, read_only=True)
    organization = OrganizationSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    position = PositionSerializer(read_only=True)
    past_exam = PastExamListSerializer(read_only=True)
    
    # Nested serializer for related WrittenExams if you want them in the RootExam detail view
    written_exams = WrittenExamSerializer(many=True, read_only=True)

    class Meta:
        model = RootExam
        fields = [
            'id', 'title', 'description', 'exam_mode', 'exam_type',
            'exam_date', 'created_at', 'updated_at', 'created_by',
            'subjects', 'organization', 'department', 'position', 'past_exam',
            'written_exams' # Include the nested written exams
        ]
        read_only_fields = ['created_at', 'updated_at']
