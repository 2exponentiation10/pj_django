from django.contrib import admin

from .models import Chapter, MediaAsset, PronunciationAttempt, Sentence, UserProfile, Word


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "difficulty", "context_tag", "accuracy")
    search_fields = ("title", "context_tag")
    list_filter = ("difficulty", "context_tag")


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("id", "chapter", "korean_word", "north_korean_word", "is_collect", "accuracy")
    search_fields = ("korean_word", "north_korean_word")
    list_filter = ("chapter", "is_collect")


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ("id", "chapter", "korean_sentence", "is_collect", "accuracy")
    search_fields = ("korean_sentence", "north_korean_sentence")
    list_filter = ("chapter", "is_collect")


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "label", "key_text", "chapter", "word", "sentence", "updated_at")
    search_fields = ("label", "key_text")
    list_filter = ("category",)


@admin.register(PronunciationAttempt)
class PronunciationAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "sentence", "score_percent", "speed_score", "pitch_score", "created_at")
    search_fields = ("reference_text", "transcript")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "role", "is_active", "updated_at")
    search_fields = ("user__username", "display_name")
    list_filter = ("role", "is_active")
