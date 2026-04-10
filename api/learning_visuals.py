from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import ssl
import urllib.parse
import urllib.request

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .models import Chapter, MediaAsset, Sentence, Word

COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
REQUEST_HEADERS = {
    'User-Agent': 'SatooriLearningVisualizer/1.0 (portfolio local environment)',
}
SSL_CONTEXT = ssl._create_unverified_context()
CACHE_DIR = Path('/tmp/satoori_commons_cache')
QUERY_CACHE_DIR = CACHE_DIR / 'queries'
IMAGE_CACHE_DIR = CACHE_DIR / 'images'
ROOT_OUT_DIR = Path('/tmp/satoori_generated_assets')
WORD_OUT_DIR = ROOT_OUT_DIR / 'words'
SENTENCE_OUT_DIR = ROOT_OUT_DIR / 'sentences'
CHAPTER_OUT_DIR = ROOT_OUT_DIR / 'chapters'
SAVE_DEBUG_IMAGES = os.getenv('LEARNING_VISUALS_DEBUG', '').lower() in {'1', 'true', 'yes', 'on'}
PRIMARY_FONT_CANDIDATES = [
    '/System/Library/Fonts/AppleSDGothicNeo.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]
SECONDARY_FONT_CANDIDATES = [
    '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]
CANVAS_WORD = (1200, 900)
CANVAS_SENTENCE = (1600, 900)
CANVAS_CHAPTER = (1280, 720)

CHAPTER_THEME = {
    1: {
        'title': '인사와 일상',
        'accent': '#2563EB',
        'overlay': '#0F172ACC',
        'queries': [
            'people greeting in office',
            'asian business handshake meeting',
            'people talking indoors',
            'phone call office person',
        ],
    },
    2: {
        'title': '식당과 음식',
        'accent': '#EA580C',
        'overlay': '#111827CC',
        'queries': [
            'korean restaurant food',
            'takeout food counter',
            'restaurant payment receipt',
            'korean side dishes meal',
        ],
    },
    3: {
        'title': '병원과 행정',
        'accent': '#16A34A',
        'overlay': '#0F172ACC',
        'queries': [
            'hospital reception desk',
            'doctor prescription paper',
            'government office service counter',
            'documents on desk office',
        ],
    },
    4: {
        'title': '직장과 대화',
        'accent': '#7C3AED',
        'overlay': '#111827CC',
        'queries': [
            'office meeting team',
            'business presentation office',
            'coworkers discussion office',
            'calendar planner desk office',
        ],
    },
    5: {
        'title': '교통과 길찾기',
        'accent': '#0F766E',
        'overlay': '#082F49CC',
        'queries': [
            'subway station platform',
            'bus stop city street',
            'transit card ticket gate',
            'navigation map city street',
        ],
    },
    6: {
        'title': '쇼핑과 결제',
        'accent': '#E11D48',
        'overlay': '#111827CC',
        'queries': [
            'shopping mall clothing store',
            'payment terminal card shopping',
            'sale retail store',
            'store inventory shelf',
        ],
    },
    7: {
        'title': '학교와 공부',
        'accent': '#CA8A04',
        'overlay': '#172554CC',
        'queries': [
            'classroom students studying',
            'student presentation classroom',
            'exam notes study desk',
            'school counseling conversation',
        ],
    },
    8: {
        'title': '은행과 통신',
        'accent': '#334155',
        'overlay': '#0F172ACC',
        'queries': [
            'mobile banking smartphone',
            'bank counter account service',
            'phone verification app',
            'telecom store smartphone plan',
        ],
    },
}

WORD_QUERY_MAP = {
    '감사합니다': ['people bowing thank you', 'people greeting politely'],
    '실례합니다': ['person asking excuse indoors', 'people meeting in hallway'],
    '괜찮아요': ['smiling people conversation', 'friend reassuring another person'],
    '조금만 기다려 주세요': ['people waiting at counter', 'waiting line indoors'],
    '처음 뵙겠습니다': ['business handshake first meeting', 'people greeting each other formally'],
    '잘 부탁드립니다': ['handshake business meeting', 'team greeting office'],
    '전화드릴게요': ['person making phone call office', 'smartphone call close up'],
    '확인해 볼게요': ['person checking document office', 'checking smartphone screen'],
    '포장': ['takeout food counter', 'food takeaway package'],
    '맵기': ['spicy korean food', 'red spicy dish'],
    '영수증': ['receipt on table payment', 'paper receipt close up'],
    '현금': ['cash banknotes hand', 'cash payment counter'],
    '카드': ['credit card payment', 'card in hand close up'],
    '추가 주문': ['restaurant ordering menu', 'customer ordering food'],
    '계산': ['restaurant bill payment', 'paying restaurant bill'],
    '반찬': ['korean side dishes', 'small dishes korean food'],
    '진료 예약': ['hospital appointment desk', 'clinic reception desk'],
    '접수': ['hospital reception counter', 'service desk hospital'],
    '대기 번호': ['queue ticket number display', 'waiting number ticket'],
    '신분증': ['id card in hand', 'identification card close up'],
    '처방전': ['prescription form paper', 'medicine prescription document'],
    '주민센터': ['government office counter', 'public service office desk'],
    '서류': ['documents paperwork desk', 'paper files office desk'],
    '발급': ['document printer office', 'certificate issuing counter'],
    '회의': ['office meeting team', 'conference room meeting'],
    '업무 보고': ['business presentation office', 'report meeting office'],
    '동료': ['coworkers talking office', 'team members office'],
    '마감': ['deadline office work late', 'busy office desk calendar'],
    '일정': ['calendar planner desk', 'schedule planner office'],
    '휴가': ['vacation luggage beach', 'travel suitcase vacation'],
    '인수인계': ['handover documents office', 'passing files to coworker'],
    '피드백': ['team feedback conversation', 'discussion around laptop office'],
    '환승': ['subway transfer station', 'transfer corridor station'],
    '정류장': ['bus stop city street', 'bus stop sign urban'],
    '출구': ['subway exit sign', 'station exit stairs'],
    '요금': ['bus fare ticket', 'price display transit'],
    '교통카드': ['transit card gate', 'transportation card tap'],
    '노선': ['subway route map', 'bus route map'],
    '막차': ['night bus city', 'last train platform night'],
    '길 안내': ['city map navigation', 'person using map phone'],
    '교환': ['clothes exchange counter', 'return exchange shopping desk'],
    '환불': ['refund receipt shopping', 'refund service counter'],
    '사이즈': ['clothing size label', 'trying clothes fitting room'],
    '할인': ['sale sign retail store', 'discount price tag'],
    '포인트': ['loyalty card payment', 'membership card app'],
    '결제': ['card terminal payment', 'mobile payment close up'],
    '품절': ['sold out shelf sign', 'empty retail shelf'],
    '재고': ['warehouse stock boxes', 'store inventory shelf'],
    '수강 신청': ['course registration computer', 'student registration desk'],
    '과제': ['student homework desk', 'notebook study assignment'],
    '발표': ['student presentation classroom', 'presentation in classroom'],
    '시험 범위': ['exam notes study', 'study notes desk'],
    '출석': ['classroom attendance list', 'students in classroom'],
    '지각': ['running student late', 'clock student hurry'],
    '보충 수업': ['tutoring classroom', 'extra class study'],
    '상담': ['school counseling conversation', 'counselor student talk'],
    '계좌': ['bank account app', 'bankbook account'],
    '이체': ['mobile banking transfer', 'online bank transfer screen'],
    '비밀번호': ['password smartphone login', 'typing password phone'],
    '한도': ['credit card limit app', 'banking limit screen'],
    '수수료': ['bank fee notice', 'service fee payment'],
    '요금제': ['telecom plan smartphone', 'mobile carrier store'],
    '본인 인증': ['identity verification phone', 'sms verification screen'],
    '재발급': ['replacement card desk', 'reissue service counter'],
}

SENTENCE_QUERY_RULES = [
    (('안녕하세요', '처음 뵙', '감사합니다', '도와드릴게요'), ['people greeting in office', 'people talking politely indoors']),
    (('기다려', '잠시만'), ['waiting line indoors', 'people waiting at service desk']),
    (('확인', '설명'), ['person checking document office', 'consultation at desk']),
    (('연락', '전화'), ['person making phone call office', 'smartphone call close up']),
    (('맵기', '음식', '메뉴', '포장', '영수증', '카드', '주문', '매장'), ['korean restaurant food', 'restaurant payment receipt', 'takeout food counter']),
    (('진료', '처방', '접수', '신분증', '서류', '발급'), ['hospital reception desk', 'prescription form paper', 'government office service counter']),
    (('회의', '보고', '동료', '일정', '휴가', '피드백'), ['office meeting team', 'business presentation office', 'calendar planner desk office']),
    (('환승', '정류장', '출구', '교통카드', '노선', '막차', '길'), ['subway station platform', 'bus stop city street', 'navigation map city street']),
    (('교환', '환불', '사이즈', '할인', '결제', '품절', '재고'), ['shopping mall clothing store', 'payment terminal card shopping', 'sale retail store']),
    (('수강', '과제', '발표', '시험', '출석', '지각', '수업', '상담'), ['classroom students studying', 'student presentation classroom', 'school counseling conversation']),
    (('계좌', '이체', '비밀번호', '한도', '수수료', '요금제', '인증', '재발급'), ['mobile banking smartphone', 'bank counter account service', 'phone verification app']),
]


def _font_path(secondary: bool = False) -> str:
    candidates = SECONDARY_FONT_CANDIDATES if secondary else PRIMARY_FONT_CANDIDATES
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def _get_font(size: int, secondary: bool = False):
    return ImageFont.truetype(_font_path(secondary), size)


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path


def _hash_key(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _request_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=90) as response:
        return json.loads(response.read().decode('utf-8'))


def _search_commons_images(query: str) -> list[str]:
    _ensure_dir(QUERY_CACHE_DIR)
    cache_path = QUERY_CACHE_DIR / f'{_hash_key(query)}.json'
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding='utf-8'))

    params = {
        'action': 'query',
        'generator': 'search',
        'gsrsearch': query,
        'gsrnamespace': '6',
        'gsrlimit': '8',
        'prop': 'imageinfo',
        'iiprop': 'url',
        'iiurlwidth': '1600',
        'format': 'json',
    }
    url = f"{COMMONS_API}?{urllib.parse.urlencode(params)}"
    data = _request_json(url)
    urls: list[str] = []
    for page in data.get('query', {}).get('pages', {}).values():
        title = str(page.get('title', '')).lower()
        if not title.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            continue
        info = (page.get('imageinfo') or [{}])[0]
        image_url = info.get('thumburl') or info.get('url')
        if image_url:
            urls.append(image_url)
    cache_path.write_text(json.dumps(urls, ensure_ascii=False), encoding='utf-8')
    return urls


def _download_binary(url: str) -> bytes:
    _ensure_dir(IMAGE_CACHE_DIR)
    suffix = Path(urllib.parse.urlparse(url).path).suffix or '.img'
    cache_path = IMAGE_CACHE_DIR / f'{_hash_key(url)}{suffix}'
    if cache_path.exists():
        return cache_path.read_bytes()
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=120) as response:
        data = response.read()
    cache_path.write_bytes(data)
    return data


def _pick_image_url(queries: list[str], seed: int) -> str | None:
    for query in queries:
        results = _search_commons_images(query)
        if results:
            return results[seed % len(results)]
    return None


def _cover_photo(url: str | None, size: tuple[int, int], fallback_color: str) -> Image.Image:
    if url:
        try:
            data = _download_binary(url)
            image = Image.open(io.BytesIO(data)).convert('RGB')
            return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
        except Exception:
            pass
    return Image.new('RGB', size, fallback_color)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int, max_lines: int = 2):
    for size in range(start_size, min_size - 1, -2):
        font = _get_font(size)
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines and max(draw.textbbox((0, 0), line, font=font)[2] for line in lines) <= max_width:
            return font, lines
    font = _get_font(min_size)
    return font, _wrap_text(draw, text, font, max_width)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int):
    words = text.split(' ')
    lines: list[str] = []
    current = ''
    for word in words:
        candidate = word if not current else f'{current} {word}'
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ['']


def _apply_overlay(base: Image.Image, overlay_color: str) -> Image.Image:
    image = base.convert('RGBA')
    overlay = Image.new('RGBA', image.size, overlay_color)
    image = Image.alpha_composite(image, overlay)
    vignette = Image.new('L', image.size, 0)
    vdraw = ImageDraw.Draw(vignette)
    width, height = image.size
    for inset, opacity in ((0, 120), (50, 80), (110, 35)):
        vdraw.rounded_rectangle((inset, inset, width - inset, height - inset), radius=32, outline=opacity, width=60)
    vignette = vignette.filter(ImageFilter.GaussianBlur(40))
    shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
    shadow.putalpha(vignette)
    return Image.alpha_composite(image, shadow)


def _draw_chip(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, text: str, text_fill: str = 'white'):
    draw.rounded_rectangle(box, radius=28, fill=fill)
    draw.text(((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), text, font=_get_font(28, secondary=True), anchor='mm', fill=text_fill)


def _draw_photo_layout(*, size: tuple[int, int], photo: Image.Image, title: str, subtitle: str, eyebrow: str, footer: str, accent: str, overlay: str) -> bytes:
    image = _apply_overlay(photo.resize(size), overlay)
    draw = ImageDraw.Draw(image)
    width, height = size

    card_box = (64, height - 300, width - 64, height - 70)
    card_shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(card_shadow)
    sdraw.rounded_rectangle((card_box[0], card_box[1] + 14, card_box[2], card_box[3] + 14), radius=34, fill=(15, 23, 42, 80))
    card_shadow = card_shadow.filter(ImageFilter.GaussianBlur(20))
    image = Image.alpha_composite(image, card_shadow)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(card_box, radius=34, fill=(255, 255, 255, 228))
    _draw_chip(draw, (84, 76, 380, 136), accent, eyebrow)

    title_font, title_lines = _fit_font(draw, title, width - 220, 64, 34, max_lines=3)
    y = height - 250
    for line in title_lines:
        draw.text((94, y), line, font=title_font, fill='#0F172A')
        y += title_font.size + 8

    subtitle_font, subtitle_lines = _fit_font(draw, subtitle, width - 220, 34, 22, max_lines=3)
    for line in subtitle_lines:
        draw.text((94, y + 6), line, font=subtitle_font, fill='#334155')
        y += subtitle_font.size + 6

    draw.text((94, height - 110), footer, font=_get_font(24, secondary=True), fill='#64748B')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def _save_debug_png(image_bytes: bytes, path: Path):
    if not SAVE_DEBUG_IMAGES:
        return
    _ensure_dir(path.parent)
    path.write_bytes(image_bytes)


def _word_queries(word: Word) -> list[str]:
    queries = WORD_QUERY_MAP.get(word.korean_word, [])
    return [*queries, *CHAPTER_THEME[word.chapter_id]['queries']]


def _sentence_queries(sentence: Sentence) -> list[str]:
    queries: list[str] = []
    text = sentence.korean_sentence
    for keywords, candidates in SENTENCE_QUERY_RULES:
        if any(keyword in text for keyword in keywords):
            queries.extend(candidates)
    queries.extend(CHAPTER_THEME[sentence.chapter_id]['queries'])
    return queries


def _word_card_bytes(word: Word) -> bytes:
    theme = CHAPTER_THEME[word.chapter_id]
    photo = _cover_photo(
        _pick_image_url(_word_queries(word), word.id),
        CANVAS_WORD,
        '#E2E8F0',
    )
    photo = ImageEnhance.Color(photo).enhance(1.05)
    bytes_data = _draw_photo_layout(
        size=CANVAS_WORD,
        photo=photo,
        title=word.korean_word,
        subtitle=f'북한식: {word.north_korean_word}',
        eyebrow=f"{theme['title']} · 단어",
        footer='Wikimedia Commons 공개 이미지 기반 학습 카드',
        accent=theme['accent'],
        overlay=theme['overlay'],
    )
    _save_debug_png(bytes_data, WORD_OUT_DIR / f'word-{word.id:03d}.png')
    return bytes_data


def _sentence_card_bytes(sentence: Sentence) -> bytes:
    theme = CHAPTER_THEME[sentence.chapter_id]
    photo = _cover_photo(
        _pick_image_url(_sentence_queries(sentence), sentence.id),
        CANVAS_SENTENCE,
        '#CBD5E1',
    )
    photo = ImageEnhance.Contrast(photo).enhance(1.03)
    bytes_data = _draw_photo_layout(
        size=CANVAS_SENTENCE,
        photo=photo,
        title=sentence.korean_sentence,
        subtitle=f'북한식: {sentence.north_korean_sentence}',
        eyebrow=f"{theme['title']} · 문장",
        footer='실제 장면 사진 위에 학습 문장을 얹은 회화 카드',
        accent=theme['accent'],
        overlay=theme['overlay'],
    )
    _save_debug_png(bytes_data, SENTENCE_OUT_DIR / f'sentence-{sentence.id:03d}.png')
    return bytes_data


def _chapter_cover_bytes(chapter: Chapter) -> bytes:
    theme = CHAPTER_THEME[chapter.id]
    photo = _cover_photo(
        _pick_image_url(theme['queries'], chapter.id),
        CANVAS_CHAPTER,
        '#CBD5E1',
    )
    bytes_data = _draw_photo_layout(
        size=CANVAS_CHAPTER,
        photo=photo,
        title=chapter.title,
        subtitle=f'난이도: {chapter.difficulty} · 태그: {chapter.context_tag}',
        eyebrow='Chapter Cover',
        footer='실제 장면 기반 학습 커버',
        accent=theme['accent'],
        overlay=theme['overlay'],
    )
    _save_debug_png(bytes_data, CHAPTER_OUT_DIR / f'chapter-{chapter.id:02d}.png')
    return bytes_data


def _upsert_asset(*, owner, category: str, label: str, key_text: str, image_bytes: bytes, chapter=None, word=None, sentence=None):
    filters = {'owner': owner, 'category': category}
    if category == MediaAsset.CATEGORY_CHAPTER and chapter is not None:
        filters['chapter'] = chapter
    elif category == MediaAsset.CATEGORY_WORD and word is not None:
        filters['word'] = word
    elif category == MediaAsset.CATEGORY_SENTENCE and sentence is not None:
        filters['sentence'] = sentence
    else:
        filters['key_text'] = key_text

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
    chapters = list(Chapter.objects.filter(owner=owner).order_by('id'))
    total_items = len(chapters)
    total_items += sum(chapter.words.count() for chapter in chapters)
    total_items += sum(chapter.sentences.count() for chapter in chapters)
    chapter_count = word_count = sentence_count = 0
    completed_items = 0

    if progress_callback:
        progress_callback(
            {
                'status': 'running',
                'message': 'Commons 이미지 기반 학습 시각자료 준비 중',
                'total_items': total_items,
                'completed_items': completed_items,
                'chapters': chapter_count,
                'words': word_count,
                'sentences': sentence_count,
            }
        )

    for chapter in chapters:
        _upsert_asset(
            owner=owner,
            category=MediaAsset.CATEGORY_CHAPTER,
            label=f'{chapter.title} Commons 커버',
            key_text=chapter.title,
            image_bytes=_chapter_cover_bytes(chapter),
            chapter=chapter,
        )
        chapter_count += 1
        completed_items += 1
        if progress_callback:
            progress_callback(
                {
                    'status': 'running',
                    'message': f'챕터 커버 생성 · {chapter.title}',
                    'total_items': total_items,
                    'completed_items': completed_items,
                    'chapters': chapter_count,
                    'words': word_count,
                    'sentences': sentence_count,
                }
            )

        words = list(chapter.words.all().order_by('id'))
        for word in words:
            _upsert_asset(
                owner=owner,
                category=MediaAsset.CATEGORY_WORD,
                label=f'{word.korean_word} Commons 이미지',
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
                        'status': 'running',
                        'message': f'단어 이미지 생성 · {word.korean_word}',
                        'total_items': total_items,
                        'completed_items': completed_items,
                        'chapters': chapter_count,
                        'words': word_count,
                        'sentences': sentence_count,
                    }
                )

        sentences = list(chapter.sentences.all().order_by('id'))
        for sentence in sentences:
            _upsert_asset(
                owner=owner,
                category=MediaAsset.CATEGORY_SENTENCE,
                label=f'문장 {sentence.id} Commons 장면 카드',
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
                        'status': 'running',
                        'message': f'문장 장면 카드 생성 · #{sentence.id}',
                        'total_items': total_items,
                        'completed_items': completed_items,
                        'chapters': chapter_count,
                        'words': word_count,
                        'sentences': sentence_count,
                    }
                )

    return {
        'total_items': total_items,
        'completed_items': completed_items,
        'chapters': chapter_count,
        'words': word_count,
        'sentences': sentence_count,
    }
