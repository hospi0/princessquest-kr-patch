# -*- coding: utf-8 -*-
r"""작은 글꼴(도구·장비·마법·전투 이름) 한글화(2026-10-30)
  그림: MWAKU.B8 = 무압축 320×224 8bpp 한 장, 맨 위 8×8 칸(가로 40칸) — 칸 I = (I%40*8, I//40*8)
        스크립트(55개 MES)가 슬롯 300+I 로 칸을 잘라 등록: `0f 49 08 07 93 28` = I<100
  글자: 이름은 MES 안 `06 반각문자열 06` — 해석기 0x06006936 이 바이트를 표 0x06037244(99자)에서 찾아 슬롯 300+번호
        표에 없는 바이트 b → 코드 두 워드 교체(tools/build.py)로 슬롯 300+b. 빈 슬롯 = 272~299·400 이후(스테이트 11장 실측, 100~271 은 사용 중)
  칸 배정: 표 안 가나 칸(ﾞﾟ 제외 — 다음 글자가 ﾞﾟ 면 x 안 나감 0x06006A26) + 칸 100~160 (바이트 0xE0~0xFF·0x89~0xA5, 슬롯 b+428)
  색: 잉크 = 줄별 04 04 22 21 21 20 20 20, 그림자 91 = (+1,+1)
  python tools/smallfont.py   → 이름표 검사 + 미리보기 work/shot/small_compare.png"""
import os, re, sys, csv, unicodedata, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from bdf import Font

BDF = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf'
INK = [0x04, 0x04, 0x22, 0x21, 0x21, 0x20, 0x20, 0x20]
SHADOW = 0x91
# 대사에 원문 낱말이 없는 이름 — 음역(마법 이름은 원문 그대로 읽기)
EXTRA = {'ヒルマジック': '힐매직', 'ウイロー': '윌로', 'カスタード': '커스터드', 'シフォン': '시폰', 'ミント': '민트', 'ガトー': '가토',
         'パンナコッタ': '판나코타', 'スフレ': '수플레',
         'ファイ': '파이', 'ファイア': '파이어', 'ファイアン': '파이언', 'アクン': '아쿤', 'アクア': '아쿠아', 'アクアン': '아쿠안',
         'パール': '파르', 'パリルラ': '파리르라', 'パルライン': '파르라인', 'グラン': '그랑', 'グラヴィア': '그라비아', 'グラビトロン': '그라비트론',
         'マホウ': '마법'}
LIT = re.compile(rb'\x06([\x20-\x7e\xa1-\xdf]{1,40})\x06')


def full(s):
    return unicodedata.normalize('NFKC', s.strip().replace('-', 'ー').replace('ｰ', 'ー'))


def names():
    """{반각 리터럴 bytes: 한글 이름} — RESET·SENTO.MES 의 가나 리터럴 전부"""
    jp = {r['JP']: r['KO'] for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'uniq.tsv'), encoding='utf-8'), delimiter='\t')}
    out = collections.OrderedDict()
    for f in ('RESET.MES', 'SENTO.MES'):
        for m in LIT.finditer(open(os.path.join(ROOT, 'work', 'disc0', f), 'rb').read()):
            b = m.group(1); s = b.decode('cp932')
            if not re.search('[ｦ-ﾟ]', s): continue
            j = full(s); ko = EXTRA.get(j) or jp.get(j)
            if not ko: raise SystemExit('이름 번역 없음 %r %s' % (s, j))
            out[b] = ko
    return out


def assign(syl):
    """음절 → 리터럴 바이트. 표 안 가나 칸 먼저(슬롯 재사용), 그다음 바이트 0xE0~0xFF·0x89~0xA5 (칸 100~160, 슬롯 b+428 = 565~683 — tools/build.py)"""
    table = [0xB1 + i for i in range(44)] + [0xDD] + [0xA7 + i for i in range(9)] + [0xA6]   # ｱ..ﾜ ﾝ ｧ..ｯ ｦ
    extra = EXTRA_B
    latin = list(b'ZXQJ')                     # 라틴 칸 — 8×8 영문을 쓰는 리터럴 0개, 모자란 만큼만
    slots = table + extra + latin
    if len(syl) > len(slots): raise SystemExit('칸 모자람 %d > %d' % (len(syl), len(slots)))
    return dict(zip(syl, slots))


TBL = [0x20] + list(b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') + [0x20] * 3 + list(range(0xB1, 0xDD)) + [0xA6, 0xDD] + list(range(0xA7, 0xB0)) + [0xDE, 0xDF, 0x2D, 0x2B]


# 2026-10-30: 표 밖 바이트 0x64~0xA0(슬롯 400~460) → 전투가 400~446 을 덮어 글자가 적 그림이 됨 —
#   칸 100~131 = 바이트 0xE0~0xFF(슬롯 b+428 = 652~683) · 칸 132~160 = 0x89~0xA5(565~593), tools/build.py 반복문·A.BIN 과 짝
EXTRA_B = list(range(0xE0, 0x100)) + list(range(0x89, 0xA6))


def cell_of(b):
    """바이트 → MWAKU 칸 번호(표 안 = 슬롯 300+칸, 표 밖 = 칸 100~160)"""
    return TBL.index(b) if b in TBL else EXTRA_B.index(b) + 100


def glyph(fnt, ch):
    """→ 8×8 화소(바이트 64) — 잉크 7×7 + 그림자(+1,+1)"""
    pts, _ = fnt.draw(ch, 0, 0)
    if not pts: raise SystemExit('글자 없음 ' + ch)
    x0 = min(p[0] for p in pts); y0 = min(p[1] for p in pts)
    pts = [(x - x0, y - y0) for x, y in pts]
    if max(p[0] for p in pts) > 6 or max(p[1] for p in pts) > 6: raise SystemExit('7×7 넘침 ' + ch)
    cellb = bytearray(64)
    for x, y in pts:
        if x + 1 < 8 and y + 1 < 8 and not cellb[(y + 1) * 8 + x + 1]: cellb[(y + 1) * 8 + x + 1] = SHADOW
    for x, y in pts: cellb[y * 8 + x] = INK[y]
    return bytes(cellb)


def put_cell(img, c, g):
    x, y = c % 40 * 8, c // 40 * 8
    for r in range(8): img[(y + r) * 320 + x:(y + r) * 320 + x + 8] = g[r * 8:r * 8 + 8]


def build_mwaku(orig):
    """→ (새 MWAKU.B8 바이트, {음절: 바이트})"""
    ns = names()
    cnt = collections.Counter(c for k in ns.values() for c in k if c != ' ')
    syl = [c for c, _ in cnt.most_common()]
    m = assign(syl)
    img = bytearray(orig); fnt = Font(BDF)
    for ch, b in m.items(): put_cell(img, cell_of(b), glyph(fnt, ch))
    return bytes(img), m


def literal(b, ko, m):
    """원 리터럴 길이 유지 — 앞 공백(가운데 맞춤)은 그대로, 뒤는 공백 채움"""
    lead = len(b) - len(b.lstrip(b' '))
    enc = bytes(m[c] if c != ' ' else 0x20 for c in ko)
    out = b' ' * lead + enc
    if len(out) > len(b): raise SystemExit('이름 넘침 %r %s' % (b, ko))
    return out + b' ' * (len(b) - len(out))


def preview():
    from PIL import Image
    import struct
    d = open(os.path.join(ROOT, 'work', 'disc0', 'MWAKU.B8'), 'rb').read()
    p = open(os.path.join(ROOT, 'work', 'disc0', 'MWAKU.PAL'), 'rb').read()
    pal = []
    for i in range(256):
        c = struct.unpack_from('>H', p, i * 2)[0]
        pal.append(((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8))
    img, m = build_mwaku(d)
    ns = names()
    print('이름', len(ns), '음절', len(m), '최대 글자', max(len(v) for v in ns.values()), '슬롯 최대', max(cell_of(b) for b in m.values()))
    sys.path.insert(0, r'C:\claude\project\aww-kr-patch\tools')
    import hangul8comp
    bg = (24, 8, 40)
    show = ['브로드소드', '레더아머', '실버링', '포션', '미들포션', '힐매직', '파워드롭', '온페어리', '체인메일', '엘리먼트소드', '아르테미스피어싱', '마스터오브지오', '프린세스키스', '커스터드', '그라비트론']
    fnt = Font(BDF)
    W, H = 340, 10 * len(show) + 8
    im = Image.new('RGB', (W, H), bg); px = im.load()
    def blit(g, x, y):
        for r in range(8):
            for c in range(8):
                v = g[r * 8 + c]
                if v: px[x + c, y + r] = pal[v]
    for n, s in enumerate(show):
        y = 4 + n * 10
        for i, ch in enumerate(s): blit(glyph(fnt, ch), 6 + i * 8, y)
        for i, ch in enumerate(s):                                     # 왼쪽 갈무리7 / 오른쪽 hangul8comp
            g = hangul8comp.glyph8(ch); cellb = bytearray(64)
            for yy in range(8):
                for xx in range(8):
                    if g[yy][xx] and xx + 1 < 8 and yy + 1 < 8 and not cellb[(yy + 1) * 8 + xx + 1]: cellb[(yy + 1) * 8 + xx + 1] = SHADOW
            for yy in range(8):
                for xx in range(8):
                    if g[yy][xx]: cellb[yy * 8 + xx] = INK[yy]
            blit(bytes(cellb), 176 + i * 8, y)
    im.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', 'shot', 'small_compare.png'))
    print(os.path.join(ROOT, 'work', 'shot', 'small_compare.png'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    preview()
