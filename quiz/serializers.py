from rest_framework import serializers
from .models import *
# from users.models import User
from collections import Counter
from django.contrib.auth import get_user_model
User = get_user_model()


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']
        
class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'image', 'is_correct', 'question']

    def create(self, validated_data):
        # Here we ensure that the question is set properly from the validated_data
        return QuestionOption.objects.create(**validated_data)


    def validate(self, data):
        if not data.get("text") and not data.get("image"):
            raise serializers.ValidationError("An option must have either text or an image.")
        return data

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class ExamTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamType
        fields = ["id", "name"]

class QuestionUsageSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)

    class Meta:
        model = QuestionUsage
        fields = ['id', 'question', 'question_text', 'exam', 'year']
        read_only_fields = ['question_text']



class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all(), write_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), write_only=True)
    category_name = serializers.SerializerMethodField()
    question_usage_details = serializers.SerializerMethodField()  # Renamed method
    created_by = serializers.StringRelatedField(read_only=True)
    reviewed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'text', 'image', 'marks', 'exam',
            'options', 'status', 'remarks', 'category', 'created_by', 'category_name',
            'difficulty_level', 'time_limit', 'reviewed_by', 'updated_at',
            'created_at', 'subject', 'question_usage_details'  # Updated field name
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category and obj.category.name else None

    def get_question_usage_details(self, obj):
        usages = obj.usages.select_related('past_exam')  # Optimize query to fetch related PastExam
        details = []
        for usage in usages:
            past_exam_title = usage.past_exam.title if usage.past_exam else "External Exam"  # Handle cases without PastExam
            details.append(f"{past_exam_title} ({usage.year})")
        return ", ".join(details) if details else "No uses"

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        question = Question.objects.create(**validated_data)
        for option_data in options_data:
            QuestionOption.objects.create(question=question, **option_data)
        return question

    # def validate(self, data):
    #     text, image = data.get('text'), data.get('image')
    #     explanation = data.get('explanation')
    #     explanation_image = data.get('explanation_image')

    #     if bool(text) == bool(image):
    #         raise serializers.ValidationError("Provide either 'text' or 'image', not both.")

    #     if explanation and explanation_image:
    #         raise serializers.ValidationError("Provide either 'explanation' (text) or 'explanation_image', not both.")

    #     return data




class ExamAttemptSerializer(serializers.ModelSerializer):
    score = serializers.ReadOnlyField()
    is_passed = serializers.ReadOnlyField()
    user_name = serializers.CharField(source='user.username', read_only=True)  # User's name
    total_questions = serializers.IntegerField(source='exam.total_questions', read_only=True)  # Total questions in the exam
    pass_mark = serializers.IntegerField(source='exam.pass_mark', read_only=True)  # Total questions in the exam
    exam_title = serializers.StringRelatedField(source='exam.title', read_only=True) #

    class Meta:
        model = ExamAttempt
        fields = [
            'id', 'user', 'user_name', 'exam', 'total_questions', 'answered', 'pass_mark',
            'wrong_answers', 'total_correct_answers', 'score', 'is_passed', 'attempt_time', 'score', 'exam_title'
        ]
        read_only_fields = ['attempt_time', 'score', 'is_passed']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user_name'] = instance.user.username
        representation['total_questions'] = instance.exam.total_questions
        representation['pass_mark'] = instance.exam.pass_mark
        representation['exam_title'] = instance.exam.title
        
        
        return representation



class ExamCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamCategory
        fields = '__all__'
        
        
        
class ExamQuestionOptionSerializer(serializers.ModelSerializer):
    option_text = serializers.CharField(source='option.text', read_only=True)

    class Meta:
        model = ExamQuestionOption
        fields = ['id', 'option', 'option_text']


class ExamQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    options = serializers.SerializerMethodField()
    question_usages = serializers.SerializerMethodField()
    class Meta:
        model = ExamQuestion
        fields = ['id', 'question', 'order', 'points', 'options', 'question_usages']

    
    

    def get_options(self, exam_question):
        # Get ExamQuestionOption instances linked to this ExamQuestion
        option_links = ExamQuestionOption.objects.filter(
            exam_question=exam_question
        ).select_related("option").order_by("id")
        print("devide", option_links)
        options_data = [QuestionOptionSerializer(link.option).data for link in option_links]
        return options_data


    def get_question_usages(self, past_exam_question):
        """
        Retrieves the year and exam title for all question usages related to this question.
        """
        question_usages = past_exam_question.question.usages.all().select_related('past_exam') # Fetch all usages and related PastExam

        usage_data = []
        for usage in question_usages:
            usage_data.append({
                "year": usage.year,
                "exam_title": usage.exam if usage.exam else usage.past_exam.title if usage.past_exam else None,
            })
        return usage_data if usage_data else None
   
class ExamSerializer(serializers.ModelSerializer):
    status_id = serializers.IntegerField(source='exam.id', read_only=True)
    status = serializers.ReadOnlyField()  # Read-only field to display exam status
    category_name = serializers.CharField(source='category.name', read_only=True)  # Category name for convenience
    questions = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()  # Custom field for subjects with question count
    creater_name = serializers.CharField(source='created_by.username', read_only=True)

    exam_type = serializers.PrimaryKeyRelatedField(queryset=ExamType.objects.all())

    # Read-only field to show exam_type name in the response
    exam_type_name = serializers.CharField(source='exam_type.name', read_only=True)

    # Add these fields
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)

    class Meta:
        model = Exam
        fields = [
            'exam_id', 'title', 'total_questions', 'created_by', 'creater_name', 'total_mark',
            'pass_mark', 'negative_mark', 'created_at', 'updated_at',
            'starting_time', 'last_date', 'category', 'category_name', 
            'duration', 'status', 'questions', 'status_id', 'subjects',
            'organization', 'organization_name', 'department', 'department_name', 'position', 'position_name', 'exam_type', 'exam_type_name'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'status', 'category_name',
            'organization_name', 'department_name', 'position_name', 'exam_type_name'
        ]
    
    def get_subjects(self, obj):
        question_subjects = [question.subject.name for question in obj.questions.all()]
        subject_count = Counter(question_subjects)
        return [{'subject': subject, 'question_count': count} for subject, count in subject_count.items()]
    
    def get_questions(self, exam):
        """
        Gets the questions for this past exam, with their exam-specific options.
        """
        # Get the PastExamQuestions for this exam.  Crucially, order them.
        exam_questions = ExamQuestion.objects.filter(exam=exam).order_by("id")
        
        # Serialize each PastExamQuestion, which will include the correct options.
        question_data = []
        for peq in exam_questions:
            question_serializer = ExamQuestionSerializer(peq) # Use the PastExamQuestionSerializer
            question_data.append(question_serializer.data)
        return question_data
    
    
class ExamListSerializer(serializers.ModelSerializer):
    exam_type = serializers.PrimaryKeyRelatedField(queryset=ExamType.objects.all())
    exam_type_name = serializers.CharField(source='exam_type.name', read_only=True)
    created_by = serializers.StringRelatedField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True) 
    category = serializers.StringRelatedField()

    class Meta:
        model = Exam
        fields = [
            'exam_id',
            'title',
            'exam_type',
            'exam_type_name',
            'total_questions',
            'total_mark',
            'pass_mark',
            'negative_mark',
            'duration',
            'starting_time',
            'last_date',
            'organization_name',
            'department_name',
            'position_name',
            'subject_name',
            'category',
            'created_by',
            'created_at',
        ]

class StatusSerializer(serializers.ModelSerializer):
    exam_details = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = '__all__'

    def get_exam_details(self, obj):
        return obj.get_exam_details()

class ExamDifficultySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamDifficulty
        fields = [
            'exam',
            'difficulty1_percentage',
            'difficulty2_percentage',
            'difficulty3_percentage',
            'difficulty4_percentage',
            'difficulty5_percentage',
            'difficulty6_percentage',
        ]
    
    def validate(self, data):
        """
        Ensure that the sum of the difficulty percentages is equal to 100%.
        """
        total_percentage = (data['difficulty1_percentage'] +
                            data['difficulty2_percentage'] +
                            data['difficulty3_percentage'] +
                            data['difficulty4_percentage'] +
                            data['difficulty5_percentage'] +
                            data['difficulty6_percentage'])
        if total_percentage != 100:
            raise serializers.ValidationError("The total percentage of difficulty questions must equal 100%.")
        return data



    
class LeaderboardSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    exam = serializers.ReadOnlyField(source='exam.title')
    user_id = serializers.ReadOnlyField(source='user.id')
    position = serializers.SerializerMethodField()
    class Meta:
        model = Leaderboard
        fields = '__all__'
        
    
    def get_position(self, obj):
        # Calculate position dynamically
        ordered_leaderboard = Leaderboard.objects.filter(exam=obj.exam).order_by('-score')
        position = 1
        for entry in ordered_leaderboard:
            if entry.user == obj.user:
                return position
            position += 1
        return None





class SubjectQuestionCountSerializer(serializers.Serializer):
    subject_name = serializers.CharField()
    question_count = serializers.IntegerField()





class ResultSerializer(serializers.Serializer):
    username = serializers.CharField(source='user__username')
    cumulative_questions = serializers.IntegerField()
    cumulative_score = serializers.IntegerField()
    total_correct = serializers.IntegerField()



class QuestionUsageSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)

    class Meta:
        model = QuestionUsage
        fields = ['id', 'question', 'question_text', 'exam', 'year']
        read_only_fields = ['id', 'question_text']
        
        
class UserAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    selected_option_text = serializers.CharField(source='selected_option.text', read_only=True)
    question = QuestionSerializer()
    selected_option = QuestionOptionSerializer()  

    class Meta:
        model = UserAnswer
        fields = ['id', 'exam_attempt', 'question', 'question_text', 'selected_option', 'selected_option_text', 'is_correct']




class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "address"]
        
        
class DepartmentSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())

    class Meta:
        model = Department
        fields = ["id", "name", "organization"]
    
    def create(self, validated_data):
        organization = validated_data.pop('organization')  # This pops out the organization related data
        department = Department.objects.create(organization=organization, **validated_data)
        return department
        
class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "name"]
        
        
class PastExamQuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for PastExamQuestion, including options, explanations, and usage data.
    """
    options = serializers.SerializerMethodField()
    question = QuestionSerializer(read_only=True)
    question_usages = serializers.SerializerMethodField()

    explanation = serializers.CharField(read_only=True)
    explanation_image = serializers.ImageField(read_only=True)

    class Meta:
        model = PastExamQuestion
        fields = [
            "id", "question", "order", "points",
            "options", "explanation", "explanation_image", "question_usages"
        ]

    def get_options(self, past_exam_question):
        """
        Retrieves and serializes options specific to this PastExamQuestion instance.
        """
        option_links = PastExamQuestionOption.objects.filter(
            question=past_exam_question
        ).select_related("option").order_by("id")

        options_data = [QuestionOptionSerializer(link.option).data for link in option_links]
        return options_data

    def get_question_usages(self, past_exam_question):
        """
        Retrieves the year and exam title for all question usages related to this question.
        """
        question_usages = past_exam_question.question.usages.all().select_related('past_exam')

        usage_data = []
        for usage in question_usages:
            usage_data.append({
                "year": usage.year,
                "exam_title": usage.exam if usage.exam else usage.past_exam.title if usage.past_exam else None,
            })
        return usage_data if usage_data else None


class PastExamQuestionExplanationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PastExamQuestion
        fields = ['id', 'explanation', 'explanation_image']
        
class PastExamSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, allow_null=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    questions_count = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = PastExam
        fields = [
            "id", "title", "organization_name", "department_name", "position_name",
            "duration", "pass_mark", "negative_mark",
            "exam_date", "is_published", "questions_count", "questions", "created_by"
        ]

    def get_questions_count(self, obj):
        return obj.questions.count()

    def get_questions(self, past_exam):
        """
        Gets the questions for this past exam, with their exam-specific options.
        """
        # Get the PastExamQuestions for this exam.  Crucially, order them.
        past_exam_questions = PastExamQuestion.objects.filter(exam=past_exam).order_by("id")

        # Serialize each PastExamQuestion, which will include the correct options.
        question_data = []
        for peq in past_exam_questions:
            question_serializer = PastExamQuestionSerializer(peq) # Use the PastExamQuestionSerializer
            question_data.append(question_serializer.data)
        return question_data

class PastExamListSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    exam_type = serializers.SerializerMethodField()
    missing_explanations_count = serializers.SerializerMethodField()

    class Meta:
        model = PastExam
        fields = [
            'id',
            'title',
            'exam_type',
            'organization',
            'department',
            'position',
            'exam_date',
            'duration',
            'total_questions',
            'pass_mark',
            'negative_mark',
            'is_published',
            'created_by',
            'created_at',
            'missing_explanations_count',  # 👈 Add this
        ]
        
    def get_organization(self, obj):
        return obj.organization.name if obj.organization else None

    def get_department(self, obj):
        return obj.department.name if obj.department else None

    def get_position(self, obj):
        return obj.position.name if obj.position else None

    def get_created_by(self, obj):
        return obj.created_by.username if obj.created_by else None

    def get_exam_type(self, obj):
        return obj.exam_type.name if obj.exam_type else None


    def get_missing_explanations_count(self, obj):
        return obj.related_questions.filter(
            models.Q(explanation__isnull=True) | models.Q(explanation__exact='') |
            models.Q(explanation_image__isnull=True)
        ).count()


class PastExamCreateSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), write_only=True
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), write_only=True, required=False, allow_null=True
    )
    position = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(), write_only=True
    )
    exam_type = serializers.PrimaryKeyRelatedField(
        queryset=ExamType.objects.all(), write_only=True  # Include ExamType here
    )
    file = serializers.FileField(required=False, write_only=True)

    class Meta:
        model = PastExam
        fields = [
            "id",
            "title",
            "organization",
            "department",
            "position",
            "exam_type",         # ✅ Add this line
            "exam_date",
            "duration",
            "pass_mark",
            "negative_mark",
            "is_published",
            "file",
        ]
        
    def validate_title(self, value):
        if PastExam.objects.filter(title=value).exists():
            raise serializers.ValidationError("An exam with this title already exists.")
        return value

    def create(self, validated_data):
        validated_data.pop("file", None)
        user = self.context["request"].user
        validated_data["created_by"] = user
        return PastExam.objects.create(**validated_data)



class PastExamAttemptSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)  # User's name
    past_exam_title = serializers.StringRelatedField(source='past_exam.title', read_only=True)  # Past exam title
    score = serializers.ReadOnlyField()
    attempt_time = serializers.ReadOnlyField()
    pass_mark = serializers.IntegerField(source='past_exam.pass_mark')

    class Meta:
        model = PastExamAttempt
        fields = [
            'id', 'user', 'user_name', 'past_exam', 'past_exam_title', 'total_questions', 
            'answered_questions', 'correct_answers', 'wrong_answers', 'score', 'attempt_time', 'pass_mark'
        ]
        read_only_fields = ['attempt_time', 'score']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user_name'] = instance.user.username
        representation['past_exam_title'] = instance.past_exam.title
        return representation



class PastUserAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    selected_option_text = serializers.CharField(source='selected_option.text', read_only=True)

    class Meta:
        model = PastUserAnswer
        fields = ['id', 'question', 'question_text', 'selected_option', 'selected_option_text', 'is_correct']
