from django.db import migrations, models
from django.contrib.auth.hashers import make_password
import django.db.models.deletion


def _forward_assign_owner_user(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    chapter_model = apps.get_model("api", "Chapter")
    word_model = apps.get_model("api", "Word")
    sentence_model = apps.get_model("api", "Sentence")
    media_asset_model = apps.get_model("api", "MediaAsset")
    attempt_model = apps.get_model("api", "PronunciationAttempt")

    master, created = user_model.objects.get_or_create(
        username="master",
        defaults={
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
            "email": "master@local",
            "password": make_password(None),
        },
    )
    if created and not master.password:
        master.password = make_password(None)
        master.save(update_fields=["password"])

    chapter_model.objects.filter(owner__isnull=True).update(owner_id=master.id)

    words = {w.id: w.chapter_id for w in word_model.objects.all().only("id", "chapter_id")}
    sentences = {s.id: s.chapter_id for s in sentence_model.objects.all().only("id", "chapter_id")}
    chapter_owner = {c.id: c.owner_id for c in chapter_model.objects.all().only("id", "owner_id")}

    for asset in media_asset_model.objects.filter(owner__isnull=True).iterator():
        owner_id = None
        if asset.chapter_id:
            owner_id = chapter_owner.get(asset.chapter_id)
        elif asset.word_id:
            chapter_id = words.get(asset.word_id)
            owner_id = chapter_owner.get(chapter_id) if chapter_id else None
        elif asset.sentence_id:
            chapter_id = sentences.get(asset.sentence_id)
            owner_id = chapter_owner.get(chapter_id) if chapter_id else None
        asset.owner_id = owner_id or master.id
        asset.save(update_fields=["owner_id"])

    for attempt in attempt_model.objects.filter(user__isnull=True).iterator():
        owner_id = None
        if attempt.sentence_id:
            chapter_id = sentences.get(attempt.sentence_id)
            owner_id = chapter_owner.get(chapter_id) if chapter_id else None
        attempt.user_id = owner_id or master.id
        attempt.save(update_fields=["user_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_userprofile"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="chapter",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chapters",
                to="auth.user",
            ),
        ),
        migrations.AddField(
            model_name="mediaasset",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="media_assets",
                to="auth.user",
            ),
        ),
        migrations.AddField(
            model_name="pronunciationattempt",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pronunciation_attempts",
                to="auth.user",
            ),
        ),
        migrations.RunPython(_forward_assign_owner_user, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="chapter",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chapters",
                to="auth.user",
            ),
        ),
        migrations.AlterField(
            model_name="mediaasset",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="media_assets",
                to="auth.user",
            ),
        ),
    ]
