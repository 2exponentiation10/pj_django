from __future__ import annotations

import io
import os
from pathlib import Path
import ssl
import urllib.request
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .models import Chapter, MediaAsset, Sentence, Word

TWEMOJI_BASE = "https://raw.githubusercontent.com/jdecked/twemoji/main/assets/72x72"
CACHE_DIR = Path("/tmp/satoori_twemoji_cache")
ROOT_OUT_DIR = Path("/tmp/satoori_generated_assets")
WORD_OUT_DIR = ROOT_OUT_DIR / "words"
SENTENCE_OUT_DIR = ROOT_OUT_DIR / "sentences"
CHAPTER_OUT_DIR = ROOT_OUT_DIR / "chapters"
SAVE_DEBUG_IMAGES = os.getenv("LEARNING_VISUALS_DEBUG", "").lower() in {"1", "true", "yes", "on"}
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
SMALL_FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
CANVAS_WORD = (1200, 900)
CANVAS_SENTENCE = (1600, 900)
CANVAS_CHAPTER = (1280, 720)
PRIMARY_FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
SECONDARY_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

WORD_ICON_MAP = {
    "감사합니다": ("1f64f", "2728"),
    "실례합니다": ("1f647", "1f64f"),
    "괜찮아요": ("1f44c", "1f60a"),
    "조금만 기다려 주세요": ("23f3", "1f552"),
    "처음 뵙겠습니다": ("1f44b", "1f91d"),
    "잘 부탁드립니다": ("1f91d", "1f4aa"),
    "전화드릴게요": ("260e", "1f4de"),
    "확인해 볼게요": ("1f50d", "2705"),
    "포장": ("1f4e6", "1f6cd"),
    "맵기": ("1f336", "1f525"),
    "영수증": ("1f9fe", "1f4b3"),
    "현금": ("1f4b5", "1f4b8"),
    "카드": ("1f4b3", "2728"),
    "추가 주문": ("1f6d2", "2795"),
    "계산": ("1f4b0", "1f9fe"),
    "반찬": ("1f35a", "1f372"),
    "진료 예약": ("1f3e5", "1f5d3"),
    "접수": ("1f4dd", "1f3e5"),
    "대기 번호": ("1f522", "23f3"),
    "신분증": ("1f194", "1f464"),
    "처방전": ("1f48a", "1f4c4"),
    "주민센터": ("1f3db", "1f4c4"),
    "서류": ("1f4c4", "1f5c2"),
    "발급": ("1f4e4", "2728"),
    "회의": ("1f4ac", "1f465"),
    "업무 보고": ("1f4ca", "1f4bb"),
    "동료": ("1f465", "1f91d"),
    "마감": ("23f0", "2705"),
    "일정": ("1f4c5", "1f4cc"),
    "휴가": ("1f3d6", "2600"),
    "인수인계": ("1f4c1", "1f504"),
    "피드백": ("1f5e3", "1f4ac"),
    "환승": ("1f504", "1f687"),
    "정류장": ("1f68f", "1f68c"),
    "출구": ("1f6aa", "27a1"),
    "요금": ("1f4b8", "1f68c"),
    "교통카드": ("1f4b3", "1f68c"),
    "노선": ("1f5fa", "1f68c"),
    "막차": ("1f68c", "1f311"),
    "길 안내": ("1f9ed", "1f5fa"),
    "교환": ("1f504", "1f6cd"),
    "환불": ("1f4b8", "2b05"),
    "사이즈": ("1f457", "1f4cf"),
    "할인": ("1f3f7", "1f4b0"),
    "포인트": ("2b50", "1f4b3"),
    "결제": ("1f4b3", "1f4b0"),
    "품절": ("274c", "1f6d2"),
    "재고": ("1f4e6", "1f4e5"),
    "수강 신청": ("1f4da", "270d"),
    "과제": ("1f4d6", "270f"),
    "발표": ("1f3a4", "1f4ca"),
    "시험 범위": ("1f4da", "1f4dd"),
    "출석": ("2705", "1f393"),
    "지각": ("23f0", "1f3c3"),
    "보충 수업": ("1f393", "2795"),
    "상담": ("1f5e8", "1f464"),
    "계좌": ("1f3e6", "1f4b0"),
    "이체": ("1f4b8", "27a1"),
    "비밀번호": ("1f511", "1f4f1"),
    "한도": ("1f6ab", "1f4b3"),
    "수수료": ("1f4b1", "1f4b0"),
    "요금제": ("1f4f1", "1f4c3"),
    "본인 인증": ("1f510", "1f194"),
    "재발급": ("1f504", "1f194"),
}

CHAPTER_THEME = {
    1: {"title": "인사와 일상", "bg": ("#EFF6FF", "#DBEAFE"), "accent": "#2563EB", "icons": ("1f44b", "1f91d", "1f4de")},
    2: {"title": "식당과 음식", "bg": ("#FFF7ED", "#FFEDD5"), "accent": "#EA580C", "icons": ("1f35c", "1f9fe", "1f4b3")},
    3: {"title": "병원과 행정", "bg": ("#F0FDF4", "#DCFCE7"), "accent": "#16A34A", "icons": ("1f3e5", "1f48a", "1f194")},
    4: {"title": "직장과 대화", "bg": ("#F5F3FF", "#EDE9FE"), "accent": "#7C3AED", "icons": ("1f4ca", "1f4ac", "1f4c1")},
    5: {"title": "교통과 길찾기", "bg": ("#ECFEFF", "#CFFAFE"), "accent": "#0F766E", "icons": ("1f68c", "1f5fa", "1f687")},
    6: {"title": "쇼핑과 결제", "bg": ("#FFF1F2", "#FFE4E6"), "accent": "#E11D48", "icons": ("1f6cd", "1f457", "1f4b3")},
    7: {"title": "학교와 공부", "bg": ("#FEFCE8", "#FEF3C7"), "accent": "#CA8A04", "icons": ("1f4da", "270f", "1f393")},
    8: {"title": "은행과 통신", "bg": ("#F8FAFC", "#E2E8F0"), "accent": "#334155", "icons": ("1f3e6", "1f4f1", "1f511")},
}

SENTENCE_RULES = [
    (("전화", "연락"), ("260e", "1f4de")),
    (("기다려", "잠시만"), ("23f3", "1f552")),
    (("확인",), ("1f50d", "2705")),
    (("맵",), ("1f336", "1f525")),
    (("포장",), ("1f4e6", "1f6cd")),
    (("영수증", "영수표"), ("1f9fe", "1f4b3")),
    (("카드", "결제", "계산"), ("1f4b3", "1f4b0")),
    (("병원", "진료", "처방"), ("1f3e5", "1f48a")),
    (("신분증", "공민증"), ("1f194", "1f464")),
    (("회의",), ("1f4ac", "1f465")),
    (("보고", "자료"), ("1f4ca", "1f4bb")),
    (("휴가",), ("1f3d6", "2600")),
    (("지하철", "버스", "택시"), ("1f68c", "1f5fa")),
    (("출구",), ("1f6aa", "27a1")),
    (("교통카드",), ("1f4b3", "1f68c")),
    (("할인",), ("1f3f7", "1f4b0")),
    (("품절",), ("274c", "1f6d2")),
    (("수강", "과제", "시험", "출석", "지각", "수업"), ("1f4da", "270f")),
    (("상담",), ("1f5e8", "1f464")),
    (("계좌", "이체", "수수료"), ("1f3e6", "1f4b8")),
    (("비밀번호", "인증"), ("1f511", "1f4f1")),
    (("요금제", "휴대폰", "유심", "인터넷"), ("1f4f1", "1f4c3")),
]


def _font_path(secondary: bool = False) -> str:
    candidates = SECONDARY_FONT_CANDIDATES if secondary else PRIMARY_FONT_CANDIDATES
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return SMALL_FONT_PATH if secondary else FONT_PATH


def _get_font(size: int, secondary: bool = False):
    return ImageFont.truetype(_font_path(secondary), size)


def _ssl_context():
    return ssl._create_unverified_context()


def _ensure_icon(code: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{code}.png"
    if path.exists():
        return path
    with urllib.request.urlopen(f"{TWEMOJI_BASE}/{code}.png", context=_ssl_context(), timeout=60) as response:
        path.write_bytes(response.read())
    return path


def _hex_to_rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _gradient_canvas(size: tuple[int, int], start: str, end: str):
    width, height = size
    sr, sg, sb = _hex_to_rgb(start)
    er, eg, eb = _hex_to_rgb(end)
    image = Image.new("RGBA", size)
    pixels = image.load()
    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(sr + (er - sr) * ratio)
        g = int(sg + (eg - sg) * ratio)
        b = int(sb + (eb - sb) * ratio)
        for x in range(width):
            pixels[x, y] = (r, g, b, 255)
    return image


def _add_shadow(base: Image.Image, bbox, radius=34, offset=(0, 18), opacity=60):
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = bbox
    ox, oy = offset
    draw.rounded_rectangle((x1 + ox, y1 + oy, x2 + ox, y2 + oy), radius=radius, fill=(15, 23, 42, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    return Image.alpha_composite(base, shadow)


def _load_icon(icon_path: Path, size: int):
    icon = Image.open(icon_path).convert("RGBA")
    return icon.resize((size, size), Image.LANCZOS)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    start_size: int,
    min_size: int,
    max_lines: int = 2,
):
    for size in range(start_size, min_size - 1, -2):
        font = _get_font(size)
        lines = _wrap_text(draw, text, font, max_width)
        width = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)
        if width <= max_width and len(lines) <= max_lines:
            return font, lines
    font = _get_font(min_size)
    return font, _wrap_text(draw, text, font, max_width)


def _pick_sentence_icons(sentence: str, chapter_id: int):
    for keywords, icons in SENTENCE_RULES:
        if any(keyword in sentence for keyword in keywords):
            return icons
    return CHAPTER_THEME[chapter_id]["icons"][:2]


def _pick_sentence_labels(sentence: str, chapter_id: int):
    for keywords, _icons in SENTENCE_RULES:
        if any(keyword in sentence for keyword in keywords):
            labels = [keyword[:4] for keyword in keywords[:2]]
            if len(labels) == 1:
                labels.append("표현")
            return labels
    theme_words = [token for token in CHAPTER_THEME[chapter_id]["title"].replace("와", " ").replace("과", " ").split() if token]
    if len(theme_words) >= 2:
        return [theme_words[0][:4], theme_words[1][:4]]
    return [CHAPTER_THEME[chapter_id]["title"][:4], "실전"]


def _image_to_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _save_debug_png(image: Image.Image, out_path: Path):
    if not SAVE_DEBUG_IMAGES:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_image_to_bytes(image))


def _draw_text_badge(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    title: str,
    value: str,
    fill: str,
    text_fill: str = "white",
    subtle_fill: str = "#F8FAFC",
):
    draw = ImageDraw.Draw(image)
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=30, fill=fill)
    inner = (x1 + 16, y1 + 16, x2 - 16, y2 - 16)
    draw.rounded_rectangle(inner, radius=24, fill=subtle_fill)
    draw.text(((x1 + x2) // 2, y1 + 46), title, font=_get_font(24, secondary=True), anchor="mm", fill="#475569")
    value_font, lines = _fit_font(draw, value, (x2 - x1) - 50, 46, 24, max_lines=3)
    base_y = y1 + 100
    for line in lines:
        draw.text(((x1 + x2) // 2, base_y), line, font=value_font, anchor="mm", fill="#0F172A")
        base_y += value_font.size + 8
    draw.rounded_rectangle((x1, y1, x2, y1 + 54), radius=30, fill=fill)
    draw.text(((x1 + x2) // 2, y1 + 28), title, font=_get_font(22, secondary=True), anchor="mm", fill=text_fill)


def _word_card_bytes(word: Word) -> bytes:
    theme = CHAPTER_THEME[word.chapter_id]
    image = _gradient_canvas(CANVAS_WORD, *theme["bg"])
    image = _add_shadow(image, (60, 60, 1140, 840), radius=40)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 60, 1140, 840), radius=40, fill="white")
    draw.rounded_rectangle((96, 96, 440, 150), radius=26, fill=theme["accent"])
    draw.text((268, 123), theme["title"], font=_get_font(30), anchor="mm", fill="white")

    draw.rounded_rectangle((110, 190, 1090, 520), radius=34, fill=theme["accent"])
    draw.rounded_rectangle((130, 210, 1070, 500), radius=30, fill="#F8FAFC")

    _draw_text_badge(
        image,
        (150, 235, 455, 465),
        title="표준어",
        value=word.korean_word,
        fill=theme["accent"],
    )
    _draw_text_badge(
        image,
        (745, 235, 1050, 465),
        title="북한식",
        value=word.north_korean_word,
        fill=theme["accent"],
    )

    draw.rounded_rectangle((500, 255, 700, 455), radius=28, fill=theme["accent"])
    draw.text((600, 355), word.korean_word[:2], font=_get_font(90), anchor="mm", fill="white")

    title_font, title_lines = _fit_font(draw, word.korean_word, 920, 72, 42)
    y = 585
    for line in title_lines:
        draw.text((600, y), line, font=title_font, anchor="mm", fill="#0F172A")
        y += title_font.size + 12

    subtitle_font, subtitle_lines = _fit_font(draw, word.north_korean_word, 900, 38, 26)
    for line in subtitle_lines:
        draw.text((600, y + 14), line, font=subtitle_font, anchor="mm", fill="#475569")
        y += subtitle_font.size + 10

    draw.text(
        (600, 792),
        f"표준어 ↔ 북한식 표현 | {word.chapter.title}",
        font=_get_font(24, secondary=True),
        anchor="mm",
        fill="#94A3B8",
    )

    _save_debug_png(image, WORD_OUT_DIR / f"word-{word.id:03d}.png")
    return _image_to_bytes(image)


def _sentence_card_bytes(sentence: Sentence) -> bytes:
    theme = CHAPTER_THEME[sentence.chapter_id]
    image = _gradient_canvas(CANVAS_SENTENCE, *theme["bg"])
    image = _add_shadow(image, (70, 70, 1530, 830), radius=42)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((70, 70, 1530, 830), radius=42, fill="white")
    draw.rounded_rectangle((110, 110, 470, 168), radius=28, fill=theme["accent"])
    draw.text((290, 139), theme["title"], font=_get_font(32), anchor="mm", fill="white")

    draw.rounded_rectangle((1140, 110, 1480, 168), radius=28, fill="#E2E8F0")
    draw.text((1310, 139), "문장 장면 카드", font=_get_font(26, secondary=True), anchor="mm", fill="#334155")

    left_label, right_label = _pick_sentence_labels(sentence.korean_sentence, sentence.chapter_id)

    draw.rounded_rectangle((120, 220, 1480, 520), radius=34, fill=theme["accent"])
    draw.rounded_rectangle((140, 240, 1460, 500), radius=30, fill="#F8FAFC")
    _draw_text_badge(
        image,
        (170, 255, 420, 485),
        title="상황",
        value=left_label,
        fill=theme["accent"],
    )
    _draw_text_badge(
        image,
        (1180, 255, 1430, 485),
        title="핵심",
        value=right_label,
        fill=theme["accent"],
    )

    title_font, title_lines = _fit_font(draw, sentence.korean_sentence, 800, 64, 36, max_lines=3)
    y = 280
    for line in title_lines:
        draw.text((800, y), line, font=title_font, anchor="mm", fill="#0F172A")
        y += title_font.size + 10

    subtitle_font, subtitle_lines = _fit_font(
        draw,
        sentence.north_korean_sentence,
        1080,
        36,
        24,
        max_lines=3,
    )
    y = 585
    draw.text((160, 575), "북한식 표현", font=_get_font(24, secondary=True), fill="#64748B")
    for line in subtitle_lines:
        draw.text((800, y), line, font=subtitle_font, anchor="mm", fill="#475569")
        y += subtitle_font.size + 8

    draw.text(
        (800, 770),
        f"학습 문장 #{sentence.id} | 실전 장면 연상용 시각 카드",
        font=_get_font(24, secondary=True),
        anchor="mm",
        fill="#94A3B8",
    )

    _save_debug_png(image, SENTENCE_OUT_DIR / f"sentence-{sentence.id:03d}.png")
    return _image_to_bytes(image)


def _chapter_cover_bytes(chapter: Chapter) -> bytes:
    theme = CHAPTER_THEME[chapter.id]
    image = _gradient_canvas(CANVAS_CHAPTER, *theme["bg"])
    image = _add_shadow(image, (50, 50, 1230, 670), radius=42)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((50, 50, 1230, 670), radius=42, fill="white")
    draw.rounded_rectangle((84, 86, 390, 142), radius=28, fill=theme["accent"])
    draw.text((237, 114), "Chapter Cover", font=_get_font(28, secondary=True), anchor="mm", fill="white")

    draw.text((100, 228), chapter.title, font=_get_font(64), fill="#0F172A")
    meta = f"난이도: {chapter.difficulty} · 태그: {chapter.context_tag}"
    draw.text((100, 304), meta, font=_get_font(28, secondary=True), fill="#64748B")

    chapter_labels = [token for token in chapter.title.replace("와", " ").replace("과", " ").split() if token]
    while len(chapter_labels) < 3:
        chapter_labels.append("학습")
    _draw_text_badge(image, (700, 140, 980, 330), title="장면", value=chapter_labels[0], fill=theme["accent"])
    _draw_text_badge(image, (980, 250, 1260, 440), title="표현", value=chapter_labels[1], fill=theme["accent"])
    _draw_text_badge(image, (560, 360, 840, 550), title="적용", value=chapter_labels[2], fill=theme["accent"])

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((100, 520, 500, 590), radius=24, fill="#F8FAFC", outline="#E2E8F0")
    draw.text((300, 555), "표준어 · 북한식 표현 · 장면 학습", font=_get_font(24, secondary=True), anchor="mm", fill="#334155")

    _save_debug_png(image, CHAPTER_OUT_DIR / f"chapter-{chapter.id:02d}.png")
    return _image_to_bytes(image)


def _upsert_asset(*, owner, category: str, label: str, key_text: str, image_bytes: bytes, chapter=None, word=None, sentence=None):
    filters = {"owner": owner, "category": category}
    if category == MediaAsset.CATEGORY_CHAPTER and chapter is not None:
        filters["chapter"] = chapter
    elif category == MediaAsset.CATEGORY_WORD and word is not None:
        filters["word"] = word
    elif category == MediaAsset.CATEGORY_SENTENCE and sentence is not None:
        filters["sentence"] = sentence
    else:
        filters["key_text"] = key_text

    MediaAsset.objects.filter(**filters).delete()

    asset = MediaAsset(
        owner=owner,
        category=category,
        label=label,
        key_text=key_text,
        chapter=chapter,
        word=word,
        sentence=sentence,
    )
    file_name = f"{category}-{chapter.id if chapter else 'x'}-{word.id if word else sentence.id if sentence else 'cover'}.png"
    asset.image.save(file_name, ContentFile(image_bytes), save=False)
    asset.save()
    return asset


def seed_practice_visuals(*, owner, progress_callback=None) -> dict[str, int]:
    chapters = list(Chapter.objects.filter(owner=owner).order_by("id"))
    total_items = len(chapters)
    total_items += sum(chapter.words.count() for chapter in chapters)
    total_items += sum(chapter.sentences.count() for chapter in chapters)
    chapter_count = word_count = sentence_count = 0
    completed_items = 0

    if progress_callback:
        progress_callback(
            {
                "status": "running",
                "message": "학습 시각자료 준비 중",
                "total_items": total_items,
                "completed_items": completed_items,
                "chapters": chapter_count,
                "words": word_count,
                "sentences": sentence_count,
            }
        )

    for chapter in chapters:
        _upsert_asset(
            owner=owner,
            category=MediaAsset.CATEGORY_CHAPTER,
            label=f"{chapter.title} 자동 커버",
            key_text=chapter.title,
            image_bytes=_chapter_cover_bytes(chapter),
            chapter=chapter,
        )
        chapter_count += 1
        completed_items += 1
        if progress_callback:
            progress_callback(
                {
                    "status": "running",
                    "message": f"챕터 커버 생성 · {chapter.title}",
                    "total_items": total_items,
                    "completed_items": completed_items,
                    "chapters": chapter_count,
                    "words": word_count,
                    "sentences": sentence_count,
                }
            )

        words = list(chapter.words.all().order_by("id"))
        for word in words:
            _upsert_asset(
                owner=owner,
                category=MediaAsset.CATEGORY_WORD,
                label=f"{word.korean_word} 자동 카드",
                key_text=word.korean_word,
                image_bytes=_word_card_bytes(word),
                chapter=chapter,
                word=word,
            )
            word_count += 1
            completed_items += 1
            if progress_callback and (completed_items % 4 == 0 or completed_items == total_items):
                progress_callback(
                    {
                        "status": "running",
                        "message": f"단어 카드 생성 · {word.korean_word}",
                        "total_items": total_items,
                        "completed_items": completed_items,
                        "chapters": chapter_count,
                        "words": word_count,
                        "sentences": sentence_count,
                    }
                )

        sentences = list(chapter.sentences.all().order_by("id"))
        for sentence in sentences:
            _upsert_asset(
                owner=owner,
                category=MediaAsset.CATEGORY_SENTENCE,
                label=f"문장 {sentence.id} 자동 장면 카드",
                key_text=sentence.korean_sentence,
                image_bytes=_sentence_card_bytes(sentence),
                chapter=chapter,
                sentence=sentence,
            )
            sentence_count += 1
            completed_items += 1
            if progress_callback and (completed_items % 4 == 0 or completed_items == total_items):
                progress_callback(
                    {
                        "status": "running",
                        "message": f"문장 카드 생성 · #{sentence.id}",
                        "total_items": total_items,
                        "completed_items": completed_items,
                        "chapters": chapter_count,
                        "words": word_count,
                        "sentences": sentence_count,
                    }
                )

    return {
        "total_items": total_items,
        "completed_items": completed_items,
        "chapters": chapter_count,
        "words": word_count,
        "sentences": sentence_count,
    }
