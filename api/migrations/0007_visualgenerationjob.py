from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_user_scoping"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VisualGenerationJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "queued"),
                            ("running", "running"),
                            ("succeeded", "succeeded"),
                            ("failed", "failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("total_items", models.IntegerField(default=0)),
                ("completed_items", models.IntegerField(default=0)),
                ("chapters_count", models.IntegerField(default=0)),
                ("words_count", models.IntegerField(default=0)),
                ("sentences_count", models.IntegerField(default=0)),
                ("message", models.CharField(blank=True, default="", max_length=255)),
                ("error_text", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="visual_generation_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
