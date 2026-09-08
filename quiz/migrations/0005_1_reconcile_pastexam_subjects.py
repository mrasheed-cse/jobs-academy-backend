# Hand-written reconciliation migration - see 0001_1_reconcile_missing_models.py
# for background. Migration 0003 added a 'subjects' TextField to PastExam,
# but the real current model no longer references this field at all - it
# was dropped from models.py at some point without a matching migration.
#
# STATE ONLY - runs zero real SQL. The real database column (if it still
# physically exists) is left untouched, harmless and unused; this only
# fixes Django's tracking so future `makemigrations` calls stop trying to
# generate a real DROP COLUMN for it on every run.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0005_add_question_group_reviewed'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(model_name='pastexam', name='subjects'),
            ],
        ),
    ]
