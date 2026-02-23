from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_pronunciationattempt"),
    ]

    operations = [
        migrations.AddField(
            model_name="chapter",
            name="context_tag",
            field=models.CharField(default="daily", max_length=50),
        ),
        migrations.AddField(
            model_name="chapter",
            name="difficulty",
            field=models.CharField(default="beginner", max_length=20),
        ),
    ]
