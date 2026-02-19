from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PronunciationAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_text", models.TextField()),
                ("transcript", models.TextField(blank=True, default="")),
                ("score_percent", models.FloatField(default=0.0)),
                ("text_score", models.FloatField(default=0.0)),
                ("speed_score", models.FloatField(blank=True, null=True)),
                ("pitch_score", models.FloatField(blank=True, null=True)),
                ("pitch_curve_similarity", models.FloatField(blank=True, null=True)),
                ("volume_curve_similarity", models.FloatField(blank=True, null=True)),
                ("audio_duration_sec", models.FloatField(blank=True, null=True)),
                ("syllables_per_sec", models.FloatField(blank=True, null=True)),
                ("pitch_median_hz", models.FloatField(blank=True, null=True)),
                ("pitch_std_hz", models.FloatField(blank=True, null=True)),
                ("voiced_frames", models.IntegerField(default=0)),
                ("user_pitch_curve", models.JSONField(blank=True, default=list)),
                ("user_volume_curve", models.JSONField(blank=True, default=list)),
                ("reference_pitch_curve", models.JSONField(blank=True, default=list)),
                ("reference_volume_curve", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "sentence",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pronunciation_attempts",
                        to="api.sentence",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
