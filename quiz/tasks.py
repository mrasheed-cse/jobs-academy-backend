from celery import shared_task
from django.utils import timezone
from .models import ExamAttempt
# from subscription.models import UsageTracking, UserSubscription

@shared_task
def auto_submit_exam(attempt_id):
    try:
        # Fetch the attempt object
        attempt = ExamAttempt.objects.get(id=attempt_id)
        user = attempt.user
        exam = attempt.exam

        # Fetch the user's usage tracking and package details
        # usage_tracking = UsageTracking.objects.filter(user=user).first()
        # if not usage_tracking or not usage_tracking.package:
        #     print(f"User {user.username} does not have a valid subscription.")
        #     return  # or return a failure status, as per your design

        # package = usage_tracking.package
        
        # # Check if the exam is started and if the user has exceeded attempt limits
        # exam_attempts = usage_tracking.exam_attempts
        # if str(exam.exam_id) not in exam_attempts:
        #     print(f"User {user.username} has not started the exam.")
        #     return  # or return a failure status

        attempts_taken = exam_attempts[str(exam.exam_id)]["attempts"]
        if attempts_taken >= package.max_attempts:
            print(f"User {user.username} has reached the max attempts for this exam.")
            return  # or return a failure status

        # Check if the user has exceeded the total exam limit
        # if usage_tracking.total_exams_taken >= package.max_exams:
        #     print(f"User {user.username} has reached the total exam limit for their package.")
        #     return  # or return a failure status

        # Check if the attempt has already been completed
        if attempt.passed or attempt.answered > 0:
            print(f"Attempt {attempt_id} is already submitted or passed.")
            return  # or return a success status

        # Process unanswered questions by setting a default answer
        unanswered_questions = attempt.exam.questions.exclude(id__in=[a.question_id for a in attempt.answers.all()])
        for question in unanswered_questions:
            attempt.answers.create(question_id=question.id, option='none')  # Adjust 'none' as per your needs

        # Recalculate pass/fail status
        attempt.passed = attempt.is_passed()
        attempt.attempt_time = timezone.now()
        attempt.save()

        print(f"Attempt {attempt_id} has been auto-submitted.")

    except ExamAttempt.DoesNotExist:
        print(f"ExamAttempt with id {attempt_id} does not exist.")
    except Exception as e:
        print(f"An error occurred while processing the auto-submit: {str(e)}")
