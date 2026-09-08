from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="Subject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(blank=True, null=True, unique=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="question_images/")),
                ("marks", models.IntegerField(blank=True, null=True)),
                ("difficulty_level", models.IntegerField(blank=True, null=True)),
                ("status", models.CharField(blank=True, default="submitted", max_length=20, null=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="quiz.category")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="quiz.subject")),
            ],
        ),
        migrations.CreateModel(
            name="QuestionOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("is_correct", models.BooleanField(default=False)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="quiz.question")),
            ],
        ),
        migrations.CreateModel(
            name="Exam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("duration", models.IntegerField(blank=True, null=True)),
                ("total_marks", models.IntegerField(blank=True, null=True)),
                ("pass_marks", models.IntegerField(blank=True, null=True)),
                ("is_published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PastExam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.TextField(unique=True)),
                ("exam_date", models.DateField()),
                ("duration", models.IntegerField(blank=True, null=True)),
                ("is_published", models.BooleanField(default=True)),
                ("total_questions", models.PositiveIntegerField(default=0)),
                ("pass_mark", models.PositiveIntegerField(default=50)),
                ("negative_mark", models.FloatField(default=0.0)),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_past_exams", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PastExamQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.IntegerField(blank=True, null=True)),
                ("points", models.FloatField(blank=True, null=True)),
                ("exam", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="related_questions", to="quiz.pastexam")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="related_pastexams", to="quiz.question")),
            ],
        ),
    ]
