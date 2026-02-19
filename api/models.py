from django.db import models

class Chapter(models.Model):
    title = models.CharField(max_length=100)
    accuracy = models.FloatField(default=0.0)
    def __str__(self):
        return self.title

class Word(models.Model):
    chapter = models.ForeignKey(Chapter, related_name='words', on_delete=models.CASCADE)
    korean_word = models.CharField(max_length=100)
    north_korean_word = models.CharField(max_length=100)
    is_called = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    is_collect = models.BooleanField(default=False)
    accuracy = models.FloatField(default=0.0)  # 단어 정확도 추가
    def __str__(self):
        return self.korean_word


class Sentence(models.Model):
    chapter = models.ForeignKey(Chapter, related_name='sentences', on_delete=models.CASCADE)
    korean_sentence = models.CharField(max_length=255)
    north_korean_sentence = models.CharField(max_length=255)
    is_called = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    is_collect = models.BooleanField(default=False)
    accuracy = models.FloatField(default=0.0)

    def __str__(self):
        return self.korean_sentence


class PronunciationAttempt(models.Model):
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
