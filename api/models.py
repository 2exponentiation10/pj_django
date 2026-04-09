from django.db import models
from django.contrib.auth.models import User


class Chapter(models.Model):
    owner = models.ForeignKey(User, related_name="chapters", on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    accuracy = models.FloatField(default=0.0)
    difficulty = models.CharField(max_length=20, default="beginner")
    context_tag = models.CharField(max_length=50, default="daily")

    def __str__(self):
        return self.title


class Word(models.Model):
    chapter = models.ForeignKey(Chapter, related_name="words", on_delete=models.CASCADE)
    korean_word = models.CharField(max_length=100)
    north_korean_word = models.CharField(max_length=100)
    is_called = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    is_collect = models.BooleanField(default=False)
    accuracy = models.FloatField(default=0.0)  # 단어 정확도 추가

    def __str__(self):
        return self.korean_word


class Sentence(models.Model):
    chapter = models.ForeignKey(Chapter, related_name="sentences", on_delete=models.CASCADE)
    korean_sentence = models.CharField(max_length=255)
    north_korean_sentence = models.CharField(max_length=255)
    is_called = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    is_collect = models.BooleanField(default=False)
    accuracy = models.FloatField(default=0.0)

    def __str__(self):
        return self.korean_sentence


class MediaAsset(models.Model):
    CATEGORY_WORD = "word"
    CATEGORY_SENTENCE = "sentence"
    CATEGORY_CHAPTER = "chapter"
    CATEGORY_GENERAL = "general"
    CATEGORY_CHOICES = [
        (CATEGORY_WORD, "word"),
        (CATEGORY_SENTENCE, "sentence"),
        (CATEGORY_CHAPTER, "chapter"),
        (CATEGORY_GENERAL, "general"),
    ]

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
        db_index=True,
    )
    owner = models.ForeignKey(User, related_name="media_assets", on_delete=models.CASCADE)
    label = models.CharField(max_length=200, blank=True, default="")
    key_text = models.CharField(max_length=255, blank=True, default="", db_index=True)
    image = models.ImageField(upload_to="media_assets/%Y/%m/")
    chapter = models.ForeignKey(
        Chapter,
        related_name="media_assets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    word = models.ForeignKey(
        Word,
        related_name="media_assets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sentence = models.ForeignKey(
        Sentence,
        related_name="media_assets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        target = self.key_text or self.label or f"id={self.id}"
        return f"{self.category}:{target}"


class PronunciationAttempt(models.Model):
    user = models.ForeignKey(
        User,
        related_name="pronunciation_attempts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sentence = models.ForeignKey(
        Sentence,
        related_name="pronunciation_attempts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reference_text = models.TextField()
    transcript = models.TextField(blank=True, default="")

    score_percent = models.FloatField(default=0.0)
    text_score = models.FloatField(default=0.0)
    speed_score = models.FloatField(null=True, blank=True)
    pitch_score = models.FloatField(null=True, blank=True)
    pitch_curve_similarity = models.FloatField(null=True, blank=True)
    volume_curve_similarity = models.FloatField(null=True, blank=True)

    audio_duration_sec = models.FloatField(null=True, blank=True)
    syllables_per_sec = models.FloatField(null=True, blank=True)
    pitch_median_hz = models.FloatField(null=True, blank=True)
    pitch_std_hz = models.FloatField(null=True, blank=True)
    voiced_frames = models.IntegerField(default=0)

    # Keep compact curves for debug/visualization consistency across retries.
    user_pitch_curve = models.JSONField(default=list, blank=True)
    user_volume_curve = models.JSONField(default=list, blank=True)
    reference_pitch_curve = models.JSONField(default=list, blank=True)
    reference_volume_curve = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Attempt<{self.id}> sentence={self.sentence_id} score={self.score_percent:.2f}"


class UserProfile(models.Model):
    ROLE_LEARNER = "learner"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_LEARNER, "learner"),
        (ROLE_ADMIN, "admin"),
    ]

    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    display_name = models.CharField(max_length=120, blank=True, default="")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_LEARNER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.display_name or self.user.username


class VisualGenerationJob(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "queued"),
        (STATUS_RUNNING, "running"),
        (STATUS_SUCCEEDED, "succeeded"),
        (STATUS_FAILED, "failed"),
    ]

    owner = models.ForeignKey(
        User,
        related_name="visual_generation_jobs",
        on_delete=models.CASCADE,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    total_items = models.IntegerField(default=0)
    completed_items = models.IntegerField(default=0)
    chapters_count = models.IntegerField(default=0)
    words_count = models.IntegerField(default=0)
    sentences_count = models.IntegerField(default=0)
    message = models.CharField(max_length=255, blank=True, default="")
    error_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"VisualJob<{self.id}> {self.status} owner={self.owner_id}"
