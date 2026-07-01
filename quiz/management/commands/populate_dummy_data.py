from django.core.management.base import BaseCommand
from faker import Faker
from django.utils import timezone
from quiz.models import Exam, Question, QuestionOption, Leaderboard
from django.contrib.auth import get_user_model
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate dummy data for Exam, Question, QuestionOption, and Leaderboard models'

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Create some users
        users = []
        for _ in range(10):
            phone_number = fake.phone_number()
            user = User.objects.create_user(username=fake.user_name(), phone_number=phone_number, password='password123')
            users.append(user)

        # Create some exams with questions and options
        exams = []
        for user in users:
            for _ in range(5):  # Create 5 exams for each user
                exam = Exam.objects.create(
                    title=fake.catch_phrase(),
                    total_questions=random.randint(5, 10),
                    total_marks=random.randint(50, 100),
                    user=user,
                    last_date=timezone.now() + timezone.timedelta(days=random.randint(30, 90))
                )
                exams.append(exam)

                for _ in range(exam.total_questions):
                    question = Question.objects.create(
                        exam=exam,
                        text=fake.sentence(nb_words=6),
                        marks=random.randint(1, 5)
                    )

                    for _ in range(4):  # Assuming each question has 4 options
                        QuestionOption.objects.create(
                            question=question,
                            text=fake.word(),
                            is_correct=random.choice([True, False])
                        )

        # Create some leaderboard entries
        for user in users:
            exam = random.choice(exams)  # Ensure there's always an exam to choose from
            score = random.randint(20, 100)
            Leaderboard.objects.create(user=user, exam=exam, score=score)

        self.stdout.write(self.style.SUCCESS('Dummy data populated successfully!'))
