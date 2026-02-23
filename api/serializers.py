from rest_framework import serializers

from .models import Chapter, Sentence, Word


class WordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Word
        fields = [
            "id",
            "chapter",
            "korean_word",
            "north_korean_word",
            "is_called",
            "is_correct",
            "is_collect",
            "accuracy",
        ]


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "title", "accuracy", "difficulty", "context_tag"]


class SentenceSerializer(serializers.ModelSerializer):
    recognized_text = serializers.SerializerMethodField()

    class Meta:
        model = Sentence
        fields = [
            "id",
            "chapter",
            "korean_sentence",
            "north_korean_sentence",
            "is_called",
            "is_correct",
            "is_collect",
            "accuracy",
            "recognized_text",
        ]

    def get_recognized_text(self, obj):
        # The model currently has no persistent recognized_text column.
        return getattr(obj, "recognized_text", "")
