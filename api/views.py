import json
import base64
import io
import math
import re
import urllib.error
import urllib.parse
import urllib.request

import imageio_ffmpeg
import numpy as np
from gtts import gTTS
from pydub import AudioSegment
from django.db.models import Avg
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Chapter, Sentence, Word
from .serializers import ChapterSerializer, SentenceSerializer, WordSerializer


class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.all().order_by("id")
    serializer_class = ChapterSerializer

    @action(detail=True, methods=["get"])
    def words(self, request, pk=None):
        chapter = self.get_object()
        serializer = WordSerializer(chapter.words.all().order_by("id"), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def sentences(self, request, pk=None):
        chapter = self.get_object()
        serializer = SentenceSerializer(chapter.sentences.all().order_by("id"), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def incollect_words(self, request, pk=None):
        chapter = self.get_object()
        serializer = WordSerializer(chapter.words.filter(is_collect=False).order_by("id"), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def incollect_sentences(self, request, pk=None):
        chapter = self.get_object()
        serializer = SentenceSerializer(chapter.sentences.filter(is_collect=False).order_by("id"), many=True)
        return Response(serializer.data)

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

    @action(detail=True, methods=["post"])
    def save_word(self, request, pk=None):
        word = self.get_object()
        word.is_correct = True
        word.save(update_fields=["is_correct"])
        return Response({"status": "success"})


class SentenceViewSet(viewsets.ModelViewSet):
    queryset = Sentence.objects.all().order_by("id")
    serializer_class = SentenceSerializer

    @action(detail=True, methods=["post"])
    def save_sentence(self, request, pk=None):
        sentence = self.get_object()
        sentence.is_correct = True
        sentence.save(update_fields=["is_correct"])
        return Response({"status": "success"})


@api_view(["GET"])
def get_progress(request):
    chapters = Chapter.objects.all().order_by("id")
    progress_data = []

    for chapter in chapters:
        words = Word.objects.filter(chapter=chapter)
        total_words = words.count()
        called_words = words.filter(is_called=True).count()
        correct_words = words.filter(is_collect=True).count()

        progress = (called_words / total_words) * 100 if total_words else 0
        accuracy = (correct_words / total_words) * 100 if total_words else 0

        progress_data.append(
            {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "progress": progress,
                "accuracy": accuracy,
                "total_words": total_words,
                "called_words": called_words,
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


@api_view(["GET"])
def get_next_chapter(request):
    chapters = Chapter.objects.all().order_by("id")
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


@api_view(["GET"])
def get_saved_words(request):
    serializer = WordSerializer(Word.objects.filter(is_correct=True).order_by("id"), many=True)
    return Response(serializer.data)


@api_view(["GET"])
def get_saved_sentences(request):
    serializer = SentenceSerializer(Sentence.objects.filter(is_correct=True).order_by("id"), many=True)
    return Response(serializer.data)


@api_view(["POST", "PATCH"])
def update_word(request, word_id):
    try:
        word = Word.objects.get(pk=word_id)
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
    return Response(WordSerializer(word).data)


@api_view(["POST"])
def mark_word_as_called(request, word_id):
    try:
        word = Word.objects.get(pk=word_id)
    except Word.DoesNotExist:
        return Response({"detail": "Word not found."}, status=status.HTTP_404_NOT_FOUND)

    word.is_called = True
    word.save(update_fields=["is_called"])
    return Response({"status": "success"})


@api_view(["POST", "PATCH"])
def update_sentence(request, sentence_id):
    try:
        sentence = Sentence.objects.get(pk=sentence_id)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    if "is_correct" in request.data:
        sentence.is_correct = bool(request.data.get("is_correct"))

    if "is_collect" in request.data:
        sentence.is_collect = bool(request.data.get("is_collect"))
    elif "isCollect" in request.data:
        sentence.is_collect = bool(request.data.get("isCollect"))

    sentence.save()
    return Response(SentenceSerializer(sentence).data)


@api_view(["POST"])
def mark_sentence_as_called(request, sentence_id):
    try:
        sentence = Sentence.objects.get(pk=sentence_id)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    sentence.is_called = True
    sentence.save(update_fields=["is_called"])
    return Response({"status": "success"})


@api_view(["PUT", "POST"])
def update_sentence_accuracy(request, sentence_id):
    try:
        sentence = Sentence.objects.get(pk=sentence_id)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    accuracy = request.data.get("accuracy", sentence.accuracy)
    sentence.accuracy = float(accuracy)
    sentence.save(update_fields=["accuracy"])
    return Response(SentenceSerializer(sentence).data)


@api_view(["PUT"])
def update_sentence_accuracy_and_text(request, sentence_id):
    try:
        sentence = Sentence.objects.get(pk=sentence_id)
    except Sentence.DoesNotExist:
        return Response({"detail": "Sentence not found."}, status=status.HTTP_404_NOT_FOUND)

    accuracy = request.data.get("accuracy", sentence.accuracy)
    recognized_text = request.data.get("recognized_text", "")

    sentence.accuracy = float(accuracy)
    sentence.save(update_fields=["accuracy"])

    data = SentenceSerializer(sentence).data
    data["recognized_text"] = recognized_text
    return Response(data)


@api_view(["GET"])
def get_chapter_learning_progress(request, chapter_id):
    try:
        chapter = Chapter.objects.get(pk=chapter_id)
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
            "words": WordSerializer(words, many=True).data,
            "sentences": SentenceSerializer(sentences, many=True).data,
        }
    )


@api_view(["GET"])
def get_chapter_evaluation_results(request, chapter_id):
    sentences = Sentence.objects.filter(chapter_id=chapter_id).order_by("id")
    serializer = SentenceSerializer(sentences, many=True)
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
    openai_fallback_enabled = bool(getattr(settings, "OPENAI_FALLBACK_ENABLED", False))
    if not gemini_api_key and not (openai_api_key and openai_fallback_enabled):
        return Response(
            {"reply": _fallback_chat_reply(user_message), "fallback": True, "provider": "local"},
            status=status.HTTP_200_OK,
        )
    if not gemini_api_key and openai_api_key and openai_fallback_enabled:
        try:
            answer = _chat_with_openai(user_message)
            return Response({"reply": answer, "fallback": True, "provider": "openai"})
        except Exception:
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
        if (
            exc.code in (429, 500, 502, 503, 504) or "RESOURCE_EXHAUSTED" in detail
        ) and openai_api_key and openai_fallback_enabled:
            try:
                answer = _chat_with_openai(user_message)
                return Response({"reply": answer, "fallback": True, "provider": "openai"})
            except Exception:
                return Response(
                    {"reply": _fallback_chat_reply(user_message), "fallback": True, "provider": "local"},
                    status=status.HTTP_200_OK,
                )
        if exc.code == 429 or "RESOURCE_EXHAUSTED" in detail:
            return Response(
                {"reply": _fallback_chat_reply(user_message), "fallback": True, "provider": "local"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Gemini API request failed.", "error": detail},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as exc:  # pragma: no cover - network path
        if openai_api_key and openai_fallback_enabled:
            try:
                answer = _chat_with_openai(user_message)
                return Response({"reply": answer, "fallback": True, "provider": "openai"})
            except Exception:
                return Response(
                    {"reply": _fallback_chat_reply(user_message), "fallback": True, "provider": "local"},
                    status=status.HTTP_200_OK,
                )
        return Response(
            {"detail": "Gemini request error.", "error": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    data = json.loads(raw)
    candidates = data.get("candidates", [])
    if not candidates:
        return Response(
            {"detail": "Gemini returned no candidates.", "raw": data},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text_chunks = [part.get("text", "") for part in parts if part.get("text")]
    answer = "\n".join(text_chunks).strip()

    if not answer:
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


def _count_korean_syllables(text):
    return len(re.findall(r"[가-힣]", text or ""))


def _score_speed(syllables_per_sec):
    # Comfortable Korean speaking rate is roughly around 4~5.5 syllables/sec.
    if syllables_per_sec <= 0:
        return 0.0
    target = 4.7
    tolerance = 2.0
    distance = abs(syllables_per_sec - target)
    score = max(0.0, 1.0 - (distance / tolerance))
    return round(score, 4)


def _score_pitch(f0_values):
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
    arr = np.array(curve, dtype=np.float32)
    if arr.size == 1:
        return [round(float(arr[0]), 4)] * target_points
    x_old = np.linspace(0.0, 1.0, num=arr.size)
    x_new = np.linspace(0.0, 1.0, num=target_points)
    out = np.interp(x_new, x_old, arr)
    return [round(float(v), 4) for v in out]


def _analyze_pitch_volume(samples, sample_rate):
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
    a = np.array(curve_a[:n], dtype=np.float32)
    b = np.array(curve_b[:n], dtype=np.float32)
    mae = float(np.mean(np.abs(a - b)))
    return round(max(0.0, 1.0 - mae), 4)


def _synthesize_reference_tts(text):
    buf = io.BytesIO()
    tts = gTTS(text=text, lang="ko", slow=False)
    tts.write_to_fp(buf)
    return buf.getvalue()


def _extract_audio_metrics(audio_bytes, mime_type, transcript):
    format_hint = None
    if "/" in (mime_type or ""):
        format_hint = mime_type.split("/", 1)[1].split(";")[0].strip().lower()
    format_map = {
        "mpeg": "mp3",
        "x-wav": "wav",
        "mp4": "m4a",
        "webm": "webm",
        "ogg": "ogg",
    }
    format_hint = format_map.get(format_hint, format_hint)

    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
    segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format_hint)
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

    syllables = _count_korean_syllables(transcript)
    syllables_per_sec = syllables / max(duration_sec, 1e-6)
    speed_score = _score_speed(syllables_per_sec)

    analysis = _analyze_pitch_volume(samples, segment.frame_rate)
    f0_values = analysis["f0_values"]
    pitch_score, pitch_median_hz, pitch_std_hz = _score_pitch(f0_values)

    return {
        "duration_sec": round(duration_sec, 3),
        "korean_syllables": syllables,
        "syllables_per_sec": round(syllables_per_sec, 3),
        "speed_score": speed_score,
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


@api_view(["POST"])
def evaluate_pronunciation(request):
    reference_text = (request.data.get("reference_text") or "").strip()
    sentence_id = request.data.get("sentence_id")

    if not reference_text:
        return Response(
            {"detail": "reference_text is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    gemini_api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not gemini_api_key:
        return Response(
            {"detail": "GEMINI_API_KEY is not configured on server."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    speech_model = getattr(settings, "GEMINI_SPEECH_MODEL", "") or getattr(
        settings, "GEMINI_MODEL", "gemini-2.0-flash"
    )

    transcript = (request.data.get("recognized_text") or "").strip()
    audio_bytes = None
    mime_type = None

    audio_file = request.FILES.get("audio")
    if not transcript and not audio_file:
        return Response(
            {"detail": "Either audio file or recognized_text is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not transcript and audio_file:
        mime_type = audio_file.content_type or "audio/webm"
        audio_bytes = audio_file.read()
        if not audio_bytes:
            return Response(
                {"detail": "Uploaded audio is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            transcript = _transcribe_with_gemini(audio_bytes, mime_type, speech_model, gemini_api_key)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return Response(
                {"detail": "Gemini transcription failed.", "error": detail},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:  # pragma: no cover - network path
            return Response(
                {"detail": "Transcription error.", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
    elif audio_file:
        mime_type = audio_file.content_type or "audio/webm"
        audio_bytes = audio_file.read()

    ref_norm = _normalize_text(reference_text)
    hyp_norm = _normalize_text(transcript)
    max_len = max(len(ref_norm), len(hyp_norm), 1)
    distance = _levenshtein_distance(ref_norm, hyp_norm)
    char_similarity = max(0.0, 1.0 - (distance / max_len))
    token_similarity = _token_recall(reference_text, transcript)

    # Text similarity score (0~1).
    text_score = (0.75 * char_similarity) + (0.25 * token_similarity)
    text_score = max(0.0, min(1.0, text_score))

    audio_metrics = None
    reference_audio_metrics = None
    pitch_curve_similarity = None
    volume_curve_similarity = None
    if audio_bytes:
        try:
            audio_metrics = _extract_audio_metrics(audio_bytes, mime_type, transcript)
        except Exception:
            audio_metrics = None
        if audio_metrics:
            try:
                ref_audio_bytes = _synthesize_reference_tts(reference_text)
                reference_audio_metrics = _extract_audio_metrics(
                    ref_audio_bytes,
                    "audio/mpeg",
                    reference_text,
                )
                pitch_curve_similarity = _curve_similarity(
                    audio_metrics["pitch_curve"],
                    reference_audio_metrics["pitch_curve"],
                )
                volume_curve_similarity = _curve_similarity(
                    audio_metrics["volume_curve"],
                    reference_audio_metrics["volume_curve"],
                )
            except Exception:
                reference_audio_metrics = None
                pitch_curve_similarity = None
                volume_curve_similarity = None

    if audio_metrics:
        text_weight = 0.60
        speed_weight = 0.20
        pitch_weight = 0.20
        accuracy_ratio = (
            text_weight * text_score
            + speed_weight * audio_metrics["speed_score"]
            + pitch_weight * audio_metrics["pitch_score"]
        )
        score_rule = {
            "text_weight": text_weight,
            "speed_weight": speed_weight,
            "pitch_weight": pitch_weight,
            "text_subweights": {
                "char_similarity_weight": 0.75,
                "token_similarity_weight": 0.25,
            },
            "bands": {
                "excellent": ">= 90",
                "good": ">= 75",
                "fair": ">= 55",
                "needs_improvement": "< 55",
            },
        }
    else:
        accuracy_ratio = text_score
        score_rule = {
            "text_weight": 1.0,
            "speed_weight": 0.0,
            "pitch_weight": 0.0,
            "text_subweights": {
                "char_similarity_weight": 0.75,
                "token_similarity_weight": 0.25,
            },
            "bands": {
                "excellent": ">= 90",
                "good": ">= 75",
                "fair": ">= 55",
                "needs_improvement": "< 55",
            },
            "note": "audio metrics unavailable; text-only scoring",
        }

    accuracy_ratio = max(0.0, min(1.0, accuracy_ratio))
    score_percent = round(accuracy_ratio * 100.0, 2)

    feedback = _build_pronunciation_feedback(score_percent, reference_text, transcript)

    if sentence_id:
        try:
            sentence = Sentence.objects.get(pk=sentence_id)
            sentence.accuracy = accuracy_ratio
            sentence.save(update_fields=["accuracy"])
        except Sentence.DoesNotExist:
            return Response(
                {"detail": "Sentence not found.", "transcript": transcript},
                status=status.HTTP_404_NOT_FOUND,
            )

    return Response(
        {
            "transcript": transcript,
            "accuracy_ratio": round(accuracy_ratio, 4),
            "score_percent": score_percent,
            "char_similarity": round(char_similarity, 4),
            "token_similarity": round(token_similarity, 4),
            "text_score": round(text_score, 4),
            "audio_metrics_available": bool(audio_metrics),
            "speed_score": round(audio_metrics["speed_score"], 4) if audio_metrics else None,
            "pitch_score": round(audio_metrics["pitch_score"], 4) if audio_metrics else None,
            "audio_duration_sec": audio_metrics["duration_sec"] if audio_metrics else None,
            "syllables_per_sec": audio_metrics["syllables_per_sec"] if audio_metrics else None,
            "pitch_median_hz": audio_metrics["pitch_median_hz"] if audio_metrics else None,
            "pitch_std_hz": audio_metrics["pitch_std_hz"] if audio_metrics else None,
            "user_pitch_curve": audio_metrics["pitch_curve"] if audio_metrics else [],
            "user_volume_curve": audio_metrics["volume_curve"] if audio_metrics else [],
            "reference_pitch_curve": (
                reference_audio_metrics["pitch_curve"] if reference_audio_metrics else []
            ),
            "reference_volume_curve": (
                reference_audio_metrics["volume_curve"] if reference_audio_metrics else []
            ),
            "pitch_curve_similarity": pitch_curve_similarity,
            "volume_curve_similarity": volume_curve_similarity,
            "feedback": feedback,
            "model": speech_model,
            "score_level": _score_level(score_percent),
            "score_rule": score_rule,
        }
    )
