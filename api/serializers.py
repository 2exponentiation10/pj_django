from rest_framework import serializers

from .models import Chapter, MediaAsset, Sentence, Word


def _build_asset_url(request, asset):
    if not request or not asset:
        return ""
    return request.build_absolute_uri(f"/api/media-assets/{asset.id}/file/")


def _resolve_word_asset(word):
    direct = (
        MediaAsset.objects.filter(category=MediaAsset.CATEGORY_WORD, word_id=word.id)
        .order_by("-updated_at", "-id")
        .first()
    )
    if direct:
        return direct
    return (
        MediaAsset.objects.filter(
            category=MediaAsset.CATEGORY_WORD,
            key_text=word.korean_word,
        )
        .order_by("-updated_at", "-id")
        .first()
    )


def _resolve_sentence_asset(sentence):
    direct = (
        MediaAsset.objects.filter(category=MediaAsset.CATEGORY_SENTENCE, sentence_id=sentence.id)
        .order_by("-updated_at", "-id")
        .first()
    )
    if direct:
        return direct
    return (
        MediaAsset.objects.filter(
            category=MediaAsset.CATEGORY_SENTENCE,
            key_text=sentence.korean_sentence,
        )
        .order_by("-updated_at", "-id")
        .first()
    )


class WordSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    image_asset_id = serializers.SerializerMethodField()

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
            "image_url",
            "image_asset_id",
        ]

    def get_image_url(self, obj):
        asset = _resolve_word_asset(obj)
        return _build_asset_url(self.context.get("request"), asset)

    def get_image_asset_id(self, obj):
        asset = _resolve_word_asset(obj)
        return asset.id if asset else None


class ChapterSerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = [
            "id",
            "title",
            "accuracy",
            "difficulty",
            "context_tag",
            "cover_image_url",
        ]

    def get_cover_image_url(self, obj):
        asset = (
            MediaAsset.objects.filter(category=MediaAsset.CATEGORY_CHAPTER, chapter_id=obj.id)
            .order_by("-updated_at", "-id")
            .first()
        )
        return _build_asset_url(self.context.get("request"), asset)


class SentenceSerializer(serializers.ModelSerializer):
    recognized_text = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    image_asset_id = serializers.SerializerMethodField()

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
            "image_url",
            "image_asset_id",
        ]

    def get_recognized_text(self, obj):
        # The model currently has no persistent recognized_text column.
        return getattr(obj, "recognized_text", "")

    def get_image_url(self, obj):
        asset = _resolve_sentence_asset(obj)
        return _build_asset_url(self.context.get("request"), asset)

    def get_image_asset_id(self, obj):
        asset = _resolve_sentence_asset(obj)
        return asset.id if asset else None


class MediaAssetSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "category",
            "label",
            "key_text",
            "chapter",
            "word",
            "sentence",
            "image",
            "image_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_image_url(self, obj):
        return _build_asset_url(self.context.get("request"), obj)
