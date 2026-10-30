# -*- coding: utf-8 -*-
r"""전투 메뉴 그림 한글화(2026-10-30, 하스피 «메뉴도 찾아서 한글화») — BINDFACE.DAT 안 SENTOWAK.B8(8bpp 320×224, 0x338E00)
  출처 찾은 길: 전투 스테이트 VDP1 56×88 텍스처(VRAM 0x1E180) → WorkRAML 0x00240000 에 폭 320 그림 → BINDFACE.TBL «SENTOWAKB8»
  攻撃·道具·逃亡·魔法(왼쪽 패널 4줄) / 攻撃·道具·逃亡(오른쪽 3줄) → 공격·도구·도망·마법, 글자 칸 x 25·43(오른쪽 225·244), 윗줄 y 16·31·45·60
  지우기 = 그 줄 패널 안쪽 빈 곳 색(menu_kr.fill_rows8)
  글자 = 나눔고딕 ExtraBold 안티에일리어싱(하스피 «안티 넣고 고해상도», 원래 한자 칸 11×12 꽉) — 8배로 그려 줄여 덮임 비율,
         그림자(+1,+1) 먼저 → 글자색(12번)과 바탕을 섞은 색을 그림에 쓰인 팔레트 색 중 가장 가까운 번호로
  python tools/sentowak_kr.py → work/shot/sentowak_cmp.png (왼쪽 원본 | 오른쪽 새것, 실제 색)"""
import os, sys, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import menu_kr

OFF, SIZE, PAL = 0x338E00, 320 * 224, 0xB800              # BINDFACE.DAT 안 자리(BINDFACE.TBL)
WORDS = ['공격', '도구', '도망', '마법']
ROWS = [16, 31, 45, 60]
PANELS = [((22, 14, 57, 74), (25, 43), range(15, 21), 4),      # (지울 칸, 두 글자 x, 바탕 표본 열, 줄 수)
          ((222, 14, 256, 58), (225, 244), range(216, 222), 3)]
INK = 12
TTF = os.path.join('C:' + os.sep, 'claude', 'utils', 'font', 'nanum-gothic', 'NanumGothicExtraBold.ttf')
CW, CH, SS = 11, 12, 8                                          # 글자 칸·확대 배율


def coverage(ch):
    from PIL import Image, ImageDraw, ImageFont
    W, H = CW * SS, CH * SS
    f = ImageFont.truetype(TTF, H)
    im = Image.new('L', (W * 2, H * 2), 0); dr = ImageDraw.Draw(im)
    dr.text((W, H), ch, font=f, fill=255, anchor='mm')
    g = im.crop(im.getbbox()).resize((W, H), Image.LANCZOS).resize((CW, CH), Image.BOX)   # 칸 꽉 채움
    return [[g.getpixel((x, y)) / 255 for x in range(CW)] for y in range(CH)]


def draw_aa(d, ch, x0, y0, cols, used, sh):
    cov = coverage(ch)
    def put(x, y, rgb_new):
        d[y * 320 + x] = min(used, key=lambda i: sum((a - b) ** 2 for a, b in zip(cols[i], rgb_new)))
    def mix(c1, c2, a): return tuple(c1[k] * (1 - a) + c2[k] * a for k in range(3))
    for y in range(CH):                                         # 그림자
        for x in range(CW):
            a = cov[y][x] * 0.85
            if a > 0.05: px, py = x0 + x + 1, y0 + y + 1; put(px, py, mix(cols[d[py * 320 + px]], cols[sh], a))
    for y in range(CH):
        for x in range(CW):
            a = cov[y][x]
            if a > 0.05: px, py = x0 + x, y0 + y; put(px, py, mix(cols[d[py * 320 + px]], cols[INK], a))


def build(orig):
    d = bytearray(orig)
    area = collections.Counter(orig[y * 320 + x] for y in range(14, 74) for x in range(22, 57))
    pal = open(os.path.join(ROOT, 'work', 'disc0', 'SENTOWAK.PAL'), 'rb').read()
    cols = [menu_kr.rgb(struct.unpack_from('>H', pal, i * 2)[0]) for i in range(256)]
    sh = min((i for i in area if i and i != INK), key=lambda i: sum(cols[i]))
    used = sorted(set(orig))                                       # 그림에 실제 쓰인 팔레트 색만
    for box, xs, sx, n in PANELS:
        menu_kr.fill_rows8(d, box, sx)
        for w, y in zip(WORDS[:n], ROWS[:n]):
            for ch, x in zip(w, xs): draw_aa(d, ch, x, y, cols, used, sh)
    return bytes(d), cols


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    from PIL import Image
    orig = open(os.path.join(ROOT, 'work', 'disc0', 'SENTOWAK.B8'), 'rb').read()
    new, cols = build(orig)
    im = Image.new('RGB', (640 + 8, 224))
    for k, b in enumerate((orig, new)):
        part = Image.new('RGB', (320, 224)); part.putdata([cols[v] for v in b])
        im.paste(part, (k * 328, 0))
    im.crop((0, 0, 648, 90)).resize((648 * 3, 270), Image.NEAREST).save(os.path.join(ROOT, 'work', 'shot', 'sentowak_cmp.png'))
    print('바뀐 화소', sum(1 for a, b in zip(orig, new) if a != b), '→ work/shot/sentowak_cmp.png')


if __name__ == '__main__':
    main()
