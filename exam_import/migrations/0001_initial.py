from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('quiz', '0002_department_examtype_organization_position_and_more'),
    ]
    operations = [
        migrations.CreateModel(
            name='ImportJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exam_title',    models.TextField()),
                ('org_name',      models.TextField()),
                ('position_name', models.TextField()),
                ('exam_year',     models.IntegerField()),
                ('subject_name',  models.TextField(default='General Knowledge')),
                ('marks_per_q',   models.IntegerField(default=1)),
                ('negative_mark', models.FloatField(default=0.25)),
                ('status',        models.CharField(choices=[('pending','Pending'),('processing','Processing'),('done','Done'),('failed','Failed')], default='pending', max_length=20)),
                ('total_pages',     models.IntegerField(default=0)),
                ('processed_pages', models.IntegerField(default=0)),
                ('questions_found', models.IntegerField(default=0)),
                ('current_page',    models.TextField(blank=True, default='')),
                ('error_log',       models.TextField(blank=True, default='')),
                ('created_at',      models.DateTimeField(auto_now_add=True)),
                ('finished_at',     models.DateTimeField(null=True, blank=True)),
                ('past_exam', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_jobs', to='quiz.pastexam')),
            ],
        ),
    ]
