#!/usr/bin/env python3
from __future__ import annotations

import io
import os
from pathlib import Path

import requests
import urllib3
from PIL import Image, ImageDraw, ImageFilter, ImageFont

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = os.environ.get('SATOORI_API_BASE', 'https://satoori-api.protfolio.store/api').rstrip('/')
TWEMOJI_BASE = 'https://raw.githubusercontent.com/jdecked/twemoji/main/assets/72x72'
CACHE_DIR = Path(os.environ.get('SATOORI_ICON_CACHE', '/tmp/satoori_twemoji_cache'))
ROOT_OUT_DIR = Path(os.environ.get('SATOORI_ASSET_OUT', '/tmp/satoori_generated_assets'))
WORD_OUT_DIR = ROOT_OUT_DIR / 'words'
SENTENCE_OUT_DIR = ROOT_OUT_DIR / 'sentences'
CHAPTER_OUT_DIR = ROOT_OUT_DIR / 'chapters'
FONT_PATH = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
SMALL_FONT_PATH = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
CANVAS_WORD = (1200, 900)
CANVAS_SENTENCE = (1600, 900)
CANVAS_CHAPTER = (1280, 720)

WORD_ICON_MAP = {
    '감사합니다': ('1f64f', '2728'),
    '실례합니다': ('1f647', '1f64f'),
    '괜찮아요': ('1f44c', '1f60a'),
    '조금만 기다려 주세요': ('23f3', '1f552'),
    '처음 뵙겠습니다': ('1f44b', '1f91d'),
    '잘 부탁드립니다': ('1f91d', '1f4aa'),
    '전화드릴게요': ('260e', '1f4de'),
    '확인해 볼게요': ('1f50d', '2705'),
    '포장': ('1f4e6', '1f6cd'),
    '맵기': ('1f336', '1f525'),
    '영수증': ('1f9fe', '1f4b3'),
    '현금': ('1f4b5', '1f4b8'),
    '카드': ('1f4b3', '2728'),
    '추가 주문': ('1f6d2', '2795'),
    '계산': ('1f4b0', '1f9fe'),
    '반찬': ('1f35a', '1f372'),
    '진료 예약': ('1f3e5', '1f5d3'),
    '접수': ('1f4dd', '1f3e5'),
    '대기 번호': ('1f522', '23f3'),
    '신분증': ('1f194', '1f464'),
    '처방전': ('1f48a', '1f4c4'),
    '주민센터': ('1f3db', '1f4c4'),
    '서류': ('1f4c4', '1f5c2'),
    '발급': ('1f4e4', '2728'),
    '회의': ('1f4ac', '1f465'),
    '업무 보고': ('1f4ca', '1f4bb'),
    '동료': ('1f465', '1f91d'),
    '마감': ('23f0', '2705'),
    '일정': ('1f4c5', '1f4cc'),
    '휴가': ('1f3d6', '2600'),
    '인수인계': ('1f4c1', '1f504'),
    '피드백': ('1f5e3', '1f4ac'),
    '환승': ('1f504', '1f687'),
    '정류장': ('1f68f', '1f68c'),
    '출구': ('1f6aa', '27a1'),
    '요금': ('1f4b8', '1f68c'),
    '교통카드': ('1f4b3', '1f68c'),
    '노선': ('1f5fa', '1f68c'),
    '막차': ('1f68c', '1f311'),
    '길 안내': ('1f9ed', '1f5fa'),
    '교환': ('1f504', '1f6cd'),
    '환불': ('1f4b8', '2b05'),
    '사이즈': ('1f457', '1f4cf'),
    '할인': ('1f3f7', '1f4b0'),
    '포인트': ('2b50', '1f4b3'),
    '결제': ('1f4b3', '1f4b0'),
    '품절': ('274c', '1f6d2'),
    '재고': ('1f4e6', '1f4e5'),
    '수강 신청': ('1f4da', '270d'),
    '과제': ('1f4d6', '270f'),
    '발표': ('1f3a4', '1f4ca'),
    '시험 범위': ('1f4da', '1f4dd'),
    '출석': ('2705', '1f393'),
    '지각': ('23f0', '1f3c3'),
    '보충 수업': ('1f393', '2795'),
    '상담': ('1f5e8', '1f464'),
    '계좌': ('1f3e6', '1f4b0'),
    '이체': ('1f4b8', '27a1'),
    '비밀번호': ('1f511', '1f4f1'),
    '한도': ('1f6ab', '1f4b3'),
    '수수료': ('1f4b1', '1f4b0'),
    '요금제': ('1f4f1', '1f4c3'),
    '본인 인증': ('1f510', '1f194'),
    '재발급': ('1f504', '1f194'),
}

CHAPTER_THEME = {
    1: {'title': '인사와 일상', 'bg': ('#EFF6FF', '#DBEAFE'), 'accent': '#2563EB', 'icons': ('1f44b', '1f91d', '1f4de')},
    2: {'title': '식당과 음식', 'bg': ('#FFF7ED', '#FFEDD5'), 'accent': '#EA580C', 'icons': ('1f35c', '1f9fe', '1f4b3')},
    3: {'title': '병원과 행정', 'bg': ('#F0FDF4', '#DCFCE7'), 'accent': '#16A34A', 'icons': ('1f3e5', '1f48a', '1f194')},
    4: {'title': '직장과 대화', 'bg': ('#F5F3FF', '#EDE9FE'), 'accent': '#7C3AED', 'icons': ('1f4ca', '1f4ac', '1f4c1')},
    5: {'title': '교통과 길찾기', 'bg': ('#ECFEFF', '#CFFAFE'), 'accent': '#0F766E', 'icons': ('1f68c', '1f5fa', '1f687')},
    6: {'title': '쇼핑과 결제', 'bg': ('#FFF1F2', '#FFE4E6'), 'accent': '#E11D48', 'icons': ('1f6cd', '1f457', '1f4b3')},
    7: {'title': '학교와 공부', 'bg': ('#FEFCE8', '#FEF3C7'), 'accent': '#CA8A04', 'icons': ('1f4da', '270f', '1f393')},
    8: {'title': '은행과 통신', 'bg': ('#F8FAFC', '#E2E8F0'), 'accent': '#334155', 'icons': ('1f3e6', '1f4f1', '1f511')},
}

SENTENCE_RULES = [
    (('전화', '연락'), ('260e', '1f4de')),
    (('기다려', '잠시만'), ('23f3', '1f552')),
    (('확인',), ('1f50d', '2705')),
    (('맵',), ('1f336', '1f525')),
    (('포장',), ('1f4e6', '1f6cd')),
    (('영수증', '영수표'), ('1f9fe', '1f4b3')),
    (('카드', '결제', '계산'), ('1f4b3', '1f4b0')),
    (('병원', '진료', '처방'), ('1f3e5', '1f48a')),
    (('신분증', '공민증'), ('1f194', '1f464')),
    (('회의',), ('1f4ac', '1f465')),
    (('보고', '자료'), ('1f4ca', '1f4bb')),
    (('휴가',), ('1f3d6', '2600')),
    (('지하철', '버스', '택시'), ('1f68c', '1f5fa')),
    (('출구',), ('1f6aa', '27a1')),
    (('교통카드',), ('1f4b3', '1f68c')),
    (('할인',), ('1f3f7', '1f4b0')),
    (('품절',), ('274c', '1f6d2')),
    (('수강', '과제', '시험', '출석', '지각', '수업'), ('1f4da', '270f')),
    (('상담',), ('1f5e8', '1f464')),
    (('계좌', '이체', '수수료'), ('1f3e6', '1f4b8')),
    (('비밀번호', '인증'), ('1f511', '1f4f1')),
    (('요금제', '휴대폰', '유심', '인터넷'), ('1f4f1', '1f4c3')),
]


def get_font(size: int, secondary: bool = False):
    return ImageFont.truetype(SMALL_FONT_PATH if secondary else FONT_PATH, size)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update({'Accept': 'application/json'})
    return s


def fetch_json(s: requests.Session, path: str):
    r = s.get(f'{API_BASE}{path}', timeout=60)
    r.raise_for_status()
    return r.json()


def ensure_icon(s: requests.Session, code: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f'{code}.png'
    if path.exists():
        return path
    r = s.get(f'{TWEMOJI_BASE}/{code}.png', timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int):
    words = text.split(' ')
    lines, current = [], ''
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


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int, max_lines: int = 2):
    for size in range(start_size, min_size - 1, -2):
        font = get_font(size)
        lines = wrap_text(draw, text, font, max_width)
        width = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)
        if width <= max_width and len(lines) <= max_lines:
            return font, lines
    font = get_font(min_size)
    return font, wrap_text(draw, text, font, max_width)


def hex_to_rgb(value: str):
    value = value.lstrip('#')
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def gradient_canvas(size: tuple[int, int], start: str, end: str):
    w, h = size
    sr, sg, sb = hex_to_rgb(start)
    er, eg, eb = hex_to_rgb(end)
    img = Image.new('RGBA', size)
    px = img.load()
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(sr + (er - sr) * ratio)
        g = int(sg + (eg - sg) * ratio)
        b = int(sb + (eb - sb) * ratio)
        for x in range(w):
            px[x, y] = (r, g, b, 255)
    return img


def add_shadow(base: Image.Image, bbox, radius=34, offset=(0, 18), opacity=60):
    shadow = Image.new('RGBA', base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = bbox
    ox, oy = offset
    draw.rounded_rectangle((x1 + ox, y1 + oy, x2 + ox, y2 + oy), radius=radius, fill=(15, 23, 42, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    return Image.alpha_composite(base, shadow)


def load_icon(icon_path: Path, size: int):
    icon = Image.open(icon_path).convert('RGBA')
    return icon.resize((size, size), Image.LANCZOS)


def pick_sentence_icons(sentence: str, chapter_id: int):
    for keywords, icons in SENTENCE_RULES:
        if any(keyword in sentence for keyword in keywords):
            return icons
    return CHAPTER_THEME[chapter_id]['icons'][:2]


def save_png(img: Image.Image, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    out_path.write_bytes(buf.getvalue())
    return out_path


def make_word_card(s: requests.Session, word: dict) -> Path:
    theme = CHAPTER_THEME[word['chapter']]
    img = gradient_canvas(CANVAS_WORD, *theme['bg'])
    img = add_shadow(img, (60, 60, 1140, 840), radius=40)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((60, 60, 1140, 840), radius=40, fill='white')
    draw.rounded_rectangle((96, 96, 440, 150), radius=26, fill=theme['accent'])
    draw.text((268, 123), theme['title'], font=get_font(30), anchor='mm', fill='white')

    draw.rounded_rectangle((110, 190, 1090, 520), radius=34, fill=theme['accent'])
    draw.rounded_rectangle((130, 210, 1070, 500), radius=30, fill='#F8FAFC')

    icon_codes = WORD_ICON_MAP[word['korean_word']]
    icons = [load_icon(ensure_icon(s, code), 220) for code in icon_codes]
    img.alpha_composite(icons[0], (240, 245))
    img.alpha_composite(icons[1], (730, 245))

    draw.rounded_rectangle((480, 255, 720, 455), radius=28, fill=theme['accent'])
    draw.text((600, 355), word['korean_word'][:2], font=get_font(90), anchor='mm', fill='white')

    title_font, title_lines = fit_font(draw, word['korean_word'], 920, 72, 42)
    y = 585
    for line in title_lines:
        draw.text((600, y), line, font=title_font, anchor='mm', fill='#0F172A')
        y += title_font.size + 12

    sub_font, sub_lines = fit_font(draw, word['north_korean_word'], 900, 38, 26)
    for line in sub_lines:
        draw.text((600, y + 14), line, font=sub_font, anchor='mm', fill='#475569')
        y += sub_font.size + 10

    footer = f"표준어 ↔ 북한식 표현 | {word['chapter_title']}"
    draw.text((600, 792), footer, font=get_font(24, secondary=True), anchor='mm', fill='#94A3B8')

    return save_png(img, WORD_OUT_DIR / f"word-{word['id']:03d}.png")


def make_sentence_card(s: requests.Session, sentence: dict) -> Path:
    theme = CHAPTER_THEME[sentence['chapter']]
    img = gradient_canvas(CANVAS_SENTENCE, *theme['bg'])
    img = add_shadow(img, (70, 70, 1530, 830), radius=42)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((70, 70, 1530, 830), radius=42, fill='white')
    draw.rounded_rectangle((110, 110, 470, 168), radius=28, fill=theme['accent'])
    draw.text((290, 139), theme['title'], font=get_font(32), anchor='mm', fill='white')

    draw.rounded_rectangle((1140, 110, 1480, 168), radius=28, fill='#E2E8F0')
    draw.text((1310, 139), '문장 장면 카드', font=get_font(26, secondary=True), anchor='mm', fill='#334155')

    icon_codes = pick_sentence_icons(sentence['korean_sentence'], sentence['chapter'])
    left_icon = load_icon(ensure_icon(s, icon_codes[0]), 240)
    right_icon = load_icon(ensure_icon(s, icon_codes[1]), 240)

    draw.rounded_rectangle((120, 220, 1480, 520), radius=34, fill=theme['accent'])
    draw.rounded_rectangle((140, 240, 1460, 500), radius=30, fill='#F8FAFC')
    img.alpha_composite(left_icon, (200, 250))
    img.alpha_composite(right_icon, (1160, 250))

    title_font, title_lines = fit_font(draw, sentence['korean_sentence'], 800, 64, 36, max_lines=3)
    y = 280
    for line in title_lines:
        draw.text((800, y), line, font=title_font, anchor='mm', fill='#0F172A')
        y += title_font.size + 10

    subtitle_font, subtitle_lines = fit_font(draw, sentence['north_korean_wording'], 1080, 36, 24, max_lines=3)
    y = 585
    draw.text((160, 575), '북한식 표현', font=get_font(24, secondary=True), fill='#64748B')
    for line in subtitle_lines:
        draw.text((800, y), line, font=subtitle_font, anchor='mm', fill='#475569')
        y += subtitle_font.size + 8

    footer = f"학습 문장 #{sentence['id']} | 실전 장면 연상용 시각 카드"
    draw.text((800, 770), footer, font=get_font(24, secondary=True), anchor='mm', fill='#94A3B8')

    return save_png(img, SENTENCE_OUT_DIR / f"sentence-{sentence['id']:03d}.png")


def make_chapter_cover(s: requests.Session, chapter: dict) -> Path:
    theme = CHAPTER_THEME[chapter['id']]
    img = gradient_canvas(CANVAS_CHAPTER, *theme['bg'])
    img = add_shadow(img, (50, 50, 1230, 670), radius=42)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((50, 50, 1230, 670), radius=42, fill='white')
    draw.rounded_rectangle((84, 86, 390, 142), radius=28, fill=theme['accent'])
    draw.text((237, 114), 'Chapter Cover', font=get_font(28, secondary=True), anchor='mm', fill='white')

    draw.text((100, 228), chapter['title'], font=get_font(64), fill='#0F172A')
    meta = f"난이도: {chapter.get('difficulty', 'beginner')} · 태그: {chapter.get('context_tag', '')}"
    draw.text((100, 304), meta, font=get_font(28, secondary=True), fill='#64748B')

    icon_positions = [(760, 150, 180), (930, 285, 180), (610, 340, 180)]
    for code, (x, y, size) in zip(theme['icons'], icon_positions):
        blob = Image.new('RGBA', CANVAS_CHAPTER, (0, 0, 0, 0))
        blob_draw = ImageDraw.Draw(blob)
        blob_draw.ellipse((x - 18, y - 18, x + size + 18, y + size + 18), fill=hex_to_rgb(theme['accent']) + (50,))
        img = Image.alpha_composite(img, blob)
        icon = load_icon(ensure_icon(s, code), size)
        img.alpha_composite(icon, (x, y))

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((100, 520, 500, 590), radius=24, fill='#F8FAFC', outline='#E2E8F0')
    draw.text((300, 555), '표준어 · 북한식 표현 · 장면 학습', font=get_font(24, secondary=True), anchor='mm', fill='#334155')

    return save_png(img, CHAPTER_OUT_DIR / f"chapter-{chapter['id']:02d}.png")


def collect_existing_assets(assets: list[dict], category: str, key: str):
    grouped: dict[int, list[int]] = {}
    for asset in assets:
        if asset.get('category') != category:
            continue
        target_id = asset.get(key)
        if target_id:
            grouped.setdefault(int(target_id), []).append(int(asset['id']))
    return grouped


def upload_asset(s: requests.Session, category: str, label: str, key_text: str, path: Path, chapter_id: int | None = None, word_id: int | None = None, sentence_id: int | None = None):
    with path.open('rb') as f:
        files = {'image': (path.name, f, 'image/png')}
        data = {'category': category, 'label': label, 'key_text': key_text}
        if chapter_id:
            data['chapter'] = str(chapter_id)
        if word_id:
            data['word'] = str(word_id)
        if sentence_id:
            data['sentence'] = str(sentence_id)
        r = s.post(f'{API_BASE}/media-assets/', data=data, files=files, timeout=120)
        r.raise_for_status()
        return r.json()


def delete_assets(s: requests.Session, ids: list[int]):
    for asset_id in ids:
        r = s.delete(f'{API_BASE}/media-assets/{asset_id}/', timeout=60)
        if r.status_code not in (204, 404):
            r.raise_for_status()


def main():
    s = session()
    chapters = fetch_json(s, '/chapters/')
    assets = fetch_json(s, '/media-assets/')
    existing_words = collect_existing_assets(assets, 'word', 'word')
    existing_sentences = collect_existing_assets(assets, 'sentence', 'sentence')
    existing_chapters = collect_existing_assets(assets, 'chapter', 'chapter')

    uploaded_words = uploaded_sentences = uploaded_chapters = 0

    for chapter in chapters:
        cover_path = make_chapter_cover(s, chapter)
        delete_assets(s, existing_chapters.get(chapter['id'], []))
        upload_asset(s, 'chapter', f"{chapter['title']} 자동 커버", chapter['title'], cover_path, chapter_id=chapter['id'])
        uploaded_chapters += 1

        words = fetch_json(s, f"/chapters/{chapter['id']}/words/")
        for word in words:
            word['chapter_title'] = chapter['title']
            path = make_word_card(s, word)
            delete_assets(s, existing_words.get(word['id'], []))
            upload_asset(
                s,
                'word',
                f"{word['korean_word']} 자동 카드",
                word['korean_word'],
                path,
                chapter_id=chapter['id'],
                word_id=word['id'],
            )
            uploaded_words += 1
            print(f"uploaded word={word['id']} {word['korean_word']}")

        sentences = fetch_json(s, f"/chapters/{chapter['id']}/sentences/")
        for sentence in sentences:
            sentence['north_korean_wording'] = sentence['north_korean_sentence']
            path = make_sentence_card(s, sentence)
            delete_assets(s, existing_sentences.get(sentence['id'], []))
            upload_asset(
                s,
                'sentence',
                f"문장 {sentence['id']} 자동 장면 카드",
                sentence['korean_sentence'],
                path,
                chapter_id=chapter['id'],
                sentence_id=sentence['id'],
            )
            uploaded_sentences += 1
            print(f"uploaded sentence={sentence['id']}")

    print(f'uploaded chapters={uploaded_chapters} words={uploaded_words} sentences={uploaded_sentences}')
    print(f'output root={ROOT_OUT_DIR}')


if __name__ == '__main__':
    main()
