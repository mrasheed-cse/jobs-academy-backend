# Hand-written reconciliation migration - see 0001_1_reconcile_missing_models.py
# for background. This one fixes field ATTRIBUTE mismatches (null, blank,
# unique, max_length, choices, on_delete, default) discovered via a full
# deconstruct()-based comparison between tracked state and real model
# definitions, for fields that existed under the right name in both but
# with different properties.
#
# STATE ONLY - runs zero real SQL (database_operations=[]).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0003_1_reconcile_exam_category_question'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(model_name='exam', name='title', field=models.CharField(max_length=255, unique=True)),
                migrations.AlterField(model_name='exam', name='created_at', field=models.DateTimeField(auto_now_add=True)),
                migrations.AlterField(model_name='category', name='name', field=models.CharField(max_length=255, unique=True)),
                migrations.AlterField(model_name='subject', name='name', field=models.CharField(max_length=100, unique=True)),
                migrations.AlterField(model_name='question', name='marks', field=models.IntegerField()),
                migrations.AlterField(
                    model_name='question',
                    name='category',
                    field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='quiz.category'),
                ),
                migrations.AlterField(
                    model_name='question',
                    name='status',
                    field=models.CharField(
                        max_length=30,
                        choices=[('submitted', 'Submitted'), ('reviewed', 'Reviewed'), ('approved', 'Approved'), ('published', 'Published'), ('rejected', 'Rejected')],
                        default='submitted',
                        null=True,
                    ),
                ),
                migrations.AlterField(
                    model_name='question',
                    name='time_limit',
                    field=models.IntegerField(default=60, help_text='Time limit for this question in seconds'),
                ),
            ],
        ),
    ]
