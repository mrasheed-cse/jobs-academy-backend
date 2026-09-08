# Hand-written reconciliation migration - see 0001_1_reconcile_missing_models.py
# for background. This one reconciles Exam, Category, and Question, whose
# tracked field lists have drifted significantly from their real current
# definitions (including Exam's primary key changing from an auto id to a
# UUID exam_id at some point without a matching migration).
#
# STATE ONLY - runs zero real SQL (database_operations=[]). All of these
# fields already exist in the real database; this only fixes Django's
# internal bookkeeping so future `makemigrations` calls work correctly.
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0003_pastexam_subjects'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                # --- Exam: remove stale tracked fields ---
                migrations.RemoveField(model_name='exam', name='description'),
                migrations.RemoveField(model_name='exam', name='is_published'),
                migrations.RemoveField(model_name='exam', name='pass_marks'),
                migrations.RemoveField(model_name='exam', name='total_marks'),
                # --- Exam: primary key swap (old auto id -> real UUID exam_id) ---
                migrations.AddField(
                    model_name='exam',
                    name='exam_id',
                    field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                migrations.RemoveField(model_name='exam', name='id'),
                # --- Exam: add missing real fields ---
                migrations.AddField(
                    model_name='exam',
                    name='category',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exams', to='quiz.examcategory'),
                ),
                migrations.AddField(model_name='exam', name='total_questions', field=models.PositiveIntegerField()),
                migrations.AddField(model_name='exam', name='total_mark', field=models.PositiveIntegerField()),
                migrations.AddField(model_name='exam', name='pass_mark', field=models.PositiveIntegerField()),
                migrations.AddField(model_name='exam', name='updated_at', field=models.DateTimeField(auto_now=True)),
                migrations.AddField(model_name='exam', name='starting_time', field=models.DateTimeField(blank=True, null=True)),
                migrations.AddField(model_name='exam', name='last_date', field=models.DateField(blank=True, null=True)),

                # --- Category: add missing field ---
                migrations.AddField(model_name='category', name='description', field=models.TextField(blank=True, null=True)),

                # --- Question: add missing fields ---
                migrations.AddField(model_name='question', name='remarks', field=models.TextField(blank=True, null=True)),
                migrations.AddField(model_name='question', name='time_limit', field=models.IntegerField(default=60)),
                migrations.AddField(
                    model_name='question',
                    name='created_by',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='question_created_by', to=settings.AUTH_USER_MODEL),
                ),
                migrations.AddField(
                    model_name='question',
                    name='reviewed_by',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='question_reviewed_by', to=settings.AUTH_USER_MODEL),
                ),
                migrations.AddField(model_name='question', name='created_at', field=models.DateField(auto_now_add=True, null=True)),
                migrations.AddField(model_name='question', name='updated_at', field=models.DateField(auto_now=True, null=True)),
            ],
        ),
    ]
