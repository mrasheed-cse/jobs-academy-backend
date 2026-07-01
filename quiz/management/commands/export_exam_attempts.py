# your_django_project_root/quiz_app/management/commands/export_exam_attempts.py

import csv
import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from quiz.models import PastExamAttempt
class Command(BaseCommand):
    help = 'Exports exam attempt data to an Excel-compatible CSV file from the configured database.'

    def handle(self, *args, **options):
        # IMPORTANT: Replace 'quiz_app' with the actual name of your Django app
        # where the PastExamAttempt model is defined.
        try:
            PastExamAttempt = apps.get_model('quiz', 'PastExamAttempt')
        except LookupError:
            self.stderr.write(self.style.ERROR(
                "Error: Could not find 'PastExamAttempt' model in 'quiz_app'. "
                "Please ensure 'quiz_app' is the correct app name and 'PastExamAttempt' is defined."
            ))
            return

        # Define the output file path on your local machine
        # This will create a 'media/exports' directory in your project's base directory
        export_dir = os.path.join(settings.BASE_DIR, 'media', 'exports')
        os.makedirs(export_dir, exist_ok=True) # Ensure the directory exists

        file_path = os.path.join(export_dir, 'exam_attempts.csv')

        self.stdout.write(f'Attempting to connect to database and export data...')

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)

                # Write header row
                csv_writer.writerow([
                    'User Username',
                    'User Email',
                    'Exam Title',
                    'Attempt Time',
                    'Total Questions',
                    'Answered Questions',
                    'Correct Answers',
                    'Wrong Answers',
                    'Score'
                ])

                # Fetch data from the database
                # .select_related() optimizes by fetching related User and PastExam objects in one query
                attempts = PastExamAttempt.objects.select_related('user', 'past_exam').all().order_by('past_exam__title', 'user__username')

                if not attempts.exists():
                    self.stdout.write(self.style.WARNING("No exam attempt data found in the database."))
                else:
                    for attempt in attempts:
                        csv_writer.writerow([
                            attempt.user.username,
                            getattr(attempt.user, 'email', 'N/A'), # Use getattr for safety if email might not exist
                            attempt.past_exam.title,
                            attempt.attempt_time.strftime('%Y-%m-%d %H:%M:%S'), # Format datetime
                            attempt.total_questions,
                            attempt.answered_questions,
                            attempt.correct_answers,
                            attempt.wrong_answers,
                            attempt.score
                        ])
            self.stdout.write(self.style.SUCCESS(f'Successfully exported exam attempt data to {file_path}'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred during export: {e}"))
            self.stderr.write(self.style.ERROR("Please ensure your local settings.py is configured correctly for the remote database "
                                                "and that your local machine can connect to 161.97.141.58:5432."))