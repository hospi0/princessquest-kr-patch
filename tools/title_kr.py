# -*- coding: utf-8 -*-
r"""타이틀 그림 한글화(2026-10-30) — BINDPIC.DAT 안 TITLE.B16(무압축 15비트 BE 320×224, 스테이트 슬롯 0)
  로고 윗줄 プリンセスクエスト(x94~185, y22~35, 연보라) → «프린세스 퀘스트»
  저작권 줄 いつきあやな(x126~184, y206~215, 금색) → «이츠키 아야나»
  ⛔미리보기 승인 전 빌드 금지. PRESS START·NEW GAME 등(TITLESP.B16, 슬롯 1~7)은 영문이라 그대로
  python tools/title_kr.py  → work/shot/title_cmp.png (원본|새것)"""
import os, sys, struct
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc
from bdf import Font

TTF = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.otf'
BDF9 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf'
LOGO = (94, 22, 185, 35)
NAME = (126, 206, 184, 215)


def bindpic(name):
    t = open(os.path.join(ROOT, 'work', 'disc0', 'BINDPIC.TBL'), 'rb').read()
    for i in range(0, len(t) - 18, 19):
        if t[i:i + 11].decode('latin1').replace(' ', '') == name:
            o, z = struct.unpack_from('>II', t, i + 11)
            break
    fs = {p: (l, s) for p, l, s in disc.files(disc.bin_path(0))}
    l, s = fs['/BINDPIC.DAT']
    return disc.sec(open(disc.bin_path(0), 'rb'), l, (s + 2047) // 2048)[o:o + z]


def to_rgb(b):
    im = Image.new('RGB', (320, 224))
    im.putdata([((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8) for c in struct.unpack('>%dH' % (320 * 224), b)])
    return im


def logo_layer():
    S = 6
    W, H = (LOGO[2] - LOGO[0] + 7) * S, (LOGO[3] - LOGO[1] + 5) * S
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    F = ImageFont.truetype(TTF, 13 * S)
    txt = '프린세스 퀘스트'
    w = d.textlength(txt, font=F)
    s = (LOGO[2] - LOGO[0] - 2) * S / w
    F = ImageFont.truetype(TTF, int(13 * S * s))
    b = d.textbbox((0, 0), txt, font=F)
    d.text(((W - b[2] + b[0]) // 2 - b[0], (H - b[3] + b[1]) // 2 - b[1]), txt, font=F, fill=255)
    m = m.transform((W, H), Image.AFFINE, (1, 0.25, -0.25 * H / 2, 0, 1, 0), Image.BICUBIC)   # 원본처럼 오른쪽으로 기움
    return m.resize((W // S, H // S), Image.LANCZOS)


def edit(im):
    px = im.load()
    for y in range(LOGO[1] - 1, LOGO[3] + 2):                  # 로고 윗줄 지우기 — 금색 필기체는 남김
        for x in range(LOGO[0] - 2, LOGO[2] + 3):
            r, g, b = px[x, y]
            if not r > b + 16: px[x, y] = (0, 0, 0)
    a = logo_layer(); ox, oy = LOGO[0] - 3, LOGO[1] - 2
    ap = a.load()
    glow = a.filter(ImageFilter.GaussianBlur(0.8)).load()
    for y in range(a.height):
        for x in range(a.width):
            X, Y = ox + x, oy + y
            k, g = ap[x, y] / 255, glow[x, y] / 255
            if max(k, g) < 0.05: continue
            t = y / a.height
            ink = (236 - int(44 * t), 232 - int(52 * t), 248 - int(16 * t))
            halo = (72, 64, 120)
            bg = px[X, Y]
            if bg[0] > bg[2] + 16: continue                    # 금색 위엔 안 찍음
            c = [int(halo[i] * g * 0.9) for i in range(3)]
            px[X, Y] = tuple(min(255, int(c[i] * (1 - k) + ink[i] * k)) for i in range(3))
    for y in range(NAME[1], NAME[3] + 1):                      # 이름 줄
        for x in range(NAME[0] - 1, NAME[2] + 2):
            px[x, y] = (0, 0, 0)
    pts, w = Font(BDF9).draw('이츠키 아야나', 0, 0)
    x0 = NAME[0] + (NAME[2] - NAME[0] + 1 - w) // 2; y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    top = NAME[1] + (NAME[3] - NAME[1] + 1 - (y1 - y0 + 1)) // 2
    for x, y in pts: px[x0 + x + 1, top + y - y0 + 1] = (72, 48, 16)
    for x, y in pts:
        px[x0 + x, top + y - y0] = (248, 232, 136) if y - y0 < y1 - y0 else (240, 216, 120)
    return im, w


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    b = bindpic('TITLEB16')
    o = to_rgb(b); n, w = edit(o.copy())
    print('이름 폭', w)
    c = Image.new('RGB', (644, 224), (60, 60, 60)); c.paste(o, (0, 0)); c.paste(n, (324, 0))
    c.resize((1288, 448), Image.NEAREST).save(os.path.join(ROOT, 'work', 'shot', 'title_cmp.png'))
    z = Image.new('RGB', (2 * 110 + 4, 2 * 34), (60, 60, 60))
    for k, im in enumerate((o, n)):
        z.paste(im.crop((85, 15, 195, 42)), (k * 114, 0)); z.paste(im.crop((85, 200, 195, 220)), (k * 114, 40))
    z.resize((z.width * 4, z.height * 4), Image.NEAREST).save(os.path.join(ROOT, 'work', 'shot', 'title_zoom.png'))


if __name__ == '__main__':
    main()
