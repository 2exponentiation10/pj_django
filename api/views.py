import json
import base64
import io
import logging
import math
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import imageio_ffmpeg
except Exception:  # pragma: no cover
    imageio_ffmpeg = None

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from gtts import gTTS
except Exception:  # pragma: no cover
    gTTS = None

try:
    from pydub import AudioSegment
except Exception:  # pragma: no cover
    AudioSegment = None
from django.db.models import Avg
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Chapter, MediaAsset, PronunciationAttempt, Sentence, Word
from .serializers import (
    ChapterSerializer,
    MediaAssetSerializer,
    SentenceSerializer,
    WordSerializer,
)

logger = logging.getLogger(__name__)


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class StatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class AccuracyValueSerializer(serializers.Serializer):
    accuracy = serializers.FloatField()


class NextChapterResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()


class ReviewQueueItemSerializer(serializers.Serializer):
    sentence_id = serializers.IntegerField()
    chapter_id = serializers.IntegerField()
    chapter_title = serializers.CharField()
    difficulty = serializers.CharField()
    context_tag = serializers.CharField()
    korean_sentence = serializers.CharField()
    north_korean_sentence = serializers.CharField()
    sentence_accuracy_ratio = serializers.FloatField()
    last_score_percent = serializers.FloatField(allow_null=True)
    recent_avg_score_percent = serializers.FloatField(allow_null=True)
    priority_score = serializers.FloatField()
    reason = serializers.CharField()


class ProgressItemSerializer(serializers.Serializer):
    chapter_id = serializers.IntegerField()
    chapter_title = serializers.CharField()
    progress = serializers.FloatField()
    accuracy = serializers.FloatField()
    total_words = serializers.IntegerField()
    called_words = serializers.IntegerField()
    collect_words = serializers.IntegerField()
    total_sentences = serializers.IntegerField()
    called_sentences = serializers.IntegerField()
    collect_sentences = serializers.IntegerField()
    total_items = serializers.IntegerField()
    called_items = serializers.IntegerField()
    collect_items = serializers.IntegerField()


class ProgressResponseSerializer(serializers.Serializer):
    progress_data = ProgressItemSerializer(many=True)
    completed_chapters = serializers.IntegerField()
    overall_progress = serializers.FloatField()


class LearningProgressResponseSerializer(serializers.Serializer):
    progress = serializers.FloatField()
    words = WordSerializer(many=True)
    sentences = SentenceSerializer(many=True)


class WordUpdateRequestSerializer(serializers.Serializer):
    is_correct = serializers.BooleanField(required=False)
    is_collect = serializers.BooleanField(required=False)
    isCollect = serializers.BooleanField(required=False)


class SentenceUpdateRequestSerializer(serializers.Serializer):
    is_correct = serializers.BooleanField(required=False)
    is_collect = serializers.BooleanField(required=False)
    isCollect = serializers.BooleanField(required=False)


class SentenceAccuracyRequestSerializer(serializers.Serializer):
    accuracy = serializers.FloatField(required=False)
    recognized_text = serializers.CharField(required=False, allow_blank=True)


class SentenceWithRecognizedTextSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    chapter = serializers.IntegerField()
    korean_sentence = serializers.CharField()
    north_korean_sentence = serializers.CharField()
    is_called = serializers.BooleanField()
    is_correct = serializers.BooleanField()
    is_collect = serializers.BooleanField()
    accuracy = serializers.FloatField()
    recognized_text = serializers.CharField()
    image_url = serializers.CharField(allow_blank=True)
    image_asset_id = serializers.IntegerField(allow_null=True)


class ResetSentenceResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    deleted_attempts = serializers.IntegerField()
    sentence_id = serializers.IntegerField()


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    fallback = serializers.BooleanField(required=False)
    provider = serializers.CharField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)
    error = serializers.CharField(required=False, allow_blank=True)


class PronunciationRequestSerializer(serializers.Serializer):
    reference_text = serializers.CharField()
    sentence_id = serializers.IntegerField(required=False)
    audio = serializers.FileField()


class PronunciationEvaluationResponseSerializer(serializers.Serializer):
    transcript = serializers.CharField()
    accuracy_ratio = serializers.FloatField()
    score_percent = serializers.FloatField()
    char_similarity = serializers.FloatField()
    token_similarity = serializers.FloatField()
    text_score = serializers.FloatField()
    audio_metrics_available = serializers.BooleanField()
    speed_score = serializers.FloatField(allow_null=True)
    pitch_score = serializers.FloatField(allow_null=True)
    volume_score = serializers.FloatField(allow_null=True)
    audio_duration_sec = serializers.FloatField(allow_null=True)
    reference_duration_sec = serializers.FloatField(allow_null=True)
    syllables_per_sec = serializers.FloatField(allow_null=True)
    pitch_median_hz = serializers.FloatField(allow_null=True)
    pitch_std_hz = serializers.FloatField(allow_null=True)
    user_pitch_curve = serializers.ListField(child=serializers.FloatField())
    user_volume_curve = serializers.ListField(child=serializers.FloatField())
    reference_pitch_curve = serializers.ListField(child=serializers.FloatField())
    reference_volume_curve = serializers.ListField(child=serializers.FloatField())
    pitch_curve_similarity = serializers.FloatField(allow_null=True)
    volume_curve_similarity = serializers.FloatField(allow_null=True)
    pitch_verdict = serializers.CharField(allow_null=True)
    attempt_id = serializers.IntegerField()
    sentence_attempts_count = serializers.IntegerField(allow_null=True)
    sentence_best_score = serializers.FloatField(allow_null=True)
    recent_window_size = serializers.IntegerField()
    recent_attempt_scores = serializers.ListField(child=serializers.FloatField())
    recent_avg_score = serializers.FloatField(allow_null=True)
    recent_score_stddev = serializers.FloatField(allow_null=True)
    recent_avg_pitch_score = serializers.FloatField(allow_null=True)
    recent_avg_speed_score = serializers.FloatField(allow_null=True)
    recent_avg_volume_score = serializers.FloatField(allow_null=True)
    feedback = serializers.CharField()
    model = serializers.CharField()
    score_level = serializers.CharField()
    score_rule = serializers.JSONField()


def _get_or_create_master_user():
    user_model = get_user_model()
    user, created = user_model.objects.get_or_create(
        username="master",
        defaults={
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
            "email": "master@local",
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def _get_effective_user(request):
    if getattr(request, "user", None) and request.user.is_authenticated:
        return request.user
    return _get_or_create_master_user()


def _serializer_context(request):
    return {"request": request} if request is not None else {}


class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.all().order_by("id")
    serializer_class = ChapterSerializer

    def get_queryset(self):
        user = _get_effective_user(self.request)
        return Chapter.objects.filter(owner=user).order_by("id")

    def perform_create(self, serializer):
        serializer.save(owner=_get_effective_user(self.request))

    @extend_schema(tags=["chapters"], responses=WordSerializer(many=True))
    @action(detail=True, methods=["get"])
    def words(self, request, pk=None):
        chapter = self.get_object()
        serializer = WordSerializer(
            chapter.words.all().order_by("id"),
            many=True,
            context=_serializer_context(request),
        )
        return Response(serializer.data)

    @extend_schema(tags=["chapters"], responses=SentenceSerializer(many=True))
    @action(detail=True, methods=["get"])
    def sentences(self, request, pk=None):
        chapter = self.get_object()
        serializer = SentenceSerializer(
            chapter.sentences.all().order_by("id"),
            many=True,
            context=_serializer_context(request),
        )
        return Response(serializer.data)

    @extend_schema(tags=["chapters"], responses=WordSerializer(many=True))
    @action(detail=True, methods=["get"])
    def incollect_words(self, request, pk=None):
        chapter = self.get_object()
        serializer = WordSerializer(
            chapter.words.filter(is_collect=False).order_by("id"),
            many=True,
            context=_serializer_context(request),
        )
        return Response(serializer.data)

    @extend_schema(tags=["chapters"], responses=SentenceSerializer(many=True))
    @action(detail=True, methods=["get"])
    def incollect_sentences(self, request, pk=None):
        chapter = self.get_object()
        serializer = SentenceSerializer(
            chapter.sentences.filter(is_collect=False).order_by("id"),
            many=True,
            context=_serializer_context(request),
        )
        return Response(serializer.data)

    @extend_schema(tags=["chapters"], responses=AccuracyValueSerializer)
    @action(detail=True, methods=["get"])
    def accuracy(self, request, pk=None):
        chapter = self.get_object()
        total_words = chapter.words.count()
        correct_words = chapter.words.filter(is_collect=True).count()
        accuracy = (correct_words / total_words) * 100 if total_words else 0
        return Response({"accuracy": accuracy})


class WordViewSet(viewsets.ModelViewSet):
    queryset = Word.objects.all().order_by("id")
    serializer_class = WordSerializer

    def get_queryset(self):
        user = _get_effective_user(self.request)
        return Word.objects.filter(chapter__owner=user).order_by("id")

    @extend_schema(tags=["words"], responses=StatusResponseSerializer)
    @action(detail=True, methods=["post"])
    def save_word(self, request, pk=None):
        word = self.get_object()
        word.is_correct = True
        word.save(update_fields=["is_correct"])
        return Response({"status": "success"})


class SentenceViewSet(viewsets.ModelViewSet):
    queryset = Sentence.objects.all().order_by("id")
    serializer_class = SentenceSerializer

    def get_queryset(self):
        user = _get_effective_user(self.request)
        return Sentence.objects.filter(chapter__owner=user).order_by("id")

    @extend_schema(tags=["sentences"], responses=StatusResponseSerializer)
    @action(detail=True, methods=["post"])
    def save_sentence(self, request, pk=None):
        sentence = self.get_object()
        sentence.is_correct = True
        sentence.save(update_fields=["is_correct"])
        return Response({"status": "success"})


class MediaAssetViewSet(viewsets.ModelViewSet):
    queryset = MediaAsset.objects.select_related("chapter", "word", "sentence").all()
    serializer_class = MediaAssetSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = _get_effective_user(self.request)
        return (
            MediaAsset.objects.select_related("chapter", "word", "sentence")
            .filter(owner=user)
            .order_by("-updated_at", "-id")
        )

    def perform_create(self, serializer):
        serializer.save(owner=_get_effective_user(self.request))


@extend_schema(tags=["progress"], responses=ProgressResponseSerializer)
@api_view(["GET"])
def get_progress(request):
    user = _get_effective_user(request)
    chapters = Chapter.objects.filter(owner=user).order_by("id")
    progress_data = []

    for chapter in chapters:
        words = Word.objects.filter(chapter=chapter)
        sentences = Sentence.objects.filter(chapter=chapter)

        total_words = words.count()
        called_words = words.filter(is_called=True).count()
        collect_words = words.filter(is_collect=True).count()

        total_sentences = sentences.count()
        called_sentences = sentences.filter(is_called=True).count()
        collect_sentences = sentences.filter(is_collect=True).count()

        total_items = total_words + total_sentences
        called_items = called_words + called_sentences
        collect_items = collect_words + collect_sentences

        progress = (called_items / total_items) * 100 if total_items else 0
        accuracy = (collect_items / total_items) * 100 if total_items else 0

        progress_data.append(
            {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "progress": progress,
                "accuracy": accuracy,
                "total_words": total_words,
                "called_words": called_words,
                "collect_words": collect_words,
                "total_sentences": total_sentences,
                "called_sentences": called_sentences,
                "collect_sentences": collect_sentences,
                "total_items": total_items,
                "called_items": called_items,
                "collect_items": collect_items,
            }
        )

    completed_chapters = sum(1 for item in progress_data if item["progress"] == 100)
    overall_progress = (
        sum(item["accuracy"] for item in progress_data) / len(progress_data) if progress_data else 0
    )

    return Response(
        {
            "progress_data": progress_data,
            "completed_chapters": completed_chapters,
            "overall_progress": overall_progress,
        }
    )


@extend_schema(
    tags=["chapters"],
    responses={
        200: NextChapterResponseSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["GET"])
def get_next_chapter(request):
    user = _get_effective_user(request)
    chapters = Chapter.objects.filter(owner=user).order_by("id")
    if not chapters.exists():
        return Response({"detail": "No chapters found."}, status=status.HTTP_404_NOT_FOUND)

    for chapter in chapters:
        words = Word.objects.filter(chapter=chapter)
        total_words = words.count()
        called_words = words.filter(is_called=True).count()
        progress = (called_words / total_words) * 100 if total_words else 0
        if progress < 100:
            return Response({"id": chapter.id, "title": chapter.title})

    last = chapters.last()
    return Response({"id": last.id, "title": last.title})


@extend_schema(
    tags=["review"],
    parameters=[
        OpenApiParameter(
            name="limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="반환할 복습 후보 개수. 기본 12, 최대 50",
            required=False,
        )
    ],
    responses=ReviewQueueItemSerializer(many=True),
)
@api_view(["GET"])
def get_review_queue(request):
    user = _get_effective_user(request)
    try:
        limit = int(request.GET.get("limit", "12"))
    except ValueError:
        limit = 12
    limit = max(1, min(limit, 50))

    candidates = []
    for sentence in (
        Sentence.objects.select_related("chapter")
        .filter(chapter__owner=user)
        .order_by("id")
    ):
        recent_attempts = list(
            PronunciationAttempt.objects.filter(sentence_id=sentence.id, user=user)
            .order_by("-created_at")[:3]
        )
        if recent_attempts:
            recent_scores = [float(a.score_percent or 0.0) for a in recent_attempts]
            recent_avg = sum(recent_scores) / len(recent_scores)
            last_score = recent_scores[0]
            priority = (100.0 - recent_avg) * 0.7 + (100.0 - last_score) * 0.3
            reason = "최근 발음 점수가 낮아 복습이 필요합니다."
        else:
            # No attempts yet: schedule as medium-priority practice.
            recent_avg = None
            last_score = None
            priority = 45.0
            reason = "아직 발음 평가 기록이 없어 첫 복습을 권장합니다."

        if sentence.is_collect and (recent_avg is not None and recent_avg >= 85):
            continue

        candidates.append(
            {
                "sentence_id": sentence.id,
                "chapter_id": sentence.chapter_id,
                "chapter_title": sentence.chapter.title,
                "difficulty": sentence.chapter.difficulty,
                "context_tag": sentence.chapter.context_tag,
                "korean_sentence": sentence.korean_sentence,
                "north_korean_sentence": sentence.north_korean_sentence,
                "sentence_accuracy_ratio": round(float(sentence.accuracy or 0.0), 4),
                "last_score_percent": round(last_score, 2) if last_score is not None else None,
                "recent_avg_score_percent": round(recent_avg, 2) if recent_avg is not None else None,
                "priority_score": round(priority, 2),
                "reason": reason,
            }
        )

    candidates.sort(key=lambda item: item["priority_score"], reverse=True)
    return Response(candidates[:limit])


@extend_schema(tags=["words"], responses=WordSerializer(many=True))
@api_view(["GET"])
def get_saved_words(request):
    user = _get_effective_user(request)
    serializer = WordSerializer(
        Word.objects.filter(chapter__owner=user, is_correct=True).order_by("id"),
        many=True,
        context=_serializer_context(request),
    )
    return Response(serializer.data)


@extend_schema(tags=["sentences"], responses=SentenceSerializer(many=True))
@api_view(["GET"])
def get_saved_sentences(request):
    user = _get_effective_user(request)
    serializer = SentenceSerializer(
        Sentence.objects.filter(chapter__owner=user, is_correct=True).order_by("id"),
        many=True,
        context=_serializer_context(request),
    )
    return Response(serializer.data)


@extend_schema(
    tags=["words"],
    request=WordUpdateRequestSerializer,
    responses={
        200: WordSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["POST", "PATCH"])
def update_word(request, word_id):
    user = _get_effective_user(request)
    try:
        word = Word.objects.get(pk=word_id, chapter__owner=user)
    except Word.DoesNotExist:
        return Response({"detail": "Word not found."}, status=status.HTTP_404_NOT_FOUND)

    # Accept both snake_case and camelCase from different Flutter screens.
    if "is_correct" in request.data:
        word.is_correct = bool(request.data.get("is_correct"))

    if "is_collect" in request.data:
        word.is_collect = bool(request.data.get("is_collect"))
    elif "isCollect" in request.data:
        word.is_collect = bool(request.data.get("isCollect"))

    word.save()
    return Response(WordSerializer(word, context=_serializer_context(request)).data)


@extend_schema(
    tags=["words"],
    request=None,
    responses={
        200: StatusResponseSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["POST"])
def mark_word_as_called(request, word_id):
    user = _get_effective_user(request)
    try:
        word = Word.objects.get(pk=word_id, chapter__owner=user)
    except Word.DoesNotExist:
        return Response({"detail": "Word not found."}, status=status.HTTP_404_NOT_FOUND)

    word.is_called = True
    word.save(update_fields=["is_called"])
    return Response({"status": "success"})


@extend_schema(
    tags=["sentences"],
    request=SentenceUpdateRequestSerializer,
    responses={
        200: SentenceSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["POST", "PATCH"])
def update_sentence(request, sentence_id):
    user = _get_effective_user(request)
    try:
        sentence = Sentence.objects.get(pk=sentence_id, chapter__owner=user)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    if "is_correct" in request.data:
        sentence.is_correct = bool(request.data.get("is_correct"))

    if "is_collect" in request.data:
        sentence.is_collect = bool(request.data.get("is_collect"))
    elif "isCollect" in request.data:
        sentence.is_collect = bool(request.data.get("isCollect"))

    sentence.save()
    return Response(SentenceSerializer(sentence, context=_serializer_context(request)).data)


@extend_schema(
    tags=["sentences"],
    request=None,
    responses={
        200: StatusResponseSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["POST"])
def mark_sentence_as_called(request, sentence_id):
    user = _get_effective_user(request)
    try:
        sentence = Sentence.objects.get(pk=sentence_id, chapter__owner=user)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    sentence.is_called = True
    sentence.save(update_fields=["is_called"])
    return Response({"status": "success"})


@extend_schema(
    tags=["sentences"],
    request=SentenceAccuracyRequestSerializer,
    responses={
        200: SentenceSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["PUT", "POST"])
def update_sentence_accuracy(request, sentence_id):
    user = _get_effective_user(request)
    try:
        sentence = Sentence.objects.get(pk=sentence_id, chapter__owner=user)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    accuracy = request.data.get("accuracy", sentence.accuracy)
    sentence.accuracy = float(accuracy)
    sentence.save(update_fields=["accuracy"])
    return Response(SentenceSerializer(sentence, context=_serializer_context(request)).data)


@extend_schema(
    tags=["sentences"],
    request=SentenceAccuracyRequestSerializer,
    responses={
        200: SentenceWithRecognizedTextSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["PUT"])
def update_sentence_accuracy_and_text(request, sentence_id):
    user = _get_effective_user(request)
    try:
        sentence = Sentence.objects.get(pk=sentence_id, chapter__owner=user)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    accuracy = request.data.get("accuracy", sentence.accuracy)
    recognized_text = request.data.get("recognized_text", "")

    sentence.accuracy = float(accuracy)
    sentence.save(update_fields=["accuracy"])

    data = SentenceSerializer(sentence, context=_serializer_context(request)).data
    data["recognized_text"] = recognized_text
    return Response(data)


@extend_schema(
    tags=["chapters"],
    responses={
        200: LearningProgressResponseSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["GET"])
def get_chapter_learning_progress(request, chapter_id):
    user = _get_effective_user(request)
    try:
        chapter = Chapter.objects.get(pk=chapter_id, owner=user)
    except Chapter.DoesNotExist:
        return Response({"detail": "Chapter not found."}, status=status.HTTP_404_NOT_FOUND)

    words = Word.objects.filter(chapter=chapter)
    sentences = Sentence.objects.filter(chapter=chapter)

    total_words = words.count()
    called_words = words.filter(is_called=True).count()
    word_progress = (called_words / total_words) * 100 if total_words else 0

    total_sentences = sentences.count()
    called_sentences = sentences.filter(is_called=True).count()
    sentence_progress = (called_sentences / total_sentences) * 100 if total_sentences else 0

    return Response(
        {
            "progress": (word_progress + sentence_progress) / 2,
            "words": WordSerializer(
                words,
                many=True,
                context=_serializer_context(request),
            ).data,
            "sentences": SentenceSerializer(
                sentences,
                many=True,
                context=_serializer_context(request),
            ).data,
        }
    )


@extend_schema(tags=["chapters"], responses=SentenceSerializer(many=True))
@api_view(["GET"])
def get_chapter_evaluation_results(request, chapter_id):
    user = _get_effective_user(request)
    sentences = Sentence.objects.filter(chapter_id=chapter_id, chapter__owner=user).order_by("id")
    serializer = SentenceSerializer(
        sentences,
        many=True,
        context=_serializer_context(request),
    )
    return Response(serializer.data)


def _fallback_chat_reply(user_message):
    prompt = user_message.strip()
    if not prompt:
        return "질문을 입력해 주세요."

    if "인사" in prompt:
        return (
            "남한은 보통 '안녕하세요'를, 북한은 '안녕하십니까'를 자주 씁니다. "
            "격식과 상황에 따라 둘 다 의미는 같지만 어감 차이가 있습니다."
        )
    if "음식" in prompt or "요리" in prompt:
        return (
            "음식 관련 어휘는 지역별 차이가 큽니다. 예를 들어 남한 '라면'은 "
            "북한에서 '국수'로 표현되는 경우가 있습니다."
        )
    if "발음" in prompt or "억양" in prompt:
        return (
            "발음 비교는 문장 단위로 하는 게 가장 정확합니다. 짧은 문장을 2~3번 반복해 "
            "강세와 길이를 맞추는 방식으로 연습해 보세요."
        )

    return (
        "현재 AI 실시간 응답 한도를 초과해 기본 답변으로 안내 중입니다. "
        "질문을 더 구체적으로 주시면 남북한 어휘/표현 차이를 예시 중심으로 정리해 드릴게요."
    )


def _chat_with_openai(user_message):
    openai_api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    openai_model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    endpoint = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert in North and South Korean languages. "
                    "Answer in Korean unless explicitly asked otherwise."
                ),
            },
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.4,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {openai_api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")

    data = json.loads(raw)
    choices = data.get("choices", [])
    if not choices:
        raise ValueError("OpenAI returned no choices.")

    message = choices[0].get("message", {})
    answer = (message.get("content") or "").strip()
    if not answer:
        raise ValueError("OpenAI returned empty content.")
    return answer


@extend_schema(
    tags=["chat"],
    request=ChatRequestSerializer,
    responses={
        200: ChatResponseSerializer,
        400: DetailResponseSerializer,
        502: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Gemini 응답이 비어 있거나 비정상일 때의 raw payload",
        ),
    },
)
@api_view(["POST"])
def chat_with_gemini(request):
    user_message = (request.data.get("message") or "").strip()
    if not user_message:
        return Response(
            {"detail": "message is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    gemini_api_key = getattr(settings, "GEMINI_API_KEY", "")
    openai_api_key = getattr(settings, "OPENAI_API_KEY", "")
    openai_enabled = bool(openai_api_key)
    # Prefer OpenAI first so chat keeps working even when Gemini key is invalid.
    if openai_enabled:
        try:
            answer = _chat_with_openai(user_message)
            return Response({"reply": answer, "fallback": False, "provider": "openai"})
        except Exception:
            pass

    if not gemini_api_key:
        return Response(
            {"reply": _fallback_chat_reply(user_message), "fallback": True, "provider": "local"},
            status=status.HTTP_200_OK,
        )

    gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"
        f"?key={urllib.parse.quote(gemini_api_key)}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You are an expert in North and South Korean languages. "
                            "Answer in Korean unless explicitly asked otherwise."
                        )
                    },
                    {"text": user_message},
                ]
            }
        ]
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if openai_enabled:
            try:
                answer = _chat_with_openai(user_message)
                return Response({"reply": answer, "fallback": True, "provider": "openai"})
            except Exception:
                pass
        return Response(
            {
                "reply": _fallback_chat_reply(user_message),
                "fallback": True,
                "provider": "local",
                "reason": "gemini_http_error",
                "error": detail[:300],
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:  # pragma: no cover - network path
        if openai_enabled:
            try:
                answer = _chat_with_openai(user_message)
                return Response({"reply": answer, "fallback": True, "provider": "openai"})
            except Exception:
                pass
        return Response(
            {
                "reply": _fallback_chat_reply(user_message),
                "fallback": True,
                "provider": "local",
                "reason": "gemini_request_error",
                "error": str(exc)[:300],
            },
            status=status.HTTP_200_OK,
        )

    data = json.loads(raw)
    candidates = data.get("candidates", [])
    if not candidates:
        if openai_enabled:
            try:
                answer = _chat_with_openai(user_message)
                return Response({"reply": answer, "fallback": True, "provider": "openai"})
            except Exception:
                pass
        return Response(
            {"detail": "Gemini returned no candidates.", "raw": data},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text_chunks = [part.get("text", "") for part in parts if part.get("text")]
    answer = "\n".join(text_chunks).strip()

    if not answer:
        if openai_enabled:
            try:
                answer = _chat_with_openai(user_message)
                return Response({"reply": answer, "fallback": True, "provider": "openai"})
            except Exception:
                pass
        return Response(
            {"detail": "Gemini returned empty content.", "raw": data},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({"reply": answer})


def _normalize_text(text):
    text = (text or "").lower()
    text = re.sub(r"[^\w\s가-힣]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _levenshtein_distance(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + cost,
            ))
        prev = curr
    return prev[-1]


def _token_recall(reference, hypothesis):
    ref_tokens = _normalize_text(reference).split()
    hyp_tokens = _normalize_text(hypothesis).split()
    if not ref_tokens:
        return 0.0
    if not hyp_tokens:
        return 0.0

    ref_counts = {}
    for token in ref_tokens:
        ref_counts[token] = ref_counts.get(token, 0) + 1

    matched = 0
    for token in hyp_tokens:
        if ref_counts.get(token, 0) > 0:
            matched += 1
            ref_counts[token] -= 1
    return matched / len(ref_tokens)


def _build_pronunciation_feedback(score_percent, reference_text, transcript):
    if score_percent >= 90:
        level = "매우 정확합니다."
    elif score_percent >= 75:
        level = "전반적으로 좋습니다."
    elif score_percent >= 55:
        level = "중간 수준입니다."
    else:
        level = "개선이 필요합니다."

    ref_tokens = set(_normalize_text(reference_text).split())
    hyp_tokens = set(_normalize_text(transcript).split())
    missing = [token for token in ref_tokens if token and token not in hyp_tokens]
    missing_hint = ", ".join(missing[:5]) if missing else "핵심 단어 누락은 크지 않습니다."

    return f"{level} 놓친 단어 후보: {missing_hint}"


def _score_level(score_percent):
    if score_percent >= 90:
        return "excellent"
    if score_percent >= 75:
        return "good"
    if score_percent >= 55:
        return "fair"
    return "needs_improvement"


def _stddev(values):
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _build_recent_attempt_stats(sentence, user=None, window=3):
    if not sentence:
        return {
            "recent_window_size": window,
            "recent_attempt_scores": [],
            "recent_avg_score": None,
            "recent_score_stddev": None,
            "recent_avg_pitch_score": None,
            "recent_avg_speed_score": None,
            "recent_avg_volume_score": None,
        }

    q = PronunciationAttempt.objects.filter(sentence_id=sentence.id)
    if user is not None:
        q = q.filter(user=user)
    attempts = list(q.order_by("-created_at")[:window])
    if not attempts:
        return {
            "recent_window_size": window,
            "recent_attempt_scores": [],
            "recent_avg_score": None,
            "recent_score_stddev": None,
            "recent_avg_pitch_score": None,
            "recent_avg_speed_score": None,
            "recent_avg_volume_score": None,
        }

    scores = [float(a.score_percent or 0.0) for a in attempts]
    pitch_scores = [float(a.pitch_score) for a in attempts if a.pitch_score is not None]
    speed_scores = [float(a.speed_score) for a in attempts if a.speed_score is not None]
    volume_scores = [float(a.volume_curve_similarity) for a in attempts if a.volume_curve_similarity is not None]
    return {
        "recent_window_size": window,
        "recent_attempt_scores": [round(v, 2) for v in scores],
        "recent_avg_score": round(sum(scores) / len(scores), 2),
        "recent_score_stddev": (
            round(_stddev(scores), 2) if _stddev(scores) is not None else None
        ),
        "recent_avg_pitch_score": (
            round(sum(pitch_scores) / len(pitch_scores), 4) if pitch_scores else None
        ),
        "recent_avg_speed_score": (
            round(sum(speed_scores) / len(speed_scores), 4) if speed_scores else None
        ),
        "recent_avg_volume_score": (
            round(sum(volume_scores) / len(volume_scores), 4) if volume_scores else None
        ),
    }


def _score_speed_by_duration(user_duration_sec, reference_duration_sec):
    if user_duration_sec <= 0 or reference_duration_sec <= 0:
        return 0.0
    ratio = user_duration_sec / reference_duration_sec
    # Ratio 1.0 is ideal. 0.6~1.5 still acceptable with gradual penalty.
    if ratio < 0.6 or ratio > 1.8:
        return 0.0
    score = max(0.0, 1.0 - abs(ratio - 1.0) / 0.5)
    return round(score, 4)


def _score_pitch(f0_values):
    if np is None:
        return 0.0, None, None
    if len(f0_values) < 6:
        return 0.0, None, None

    median_f0 = float(np.median(f0_values))
    std_f0 = float(np.std(f0_values))

    # Median range score: prefer 95~260 Hz range for Korean adult speech.
    if median_f0 < 75 or median_f0 > 320:
        median_score = 0.0
    elif 95 <= median_f0 <= 260:
        median_score = 1.0
    elif median_f0 < 95:
        median_score = (median_f0 - 75) / 20.0
    else:
        median_score = (320 - median_f0) / 60.0

    # Variation score: too flat(<12Hz) or too unstable(>120Hz) gets penalty.
    if std_f0 < 12:
        var_score = std_f0 / 12.0
    elif std_f0 <= 90:
        var_score = 1.0
    elif std_f0 >= 140:
        var_score = 0.0
    else:
        var_score = (140 - std_f0) / 50.0

    pitch_score = max(0.0, min(1.0, 0.6 * median_score + 0.4 * var_score))
    return round(pitch_score, 4), round(median_f0, 2), round(std_f0, 2)


def _resample_curve(curve, target_points=64):
    if not curve:
        return []
    if np is None:
        if len(curve) >= target_points:
            step = max(1, len(curve) // target_points)
            return [round(float(curve[i]), 4) for i in range(0, len(curve), step)][:target_points]
        padded = list(curve) + [curve[-1]] * (target_points - len(curve))
        return [round(float(v), 4) for v in padded]
    arr = np.array(curve, dtype=np.float32)
    if arr.size == 1:
        return [round(float(arr[0]), 4)] * target_points
    x_old = np.linspace(0.0, 1.0, num=arr.size)
    x_new = np.linspace(0.0, 1.0, num=target_points)
    out = np.interp(x_new, x_old, arr)
    return [round(float(v), 4) for v in out]


def _analyze_pitch_volume(samples, sample_rate):
    if np is None:
        return {"pitch_curve": [], "volume_curve": [], "f0_values": []}
    frame_len = int(0.04 * sample_rate)  # 40ms
    hop_len = int(0.01 * sample_rate)    # 10ms
    if frame_len <= 0 or hop_len <= 0 or len(samples) < frame_len:
        return {
            "pitch_curve": [],
            "volume_curve": [],
            "f0_values": [],
        }

    min_hz = 75.0
    max_hz = 350.0
    min_lag = max(1, int(sample_rate / max_hz))
    max_lag = max(min_lag + 1, int(sample_rate / min_hz))

    f0_values = []
    pitch_curve = []
    volume_curve = []
    for start in range(0, len(samples) - frame_len + 1, hop_len):
        frame = samples[start : start + frame_len]
        rms = math.sqrt(float(np.mean(frame * frame)) + 1e-12)
        volume_curve.append(rms)

        if rms < 0.008:
            pitch_curve.append(0.0)
            continue

        frame = frame - np.mean(frame)
        autocorr = np.correlate(frame, frame, mode="full")[frame_len - 1 :]
        if max_lag >= len(autocorr):
            pitch_curve.append(0.0)
            continue

        search = autocorr[min_lag:max_lag]
        if search.size == 0:
            pitch_curve.append(0.0)
            continue
        lag_offset = int(np.argmax(search))
        lag = min_lag + lag_offset
        peak = float(search[lag_offset])
        if peak <= 0:
            pitch_curve.append(0.0)
            continue

        f0 = sample_rate / lag
        if min_hz <= f0 <= max_hz:
            f0_values.append(float(f0))
            pitch_curve.append((f0 - min_hz) / (max_hz - min_hz))
        else:
            pitch_curve.append(0.0)

    if volume_curve:
        vmax = max(volume_curve) or 1e-6
        volume_curve = [min(1.0, float(v / vmax)) for v in volume_curve]

    return {
        "pitch_curve": _resample_curve(pitch_curve, target_points=64),
        "volume_curve": _resample_curve(volume_curve, target_points=64),
        "f0_values": f0_values,
    }


def _curve_similarity(curve_a, curve_b):
    if not curve_a or not curve_b:
        return None
    n = min(len(curve_a), len(curve_b))
    if n <= 0:
        return None
    if np is None:
        diffs = [abs(float(curve_a[i]) - float(curve_b[i])) for i in range(n)]
        mae = sum(diffs) / n
        return round(max(0.0, 1.0 - mae), 4)
    a = np.array(curve_a[:n], dtype=np.float32)
    b = np.array(curve_b[:n], dtype=np.float32)
    mae = float(np.mean(np.abs(a - b)))
    return round(max(0.0, 1.0 - mae), 4)


def _synthesize_reference_tts(text):
    if gTTS is None:
        raise RuntimeError("gTTS is not installed")
    buf = io.BytesIO()
    tts = gTTS(text=text, lang="ko", slow=False)
    tts.write_to_fp(buf)
    return buf.getvalue()


def _build_audio_feedback(score_percent, speed_score, pitch_score, volume_score):
    if score_percent >= 90:
        level = "매우 우수합니다."
    elif score_percent >= 75:
        level = "좋습니다."
    elif score_percent >= 55:
        level = "보통입니다."
    else:
        level = "개선이 필요합니다."

    tips = []
    if (speed_score or 0.0) < 0.6:
        tips.append("말하기 속도를 기준 발음과 비슷하게 맞춰 보세요.")
    if (pitch_score or 0.0) < 0.6:
        tips.append("억양의 높낮이 변화를 조금 더 살려 보세요.")
    if (volume_score or 0.0) < 0.6:
        tips.append("문장 전체에서 음량을 더 안정적으로 유지해 보세요.")
    if not tips:
        tips.append("현재 속도/피치/음량 균형이 안정적입니다.")

    return f"{level} " + " ".join(tips)


def _extract_audio_metrics(audio_bytes, mime_type, file_name=None):
    if AudioSegment is None or imageio_ffmpeg is None or np is None:
        raise RuntimeError("audio metric dependencies are not installed")
    format_hint = None
    if "/" in (mime_type or ""):
        format_hint = mime_type.split("/", 1)[1].split(";")[0].strip().lower()
    format_map = {
        "mpeg": "mp3",
        "x-wav": "wav",
        "mp4": "m4a",
        "m4a": "m4a",
        "x-m4a": "m4a",
        "quicktime": "mov",
        "3gpp": "3gp",
        "webm": "webm",
        "ogg": "ogg",
    }
    format_hint = format_map.get(format_hint, format_hint)

    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
    decode_errors = []
    candidates = [
        format_hint,
        None,
        "m4a",
        "mp4",
        "ipod",
        "aac",
        "3gp",
        "mov",
        "webm",
        "ogg",
        "wav",
        "mp3",
    ]
    seen = set()
    segment = None
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=candidate)
            break
        except Exception as exc:
            decode_errors.append(f"{candidate or 'auto'}:{exc}")

    if segment is None:
        # iOS Voice Memos(.m4a) may decode better via file-path probing than memory stream.
        suffix = ".bin"
        if file_name and "." in file_name:
            suffix = "." + file_name.rsplit(".", 1)[1].lower()
        elif format_hint:
            suffix = f".{format_hint}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            try:
                segment = AudioSegment.from_file(tmp.name)
            except Exception as exc:
                decode_errors.append(f"file-auto:{exc}")

    if segment is None:
        # Last-resort: force transcode via ffmpeg and read as wav.
        suffix = ".bin"
        if file_name and "." in file_name:
            suffix = "." + file_name.rsplit(".", 1)[1].lower()
        elif format_hint:
            suffix = f".{format_hint}"
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = str(Path(tmpdir) / f"src{suffix}")
            out_path = str(Path(tmpdir) / "normalized.wav")
            Path(src_path).write_bytes(audio_bytes)
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i",
                src_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                out_path,
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if proc.returncode == 0 and Path(out_path).exists():
                try:
                    segment = AudioSegment.from_wav(out_path)
                except Exception as exc:
                    decode_errors.append(f"ffmpeg-wav-read:{exc}")
            else:
                err = (proc.stderr or proc.stdout or "").strip()
                decode_errors.append(f"ffmpeg-transcode:{err[:300]}")

    if segment is None:
        raise ValueError("Audio decode failed: " + " | ".join(decode_errors[:5]))
    if len(segment) <= 0:
        raise ValueError("Empty decoded audio")

    segment = segment.set_channels(1).set_frame_rate(16000)
    duration_sec = len(segment) / 1000.0
    if duration_sec <= 0:
        raise ValueError("Invalid audio duration")

    raw = segment.get_array_of_samples()
    samples = np.array(raw).astype(np.float32)
    max_val = float(1 << (8 * segment.sample_width - 1))
    if max_val <= 0:
        raise ValueError("Invalid sample width")
    samples = samples / max_val

    analysis = _analyze_pitch_volume(samples, segment.frame_rate)
    f0_values = analysis["f0_values"]
    pitch_score, pitch_median_hz, pitch_std_hz = _score_pitch(f0_values)

    return {
        "duration_sec": round(duration_sec, 3),
        "pitch_score": pitch_score,
        "pitch_median_hz": pitch_median_hz,
        "pitch_std_hz": pitch_std_hz,
        "voiced_frames": len(f0_values),
        "pitch_curve": analysis["pitch_curve"],
        "volume_curve": analysis["volume_curve"],
    }


def _transcribe_with_gemini(audio_bytes, mime_type, model_name, api_key):
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        f"?key={urllib.parse.quote(api_key)}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "다음 한국어 음성을 정확히 받아적어 주세요. "
                            "설명 없이 전사 텍스트만 반환하세요."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(audio_bytes).decode("utf-8"),
                        }
                    },
                ]
            }
        ]
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    data = json.loads(raw)
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates from Gemini")

    parts = candidates[0].get("content", {}).get("parts", [])
    text_chunks = [part.get("text", "") for part in parts if part.get("text")]
    transcript = "\n".join(text_chunks).strip()
    if not transcript:
        raise ValueError("Empty transcript from Gemini")
    return transcript


@extend_schema(
    tags=["pronunciation"],
    request=PronunciationRequestSerializer,
    responses={
        200: PronunciationEvaluationResponseSerializer,
        400: DetailResponseSerializer,
        404: DetailResponseSerializer,
        500: DetailResponseSerializer,
    },
)
@api_view(["POST"])
def evaluate_pronunciation(request):
    user = _get_effective_user(request)
    reference_text = (request.data.get("reference_text") or "").strip()
    sentence_id = request.data.get("sentence_id")

    if not reference_text:
        return Response(
            {"detail": "reference_text is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    speech_model = "audio-direct-v1"

    audio_file = request.FILES.get("audio")
    if not audio_file:
        return Response(
            {"detail": "audio file is required for pronunciation evaluation."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mime_type = audio_file.content_type or "audio/webm"
    audio_bytes = audio_file.read()
    if not audio_bytes:
        return Response(
            {"detail": "Uploaded audio is empty."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    transcript = ""
    char_similarity = 0.0
    token_similarity = 0.0
    text_score = 0.0

    try:
        logger.info(
            "Pronunciation eval request: name=%s content_type=%s size=%d",
            getattr(audio_file, "name", ""),
            mime_type,
            len(audio_bytes),
        )
        audio_metrics = _extract_audio_metrics(audio_bytes, mime_type, audio_file.name)
    except Exception as exc:
        logger.warning(
            "Pronunciation audio decode failed: name=%s content_type=%s size=%d error=%s",
            getattr(audio_file, "name", ""),
            mime_type,
            len(audio_bytes),
            str(exc)[:500],
        )
        return Response(
            {"detail": "Failed to analyze user audio.", "error": str(exc)[:1000]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        ref_audio_bytes = _synthesize_reference_tts(reference_text)
        reference_audio_metrics = _extract_audio_metrics(ref_audio_bytes, "audio/mpeg")
    except Exception as exc:
        return Response(
            {"detail": "Failed to synthesize/analyze reference TTS audio.", "error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    pitch_curve_similarity = _curve_similarity(
        audio_metrics["pitch_curve"],
        reference_audio_metrics["pitch_curve"],
    )
    volume_curve_similarity = _curve_similarity(
        audio_metrics["volume_curve"],
        reference_audio_metrics["volume_curve"],
    )

    speed_score = _score_speed_by_duration(
        float(audio_metrics["duration_sec"]),
        float(reference_audio_metrics["duration_sec"]),
    )
    pitch_score = float(pitch_curve_similarity if pitch_curve_similarity is not None else 0.0)
    volume_score = float(volume_curve_similarity if volume_curve_similarity is not None else 0.0)

    speed_weight = 0.35
    pitch_weight = 0.45
    volume_weight = 0.20
    accuracy_ratio = (
        speed_weight * speed_score
        + pitch_weight * pitch_score
        + volume_weight * volume_score
    )
    score_rule = {
        "mode": "audio_only",
        "speed_weight": speed_weight,
        "pitch_weight": pitch_weight,
        "volume_weight": volume_weight,
        "bands": {
            "excellent": ">= 90",
            "good": ">= 75",
            "fair": ">= 55",
            "needs_improvement": "< 55",
        },
    }

    accuracy_ratio = max(0.0, min(1.0, accuracy_ratio))
    score_percent = round(accuracy_ratio * 100.0, 2)

    feedback = _build_audio_feedback(score_percent, speed_score, pitch_score, volume_score)

    sentence = None
    if sentence_id:
        try:
            sentence = Sentence.objects.get(pk=sentence_id, chapter__owner=user)
            # Keep the best score for stability across repeated retries.
            sentence.accuracy = max(float(sentence.accuracy or 0.0), float(accuracy_ratio))
            sentence.save(update_fields=["accuracy"])
        except Sentence.DoesNotExist:
            return Response(
                {"detail": "Sentence not found.", "transcript": transcript},
                status=status.HTTP_404_NOT_FOUND,
            )

    attempt = PronunciationAttempt.objects.create(
        user=user,
        sentence=sentence,
        reference_text=reference_text,
        transcript=transcript,
        score_percent=score_percent,
        text_score=round(text_score, 4),
        speed_score=round(speed_score, 4),
        pitch_score=round(pitch_score, 4),
        pitch_curve_similarity=pitch_curve_similarity,
        volume_curve_similarity=volume_curve_similarity,
        audio_duration_sec=audio_metrics["duration_sec"],
        syllables_per_sec=None,
        pitch_median_hz=audio_metrics["pitch_median_hz"],
        pitch_std_hz=audio_metrics["pitch_std_hz"],
        voiced_frames=audio_metrics["voiced_frames"],
        user_pitch_curve=audio_metrics["pitch_curve"],
        user_volume_curve=audio_metrics["volume_curve"],
        reference_pitch_curve=reference_audio_metrics["pitch_curve"],
        reference_volume_curve=reference_audio_metrics["volume_curve"],
    )

    sentence_attempts_count = (
        PronunciationAttempt.objects.filter(sentence_id=sentence.id, user=user).count()
        if sentence
        else None
    )
    sentence_best_score = (
        round(float(sentence.accuracy or 0.0) * 100.0, 2) if sentence else None
    )
    recent_stats = _build_recent_attempt_stats(sentence, user=user, window=3)

    pitch_verdict = None
    if audio_metrics:
        pscore = pitch_score
        if pscore >= 0.8:
            pitch_verdict = "stable"
        elif pscore >= 0.55:
            pitch_verdict = "moderate"
        else:
            pitch_verdict = "unstable"

    return Response(
        {
            "transcript": transcript,
            "accuracy_ratio": round(accuracy_ratio, 4),
            "score_percent": score_percent,
            "char_similarity": round(char_similarity, 4),
            "token_similarity": round(token_similarity, 4),
            "text_score": round(text_score, 4),
            "audio_metrics_available": True,
            "speed_score": round(speed_score, 4),
            "pitch_score": round(pitch_score, 4),
            "volume_score": round(volume_score, 4),
            "audio_duration_sec": audio_metrics["duration_sec"],
            "reference_duration_sec": reference_audio_metrics["duration_sec"],
            "syllables_per_sec": None,
            "pitch_median_hz": audio_metrics["pitch_median_hz"],
            "pitch_std_hz": audio_metrics["pitch_std_hz"],
            "user_pitch_curve": audio_metrics["pitch_curve"],
            "user_volume_curve": audio_metrics["volume_curve"],
            "reference_pitch_curve": reference_audio_metrics["pitch_curve"],
            "reference_volume_curve": reference_audio_metrics["volume_curve"],
            "pitch_curve_similarity": pitch_curve_similarity,
            "volume_curve_similarity": volume_curve_similarity,
            "pitch_verdict": pitch_verdict,
            "attempt_id": attempt.id,
            "sentence_attempts_count": sentence_attempts_count,
            "sentence_best_score": sentence_best_score,
            "recent_window_size": recent_stats["recent_window_size"],
            "recent_attempt_scores": recent_stats["recent_attempt_scores"],
            "recent_avg_score": recent_stats["recent_avg_score"],
            "recent_score_stddev": recent_stats["recent_score_stddev"],
            "recent_avg_pitch_score": recent_stats["recent_avg_pitch_score"],
            "recent_avg_speed_score": recent_stats["recent_avg_speed_score"],
            "recent_avg_volume_score": recent_stats["recent_avg_volume_score"],
            "feedback": feedback,
            "model": speech_model,
            "score_level": _score_level(score_percent),
            "score_rule": score_rule,
        }
    )


@extend_schema(
    tags=["media-assets"],
    responses={
        200: OpenApiResponse(response=OpenApiTypes.BINARY, description="업로드된 이미지 바이너리"),
        404: DetailResponseSerializer,
    },
)
@api_view(["GET"])
def get_media_asset_file(request, asset_id):
    user = _get_effective_user(request)
    try:
        asset = MediaAsset.objects.get(pk=asset_id, owner=user)
    except MediaAsset.DoesNotExist:
        return Response({"detail": "Media asset not found."}, status=status.HTTP_404_NOT_FOUND)

    if not asset.image:
        return Response({"detail": "Media file is missing."}, status=status.HTTP_404_NOT_FOUND)

    asset.image.open("rb")
    file_name = Path(asset.image.name).name
    return FileResponse(asset.image, as_attachment=False, filename=file_name)


@extend_schema(
    tags=["sentences"],
    request=None,
    responses={
        200: ResetSentenceResponseSerializer,
        404: DetailResponseSerializer,
    },
)
@api_view(["POST"])
def reset_sentence_pronunciation(request, sentence_id):
    user = _get_effective_user(request)
    try:
        sentence = Sentence.objects.get(pk=sentence_id, chapter__owner=user)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    deleted, _ = PronunciationAttempt.objects.filter(sentence_id=sentence_id, user=user).delete()
    sentence.accuracy = 0.0
    sentence.save(update_fields=["accuracy"])
    return Response({"status": "ok", "deleted_attempts": deleted, "sentence_id": sentence.id})
