from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0002_department_examtype_organization_position_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pastexam',
            name='subjects',
            field=models.TextField(blank=True, default=''),
        ),
    ]
