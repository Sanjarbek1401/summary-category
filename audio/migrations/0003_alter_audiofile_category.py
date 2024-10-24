# Generated by Django 5.1.2 on 2024-10-22 08:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audio', '0002_remove_audiofile_categories_remove_audiofile_file_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='audiofile',
            name='category',
            field=models.CharField(blank=True, choices=[('business', 'Business'), ('gender', 'Gender'), ('transcription', 'Transcription'), ('summary', 'Summary'), ('operator_feedback', 'Operator Feedback'), ('customer_feedback', 'Customer Feedback')], max_length=255, null=True),
        ),
    ]
