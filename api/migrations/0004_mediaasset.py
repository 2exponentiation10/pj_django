from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_chapter_metadata"),
    ]

    operations = [
        migrations.CreateModel(
            name="MediaAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("word", "word"),
                            ("sentence", "sentence"),
                            ("chapter", "chapter"),
                            ("general", "general"),
                        ],
                        db_index=True,
                        default="general",
                        max_length=20,
                    ),
                ),
                ("label", models.CharField(blank=True, default="", max_length=200)),
                ("key_text", models.CharField(blank=True, db_index=True, default="", max_length=255)),
                ("image", models.ImageField(upload_to="media_assets/%Y/%m/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "chapter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="media_assets",
                        to="api.chapter",
                    ),
                ),
                (
                    "sentence",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="media_assets",
                        to="api.sentence",
                    ),
                ),
                (
                    "word",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="media_assets",
                        to="api.word",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
            },
        ),
    ]
