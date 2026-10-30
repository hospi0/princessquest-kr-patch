# -*- coding: utf-8 -*-
r"""메뉴 그림 글자 한글화(2026-10-30)
  MWAKU.B8(8bpp 320×224, 팔레트 MWAKU.PAL) · BINDPIC 안 STATUS/SAVE/SAVELOAD.B16(15비트 BE 640×224, 가로 2배로 찍힘)
  지우기: 창 안 = 같은 줄 안쪽 빈 곳 색으로 메움 / STATUS 라벨 = 바탕 무늬가 있어 SAVE.B16 같은 자리(무늬 동일) 복사
  ⛔바탕의 プリンセスクエスト 무늬는 안 고침(2026-10-30 하스피) · 미리보기 승인 전 빌드 금지
  python tools/menu_kr.py → work/shot/menu_cmp.png (위 원본·아래 새것)"""
import os, sys, struct, collections
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from bdf import Font
import title_kr

F11 = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf')
F9 = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf')

# MWAKU: (지울 칸, 글자, 왼쪽 x, 윗 y)
MW_MENU = [((115, 52, 154, 64), [('조', 117), ('사', 141)], 52), ((115, 66, 154, 79), [('도', 117), ('구', 141)], 67),
           ((115, 80, 154, 93), [('마', 117), ('법', 141)], 81), ((115, 94, 154, 107), [('변', 117), ('신', 141)], 95),
           ((115, 108, 154, 121), [('강', 117), ('함', 141)], 109)]
MW_BUY = [((198, 52, 232, 66), [('구', 201), ('입', 219)], 53), ((198, 66, 232, 80), [('판', 201), ('매', 219)], 67)]
MW_BAR = [((18, 157, 288, 172), [('도', 21), ('구', 45), ('장', 81), ('비', 105), ('세이브/로드', 148), ('설', 251), ('정', 275)], 158)]
# 640 폭 막대(x 는 640 기준, 글자 가로 2배)
B_BAR = [((50, 18, 600, 36), [('도', 58), ('구', 104), ('장', 176), ('비', 222), ('세이브/로드', 310), ('설', 516), ('정', 562)], 22)]
LABELS = [((346, 130, 430, 150), '장비품', 350, 133, 11), ((346, 148, 400, 160), '무기', 352, 149, 9),
          ((346, 168, 410, 182), '방어구', 352, 170, 9), ((346, 191, 436, 205), '액세서리', 352, 193, 9)]
RAM = [((80, 16, 129, 33), '본체', 128), ((368, 16, 502, 33), '카트리지', 501)]


def raw(name):
    return title_kr.bindpic(name)


def px16(b):
    return list(struct.unpack('>%dH' % (640 * 224), b))


def rgb(c):
    return ((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8)


def enc(r, g, b):
    return 0x8000 | (b >> 3) << 10 | (g >> 3) << 5 | r >> 3


def text_pts(fnt, s):
    pts, w = fnt.draw(s, 0, 0)
    y0 = min(p[1] for p in pts)
    return [(x, y - y0) for x, y in pts], w


def fill_rows8(d, box, sx):
    for y in range(box[1], box[3]):
        c = collections.Counter(d[y * 320 + x] for x in sx).most_common(1)[0][0]
        for x in range(box[0], box[2]): d[y * 320 + x] = c


def draw8(d, s, x0, y0, ink, sh):
    pts, _ = text_pts(F11, s)
    for x, y in pts:
        p = (y0 + y + 1) * 320 + x0 + x + 1
        d[p] = sh
    for x, y in pts: d[(y0 + y) * 320 + x0 + x] = ink


def mwaku(orig, pal):
    d = bytearray(orig)
    area = collections.Counter(orig[y * 320 + x] for y in range(52, 120) for x in range(118, 152))
    bright = max(area, key=lambda i: sum(pal[i]))
    sh = min((i for i in area if i), key=lambda i: sum(pal[i]))
    for rows, sx in ((MW_MENU, range(109, 114)), (MW_BUY, range(190, 197)), (MW_BAR, range(290, 298))):
        for box, items, y0 in rows:
            fill_rows8(d, box, sx)
            for s, x in items: draw8(d, s, x, y0, bright, sh)
    return bytes(d), bright, sh


def put16(p, fnt, s, x0, y0, ink, shadow, w2=True):
    pts, w = text_pts(fnt, s)
    k = 2 if w2 else 1
    for x, y in pts:
        for i in range(k):
            for dx in (k,):
                p[(y0 + y + 1) * 640 + x0 + x * k + i + dx] = shadow
    for x, y in pts:
        for i in range(k):
            c = ink(y) if callable(ink) else ink
            p[(y0 + y) * 640 + x0 + x * k + i] = c


def fill_rows16(p, box, sx):
    for y in range(box[1], box[3]):
        c = collections.Counter(p[y * 640 + x] for x in sx).most_common(1)[0][0]
        for x in range(box[0], box[2]): p[y * 640 + x] = c


def status(b, clean, clean2):
    p = px16(b); q = px16(clean); q2 = px16(clean2)
    white = enc(232, 232, 232); dark = enc(16, 8, 24)
    for box, items, y0 in B_BAR:
        fill_rows16(p, box, range(40, 48))
        for s, x in items: put16(p, F11, s, x, y0, white, dark)
    green = lambda y: enc(232, 248, 232) if y < 2 else enc(120, 216, 160) if y < 5 else enc(32, 136, 96)
    for box, s, x, y, sz in LABELS:
        for yy in range(box[1], box[3]):
            src, sy = (q, yy) if yy >= 138 else (q2, yy - 112)  # 무늬 세로 주기 112 — SAVE 창에 걸린 줄은 OPTION 위쪽(창 없음)에서
            p[yy * 640 + box[0]:yy * 640 + box[2]] = src[sy * 640 + box[0]:sy * 640 + box[2]]
        put16(p, F11 if sz == 11 else F9, s, x, y, green, dark)
    return struct.pack('>%dH' % (640 * 224), *p)


def save(b):
    p = px16(b); white = enc(232, 232, 232); dark = enc(16, 8, 24)
    for box, s, right in RAM:
        fill_rows16(p, box, range(45, 60))
        _, w = text_pts(F11, s)
        put16(p, F11, s, right - w * 2 - 4, 19, white, dark)
    return struct.pack('>%dH' % (640 * 224), *p)


def save01h(b):
    """세이브 소개 그림(SIRO1A1 에서 씀) — 흰 글자를 하늘로 메우고 큰 글자, 가로 2배"""
    import cv2, numpy as np
    from PIL import ImageDraw, ImageFont
    a = np.array(img16(b))
    box = (40, 22, 610, 70)                                               # 머리카락 밝은 분홍은 문턱값으로 빠짐
    roi = a[box[1]:box[3], box[0]:box[2]]
    mask = (roi.min(axis=2) > 225).astype('uint8') * 255                  # 흰 글자(둘레까지 넓힘)
    mask = cv2.dilate(mask, np.ones((5, 7), 'uint8'))
    a[box[1]:box[3], box[0]:box[2]] = cv2.inpaint(roi[:, :, ::-1].copy(), mask, 5, cv2.INPAINT_TELEA)[:, :, ::-1]
    S = 4; W, H = 280 * S, 50 * S
    t = Image.new('L', (W, H), 0); d = ImageDraw.Draw(t)
    F = ImageFont.truetype(r'C:\claude\utils\font\jua\Jua-Regular.ttf', 38 * S)
    d.text((W // 2, H // 2), '세이브해요옷!!', font=F, fill=255, anchor='mm')
    t = t.resize((560, 50), Image.LANCZOS)
    k = np.array(t).astype(float)[:, :, None] / 255
    ox, oy = 45, 22
    a[oy:oy + 50, ox:ox + 560] = (a[oy:oy + 50, ox:ox + 560] * (1 - k) + 248 * k).astype('uint8')
    v = [enc(int(r), int(g), int(c)) for r, g, c in a.reshape(-1, 3)]
    return struct.pack('>%dH' % (640 * 224), *v)


def img16(b):
    im = Image.new('RGB', (640, 224)); im.putdata([rgb(c) for c in px16(b)]); return im


def build():
    """→ {이름: 새 바이트}"""
    pal0 = open(os.path.join(ROOT, 'work', 'disc0', 'MWAKU.PAL'), 'rb').read()
    pal = [rgb(struct.unpack_from('>H', pal0, i * 2)[0]) for i in range(256)]
    o = {n: raw(n) for n in ('STATUSB16', 'SAVEB16', 'SAVELOADB16')}
    mw, br, sh = mwaku(open(os.path.join(ROOT, 'work', 'disc0', 'MWAKU.B8'), 'rb').read(), pal)
    print('MWAKU 글자색', br, pal[br], '그림자', sh, pal[sh])
    return mw, pal, o, {'STATUSB16': status(o['STATUSB16'], o['SAVEB16'], raw('OPTIONB16')), 'SAVEB16': save(o['SAVEB16']), 'SAVELOADB16': save(o['SAVELOADB16'])}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    mw, pal, o, n = build()
    m0 = open(os.path.join(ROOT, 'work', 'disc0', 'MWAKU.B8'), 'rb').read()
    def mi(b):
        im = Image.frombytes('P', (320, 224), b); im.putpalette([v for c in pal for v in c]); return im.convert('RGB')
    sheet = Image.new('RGB', (1290, 1160), (70, 70, 70))
    a, b = mi(m0), mi(mw)
    sheet.paste(a.crop((100, 45, 240, 125)).resize((420, 240), Image.NEAREST), (0, 0))
    sheet.paste(b.crop((100, 45, 240, 125)).resize((420, 240), Image.NEAREST), (430, 0))
    sheet.paste(a.crop((0, 148, 310, 180)).resize((620, 64), Image.NEAREST), (0, 250))
    sheet.paste(b.crop((0, 148, 310, 180)).resize((620, 64), Image.NEAREST), (640, 250))
    y = 320
    for k in ('STATUSB16', 'SAVEB16', 'SAVELOADB16'):
        h = 224 if k == 'STATUSB16' else 40
        sheet.paste(img16(o[k]).crop((0, 0, 640, h)), (0, y)); sheet.paste(img16(n[k]).crop((0, 0, 640, h)), (645, y)); y += h + 6
    z = img16(n['STATUSB16']).crop((340, 125, 450, 210)).resize((440, 340), Image.NEAREST)
    z0 = img16(o['STATUSB16']).crop((340, 125, 450, 210)).resize((440, 340), Image.NEAREST)
    sheet.paste(z0, (0, y)); sheet.paste(z, (450, y))
    sheet.save(os.path.join(ROOT, 'work', 'shot', 'menu_cmp.png'))
    s0 = raw('SAVE01HB16'); s1 = save01h(s0)
    c = Image.new('RGB', (1290, 224), (70, 70, 70)); c.paste(img16(s0), (0, 0)); c.paste(img16(s1), (650, 0))
    c.save(os.path.join(ROOT, 'work', 'shot', 'save01h_cmp.png'))
    print(os.path.join(ROOT, 'work', 'shot', 'menu_cmp.png'))


if __name__ == '__main__':
    main()
