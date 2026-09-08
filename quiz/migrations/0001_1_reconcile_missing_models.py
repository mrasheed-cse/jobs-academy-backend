# Hand-written reconciliation migration.
#
# These 6 models are defined in quiz/models.py and are actively used
# throughout the live app, but were never created by any tracked
# migration - the migration history was out of sync with the real
# database schema (most likely from an incomplete history squash/reset
# at some point before this project reached its current state).
#
# This migration ONLY updates Django's internal STATE tracking to say
# "these models already exist" - it runs ZERO real SQL against the
# database (database_operations=[]), because the underlying tables
# already exist in production. It must not be confused with a normal
# migration that creates new tables.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='ExamCategory',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100, unique=True)),
                        ('description', models.TextField(blank=True)),
                    ],
                    options={
                        'verbose_name_plural': 'Exam Categories',
                        'ordering': ['name'],
                    },
                ),
                migrations.CreateModel(
                    name='ExamAttempt',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='quiz.exam')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_attempts', to=settings.AUTH_USER_MODEL)),
                        ('answered', models.PositiveIntegerField(default=0)),
                        ('wrong_answers', models.PositiveIntegerField(default=0)),
                        ('passed', models.BooleanField(default=False, null=True)),
                        ('total_correct_answers', models.PositiveIntegerField(default=0)),
                        ('attempt_time', models.DateTimeField(auto_now_add=True)),
                        ('score', models.FloatField(blank=True, default=0.0, null=True)),
                    ],
                    options={
                        'verbose_name': 'Exam Attempt',
                        'verbose_name_plural': 'Exam Attempts',
                        'ordering': ['-attempt_time'],
                    },
                ),
                migrations.CreateModel(
                    name='ExamDifficulty',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('exam', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='difficulty', to='quiz.exam')),
                        ('difficulty1_percentage', models.IntegerField(default=0)),
                        ('difficulty2_percentage', models.IntegerField(default=0)),
                        ('difficulty3_percentage', models.IntegerField(default=0)),
                        ('difficulty4_percentage', models.IntegerField(default=0)),
                        ('difficulty5_percentage', models.IntegerField(default=0)),
                        ('difficulty6_percentage', models.IntegerField(default=0)),
                    ],
                    options={
                        'verbose_name': 'Exam Difficulty',
                        'verbose_name_plural': 'Exam Difficulties',
                    },
                ),
                migrations.CreateModel(
                    name='Leaderboard',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='leaderboard', to=settings.AUTH_USER_MODEL)),
                        ('score', models.IntegerField(default=0)),
                        ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leaderboards', to='quiz.exam')),
                        ('total_questions', models.IntegerField(default=0, null=True)),
                    ],
                    options={
                        'ordering': ['-score'],
                    },
                ),
                migrations.CreateModel(
                    name='QuestionUsage',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('question', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='usages', to='quiz.question')),
                        ('exam', models.CharField(blank=True, help_text='Name of the external exam where the question was used', max_length=255, null=True)),
                        ('past_exam', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='question_usages', to='quiz.pastexam')),
                        ('year', models.IntegerField(default=2024)),
                    ],
                ),
                migrations.CreateModel(
                    name='Status',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('exam', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='exam', to='quiz.exam')),
                        ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user', to=settings.AUTH_USER_MODEL)),
                        ('status', models.CharField(choices=[('student', 'student'), ('draft', 'Draft'), ('submitted_to_admin', 'Submitted to Admin'), ('under_review', 'Under Review'), ('reviewed', 'Reviewed'), ('returned_to_creator', 'Returned to Creator'), ('published', 'Published')], default='draft', max_length=50)),
                        ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_by', to=settings.AUTH_USER_MODEL)),
                    ],
                ),
            ],
        ),
    ]
