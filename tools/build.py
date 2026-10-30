# -*- coding: utf-8 -*-
r"""전체 입력 만들기(2026-10-30) → work/build/ (KANJI.FON · MES · [--small] MWAKU.B8·A.BIN) — 디스크 쓰기는 tools/discbuild.py(허락 후)
  대사: work/text/uniq.tsv KO 를 파일별 조각에 넣어 krenc.encode_mes (STAFF.MES = 원본 바이트, 스태프 롤 규칙)
  검사(빌드 실패): 번역 빈 조각 · 표 행이 어느 조각에도 안 쓰임 · 매핑 없는 글자 · 00/01 · 64KB · 재파싱 불일치
  작은 글꼴(tools/smallfont.py, 갈무리7 하스피 확정): MWAKU.B8 칸 + RESET·SENTO 이름 리터럴(길이 그대로) + 55개 MES 칸 등록 상한(100→161)
  그림(하스피 시안 통과): MWAKU 메뉴 그림(tools/menu_kr.py) · BINDPIC.DAT 안 TITLE·STATUS·SAVE·SAVELOAD·SAVE01H(제자리, 크기 불변)
    A.BIN 0x06006942~46: 표에 없는 바이트 b → 슬롯 300+b (mov #0,r5 / extu.b → extu.b / mov r2,r5)
  python tools/build.py"""
import os, sys, csv, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import krenc, mesparse, struct

DISC = os.path.join(ROOT, 'work', 'disc0')
OUT = os.path.join(ROOT, 'work', 'build')
SKIP = {'STAFF.MES'}                                   # 스태프 롤 원본
# 칸 등록 반복문: if I < 100 { 1A(11, 300+I, ...) }
LOOP_OLD = bytes.fromhex('0f4908079328030104' '1a3b03020813b34920')
LOOP_NEW = bytes.fromhex('0f49080b8728030104' '1a3b03020813b34920')   # 161 = (0x0B>>2)<<6 | 0x87>>2
A_OFF = 0x06006942 - 0x06004000
A_OLD = bytes.fromhex('E500E800621C')
A_NEW = bytes.fromhex('621CE8006523')


def load_ko():
    r = list(csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'uniq.tsv'), encoding='utf-8'), delimiter='\t'))
    return {x['JP']: x['KO'] for x in r}


def small_parts():
    import smallfont, menu_kr
    orig = open(os.path.join(DISC, 'MWAKU.B8'), 'rb').read()
    img, m = smallfont.build_mwaku(orig)
    pal0 = open(os.path.join(DISC, 'MWAKU.PAL'), 'rb').read()
    pal = [menu_kr.rgb(struct.unpack_from('>H', pal0, i * 2)[0]) for i in range(256)]
    img = menu_kr.mwaku(img, pal)[0]
    return img, {b: smallfont.literal(b, ko, m) for b, ko in smallfont.names().items()}


def merge16(orig, new):
    """바뀐 화소만 — 안 바뀐 낱말은 원본 그대로, 새 화소 윗비트는 그 그림의 다수 규칙, 검정은 0"""
    o = struct.unpack('>%dH' % (len(orig) // 2), orig); n = struct.unpack('>%dH' % (len(orig) // 2), new)
    msb = sum(1 for x in o if x & 0x8000) * 2 > sum(1 for x in o if x)
    out = [a if (a & 0x7FFF) == (b & 0x7FFF) else (0 if not b & 0x7FFF else (b & 0x7FFF) | (0x8000 if msb else 0)) for a, b in zip(o, n)]
    return struct.pack('>%dH' % len(out), *out), msb


def bindpic():
    import disc, menu_kr, title_kr
    fs = {p: (l, s) for p, l, s in disc.files(disc.bin_path(0))}
    l, s = fs['/BINDPIC.DAT']
    dat = bytearray(disc.sec(open(disc.bin_path(0), 'rb'), l, (s + 2047) // 2048)[:s])
    t = open(os.path.join(DISC, 'BINDPIC.TBL'), 'rb').read()
    ents = {t[i:i + 11].decode('latin1').replace(' ', ''): struct.unpack_from('>II', t, i + 11) for i in range(0, len(t) - 18, 19)}
    new = {}
    ti = title_kr.bindpic('TITLEB16'); im, _ = title_kr.edit(title_kr.to_rgb(ti))
    new['TITLEB16'] = struct.pack('>%dH' % (320 * 224), *[menu_kr.enc(*c) if c != (0, 0, 0) else 0 for c in im.getdata()])
    _, _, _, n = menu_kr.build(); new.update(n)
    new['SAVE01HB16'] = menu_kr.save01h(menu_kr.raw('SAVE01HB16'))
    for k, b in new.items():
        o, z = ents[k]
        if len(b) != z: raise SystemExit('그림 크기 ' + k)
        nb, msb = merge16(bytes(dat[o:o + z]), b)
        ch = sum(1 for i in range(0, z, 2) if dat[o + i:o + i + 2] != nb[i:i + 2])
        print('  %-12s 바뀐 화소 %6d 윗비트 %d' % (k, ch, msb))
        dat[o:o + z] = nb
    return bytes(dat)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    small = True
    os.makedirs(OUT, exist_ok=True)
    ko = load_ko(); used = set(); empty = []; sizes = []
    font = krenc.build_font(open(os.path.join(DISC, 'KANJI.FON'), 'rb').read())
    open(os.path.join(OUT, 'KANJI.FON'), 'wb').write(font)
    lits = None
    if small:
        img, lits = small_parts()
        open(os.path.join(OUT, 'MWAKU.B8'), 'wb').write(img)
        a = bytearray(open(os.path.join(DISC, 'A.BIN'), 'rb').read())
        if a[A_OFF:A_OFF + 6] != A_OLD: raise SystemExit('A.BIN 자리 다름')
        a[A_OFF:A_OFF + 6] = A_NEW
        open(os.path.join(OUT, 'A.BIN'), 'wb').write(a)
        open(os.path.join(OUT, 'BINDPIC.DAT'), 'wb').write(bindpic())
    nl = nb = 0
    for f in sorted(glob.glob(os.path.join(DISC, '*.MES'))):
        nm = os.path.basename(f); d = open(f, 'rb').read()
        p = os.path.join(OUT, nm)
        if nm in SKIP:
            if os.path.exists(p): os.remove(p)
            continue
        m = mesparse.Mes(d).parse(); kod = {}
        for k, a, b in m.items:
            if k != 'text': continue
            jp = m.chars(a, b); t = ko.get(jp)
            if t is None: raise SystemExit('표에 없는 원문 %s %X %s' % (nm, a, jp))
            if t: kod[a] = t; used.add(jp)
            else: empty.append((nm, a, jp))
        nd = krenc.encode_mes(d, kod)
        if small:
            if lits and nm in ('RESET.MES', 'SENTO.MES'):
                for b, new in lits.items():
                    o, n = b'\x06' + b + b'\x06', b'\x06' + new + b'\x06'
                    if nd.count(o): nl += nd.count(o); nd = nd.replace(o, n)
            c = nd.count(LOOP_OLD)
            if c != d.count(LOOP_OLD) or c == 0: raise SystemExit('등록 반복문 %s %d' % (nm, c))
            nb += c; nd = nd.replace(LOOP_OLD, LOOP_NEW)
            mesparse.Mes(nd).parse()
        open(p, 'wb').write(nd); sizes.append((len(nd), nm))
    unused = [j for j, t in ko.items() if t and j not in used]
    print('MES', len(sizes), '최대', hex(max(sizes)[0]), max(sizes)[1], '· 빈 조각', len(empty), '· 안 쓰인 표 행', len(unused))
    for x in empty[:20]: print('  빈', x)
    for x in unused[:20]: print('  미사용', x)
    if empty or unused: raise SystemExit('⛔ 번역 누락')
    if small: print('작은 글꼴: 리터럴', nl, '· 등록 반복문', nb)
    print('완료 →', OUT)


if __name__ == '__main__':
    main()
