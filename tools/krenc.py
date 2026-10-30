# -*- coding: utf-8 -*-
r"""한글 인코더·글꼴(2026-10-30) — KANJI.FON 칸 배정 + MES 다시 쓰기.
  글꼴: KS X 1001 한글 2,350자 → SJIS 889F 부터 차례로(81~84 행 기호·전각 영숫자·가나는 원본 유지)
        2바이트 경로는 SJIS 첫 바이트 81~9F 만 닿으므로(0x06006AE4) 배정도 그 안(88~9F, 4,418칸)
        자형 = 갈무리14(BDF) — 칸 16×16 1bpp, 행 = u16 BE
  MES : 대사 조각마다 (번역 있으면 KO, 없으면 JP) 를 다시 인코딩
        파일 글자표 = 그 파일에서 많이 쓰는 128자 → 0x80+i, 나머지 = (SJIS 첫 바이트−0x20, 둘째)
        검사(빌드 실패): 매핑 없는 글자 · 텍스트 바이트 00/01(블록 건너뛰기 0x06008954 가 셈) · 파일 > 0x10000(0x060C0000 부터 다른 버퍼)
  python tools/krenc.py font <출력 KANJI.FON> [미리보기.png]"""
import os, re, sys, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesparse
from bdf import Font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BDF = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
MES_MAX = 0x10000


def cell(code):                       # SJIS → KANJI.FON 칸 번호
    hi, lo = code >> 8, code & 0xFF
    hi = hi - 0x81 if hi < 0xA0 else hi - 0xC1
    return hi * 188 + (lo - 0x40 - (1 if lo > 0x7F else 0))


def ks_hangul():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            out.append(bytes([hi, lo]).decode('euc-kr'))
    return out                         # 2,350


def reserved():
    """원본 그대로 두는 글(엔딩 스태프 롤 STAFF.MES — 스태프 롤 규칙)이 쓰는 한자 칸 → 한글 배정에서 비킴(2026-10-30, 324칸)"""
    p = os.path.join(ROOT, 'work', 'disc0', 'STAFF.MES')
    m = mesparse.Mes(open(p, 'rb').read()).parse()
    return {c for k, a, b in m.items if k == 'text' for c in codes(m, a, b)}


def sjis_slots():
    keep = reserved()
    for hi in range(0x88, 0xA0):
        for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            if hi == 0x88 and lo < 0x9F: continue      # 88 행 앞쪽은 빈 칸
            if (hi << 8) | lo in keep: continue        # 스태프 롤 한자 칸
            yield (hi << 8) | lo


# 한글식 문장부호(2026-10-30 하스피 지시) — 한글 다음 칸(9540~)에 갈무리14 자형, 반각 폭 그림을 칸 왼쪽에 붙여 그림.
# 원문 전각 、。？！・ 는 원본 칸 그대로(번역문에서 반각 , . ? ! 를 쓰면 이쪽). … 는 한 칸 = ・・・ 세 칸보다 바이트 절약.
# 값 = (가로, 세로 이동 px) — 쉼표 꼬리가 칸 아래(16행)로 나가 1px 올림 · 여는 괄호는 칸 오른쪽에 붙여 다음 글자와 붙게
PUNCT = {',': (0, -1), '.': (0, 0), '…': (0, 0), '?': (0, 0), '!': (0, 0), '~': (0, 0), ':': (0, 0), ';': (0, 0),
         "'": (0, 0), '"': (0, 0), '(': (10, 0), ')': (0, 0), '-': (0, 0), '·': (0, 0)}


def charmap():
    """글자 → SJIS 코드. 한글·한글식 부호는 고정 배정, 그 밖은 원본 SJIS(81~84 행만 허용 — 한자 칸은 한글이 덮음)"""
    m = {}
    slots = sjis_slots()
    for ch, code in zip(ks_hangul() + list(PUNCT), slots): m[ch] = code
    return m


# CMAP(글자 → 코드)는 모듈 끝에서 만든다 — reserved() 가 아래 codes() 를 씀

# 번역문 다듬기(2026-10-30 하스피 승인) — 번역문에만, 원문(JP) 열은 키라 손대지 않음
#  1) 마침표 셋 이상 «...»·가운뎃점 둘 이상 «・・・» → «…» 한 칸(화면 폭·바이트 절약)
#  2) 문장부호 바로 뒤 공백 1칸(반각·전각) 삭제 — 표준 목록 전부(메모리 feedback_no_space_after_punct), 2칸 이상은 채움이라 둠
#     ％(줄바꿈) 로 쪼갠 조각마다 적용
SQUEEZE_PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'
_SQ = re.compile('([' + re.escape(SQUEEZE_PUNCT) + '])[ 　](?![ 　])')


def squeeze(t):
    out = []
    for part in t.split('％'):
        part = re.sub(r'\.{3,}', '…', part)
        part = re.sub('・{2,}', '…', part)
        out.append(_SQ.sub(r'\1', part))
    return '％'.join(out)


def code_of(ch, poc=False):
    """poc=True: 한글 아닌 글자는 원본 SJIS 그대로(시험 빌드에서 안 옮긴 일본어 줄용 — 한자 칸은 한글로 덮여 깨져 보임)"""
    if ch in CMAP: return CMAP[ch]
    b = ch.encode('cp932')
    if poc and len(b) == 2: return (b[0] << 8) | b[1]
    if len(b) != 2 or not (0x81 <= b[0] <= 0x84):
        raise ValueError('매핑 없는 글자 %r (U+%04X)' % (ch, ord(ch)))
    return (b[0] << 8) | b[1]


def build_font(orig):
    f = bytearray(orig); fnt = Font(BDF)
    for ch, code in CMAP.items():
        pts, w = fnt.draw(ch, PUNCT.get(ch, (0, 0))[0], -3 + PUNCT.get(ch, (0, 0))[1])   # 갈무리14 잉크 y4~17·x1~14 → 칸 1~14행(원본 가나 1~15행)
        rows = [0] * 16
        for x, y in pts:
            if not (0 <= x < 16 and 0 <= y < 16): raise SystemExit('글리프가 칸 밖 %s (%d,%d)' % (ch, x, y))
            rows[y] |= 0x8000 >> x
        c = cell(code); f[c * 32:c * 32 + 32] = struct.pack('>16H', *rows)
    assert len(f) == len(orig)
    return bytes(f)


def encode_mes(data, ko=None, poc=False):
    """ko: {오프셋: 번역문}. 전 대사 조각을 다시 인코딩한 새 MES 바이트."""
    ko = ko or {}
    if not ko and not poc: return data                 # 번역 없는 파일(스태프 롤) = 원본 바이트 그대로(한자 칸은 reserved() 로 보존)
    m = mesparse.Mes(data).parse()
    texts = sorted((a, b) for k, a, b in m.items if k == 'text')
    strs = [(a, b, squeeze(ko[a]) if ko.get(a) else m.chars(a, b)) for a, b in texts]
    freq = collections.Counter()
    for _, _, t in strs:
        for ch in t: freq[code_of(ch, poc)] += 1
    table = [c for c, _ in freq.most_common(128)]
    idx = {c: 0x80 + i for i, c in enumerate(table)}
    out = bytearray(struct.pack('<H', 2 + 2 * len(table)) + b''.join(struct.pack('>H', c) for c in table))
    p = m.hdr
    for a, b, t in strs:
        out += data[p:a]; enc = bytearray()
        for ch in t:
            c = code_of(ch, poc)
            if c in idx: enc.append(idx[c])
            else:
                if not 0x81 <= c >> 8 <= 0x9F: raise ValueError('2바이트로 못 쓰는 코드 %04X (%r)' % (c, ch))
                enc += bytes([(c >> 8) - 0x20, c & 0xFF])
        if 0 in enc or 1 in enc: raise ValueError('텍스트에 00/01 바이트 @%X' % a)
        if not enc: raise ValueError('빈 대사 @%X' % a)
        out += enc; p = b
    out += data[p:]
    if len(out) > MES_MAX: raise ValueError('MES 크기 %X > %X' % (len(out), MES_MAX))
    # 다시 파싱해 구조 검산: 대사 조각 수·순서·내용이 의도와 같아야
    m2 = mesparse.Mes(bytes(out)).parse()
    got = [codes(m2, a, b) for k, a, b in sorted(m2.items, key=lambda x: x[1]) if k == 'text']
    want = [[code_of(ch, poc) for ch in t] for _, _, t in strs]
    if got != want: raise ValueError('재파싱 대사 불일치')
    if len(m2.unclosed) != len(m.unclosed): raise ValueError('블록 구조 바뀜')
    return bytes(out)


def codes(m, a, b):                    # 대사 조각 → 게임이 그릴 SJIS 코드 목록(0x06006A98 과 같은 규칙)
    o = []; i = a
    while i < b:
        x = m.d[i]
        if x >= 0x80: o.append(struct.unpack_from('>H', m.table, (x - 0x80) * 2)[0]); i += 1
        else: o.append(((x + 0x20) << 8) | m.d[i + 1]); i += 2
    return o


CMAP = charmap()
CMAP[' '] = 0x8140                      # 띄어쓰기 = 전각 공백(16px — 글자 간격 고정)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1] == 'font':
        orig = open(os.path.join(ROOT, 'work', 'disc0', 'KANJI.FON'), 'rb').read()
        nf = build_font(orig); open(sys.argv[2], 'wb').write(nf)
        print('글꼴', len(nf), '한글', len(CMAP), '마지막 칸', hex(list(CMAP.values())[-1]))
        if len(sys.argv) > 3:
            from PIL import Image
            im = Image.new('L', (16 * 50, 16 * 47), 0)
            for i, (ch, code) in enumerate(CMAP.items()):
                c = cell(code); rows = struct.unpack('>16H', nf[c * 32:c * 32 + 32])
                for y, r in enumerate(rows):
                    for x in range(16):
                        if r & (0x8000 >> x): im.putpixel((i % 50 * 16 + x, i // 50 * 16 + y), 255)
            im.resize((im.width * 2, im.height * 2)).save(sys.argv[3])
