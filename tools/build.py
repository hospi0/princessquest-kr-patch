# -*- coding: utf-8 -*-
r"""전체 입력 만들기(2026-10-30) → work/build/ (KANJI.FON · MES · [--small] MWAKU.B8·A.BIN) — 디스크 쓰기는 tools/discbuild.py(허락 후)
  대사: work/text/uniq.tsv KO 를 파일별 조각에 넣어 krenc.encode_mes (STAFF.MES = 원본 바이트, 스태프 롤 규칙)
  검사(빌드 실패): 번역 빈 조각 · 표 행이 어느 조각에도 안 쓰임 · 매핑 없는 글자 · 00/01 · 64KB · 재파싱 불일치
  작은 글꼴(tools/smallfont.py, 갈무리7 하스피 확정): MWAKU.B8 칸 + RESET·SENTO 이름 리터럴(길이 그대로) + 55개 MES 칸 등록
    ⚠️2026-10-30 실기: 전투가 텍스처 슬롯 400~446 을 적·효과로 다시 등록 → 칸 100~160 을 슬롯 400~460 에 두면 이름 글자가 적 그림으로 바뀜(하스피 버그 스샷)
    → 원래 반복문(I<100 → 슬롯 300+I) 그대로 + 뒤에 반복문 둘(I<132 → 슬롯 I+552 = 652~683 · I<161 → 슬롯 I+433 = 565~593)
      (표 1800칸 · 스테이트 15장 어디서도 461 이상 안 씀 · 전투 최대 446 에서 119 이상 떨어짐)
  그림(하스피 시안 통과): MWAKU 메뉴 그림(tools/menu_kr.py) · BINDPIC.DAT 안 TITLE·STATUS·SAVE·SAVELOAD·SAVE01H(제자리, 크기 불변)
    A.BIN(이름 바이트 → 슬롯, 0x06006936~): 표 안 글자 = 300+번호(그대로) · 표에 없는 바이트 b(0xE0~0xFF·0x89~0xA5) = b+428
      0x06006942 `E500 E800 621C` → `621C E800 6523`(r5 = b) · 0x06006956 nop → add #-128,r5(찾은 경우)
      · 0x06006AD8 상수 300 → 428 (찾음: 번호−128+428 = 300+번호 / 못 찾음: b+428) — 명령 자리가 이것뿐이라 b+428 ≤ 683 이 한계
  python tools/build.py"""
import os, re, sys, csv, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import krenc, mesparse, struct

DISC = os.path.join(ROOT, 'work', 'disc0')
OUT = os.path.join(ROOT, 'work', 'build')
SKIP = {'STAFF.MES'}                                   # 스태프 롤 원본
# 칸 등록 반복문: if I < 100 { 1A(11, 300+I, ...) }
LOOP_OLD = bytes.fromhex('0f4908079328030104' '1a3b03020813b34920')
LOOP_TAIL = bytes.fromhex('0c4949312003' '00')                         # I = I + 1, 블록 끝
# ⚠앞 04 10 = 반복 시작(없으면 0f 가 한 번만 돎 — 2026-10-30 실기에서 슬롯 652 하나만 등록돼 글자 깨짐)
LOOPS = [(bytes.fromhex('0410' '0f4908' '0b13' '28030104'), bytes.fromhex('08' '23a3' '4920')),     # while I < 132: 슬롯 552 + I
         (bytes.fromhex('0410' '0f4908' '0b87' '28030104'), bytes.fromhex('08' '1bc7' '4920'))]     # while I < 161: 슬롯 433 + I
SLOT_OLD = bytes.fromhex('0813b34920')                                  # 300 I +
A_PATCH = [(0x06006942, 'E500E800621C', '621CE8006523'), (0x06006956, '0009', '7580'), (0x06006AD8, '012C', '01AC')]


def loop2(nd):
    """원래 칸 등록 반복문(I<100) 뒤에 반복문 둘(I<132 슬롯 I+552 · I<161 슬롯 I+433) 붙이기"""
    out = bytearray(); p = 0; n = 0
    while True:
        i = nd.find(LOOP_OLD, p)
        if i < 0: break
        e = nd.find(LOOP_TAIL, i) + len(LOOP_TAIL)
        body = nd[i + 9:e]                                                  # 04 1a … 0c 49 49 31 20 03 00
        if body.count(SLOT_OLD) != 1: raise SystemExit('등록 반복문 몸통 다름')
        out += nd[p:e] + b''.join(h + body.replace(SLOT_OLD, s) for h, s in LOOPS); p = e; n += 1
    return bytes(out + nd[p:]), n


def load_ko():
    r = list(csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'uniq.tsv'), encoding='utf-8'), delimiter='\t'))
    ko = {x['JP']: x['KO'] for x in r}
    # 쪽 나눔 뒤 남는 쪽이 짧은(≤6자) 대사는 한 쪽에 들어가게 줄인 번역(2026-10-30 하스피 «4~6자짜리는 번역을 줄여») — merge_ko 재실행에도 살아남게 따로
    for x in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'ko_short.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
        if x['JP'] not in ko: raise SystemExit('ko_short 원문 없음 ' + x['JP'])
        if len(krenc.paginate(krenc.squeeze(x['KO']))) > 1: raise SystemExit('ko_short 한 쪽 넘침 ' + x['KO'])
        ko[x['JP']] = x['KO']
    bad = [k for k in ko.values() if re.search(r'[っッ]|은\(는\)', k)]                # 2026-10-30 하스피 버그 — 다시 들어오면 중단
    if bad: raise SystemExit('번역에 촉음 っッ·«은(는)» 남음 %d %s' % (len(bad), bad[:3]))
    return ko


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
        for ad, old, new in A_PATCH:
            o = ad - 0x06004000; old, new = bytes.fromhex(old), bytes.fromhex(new)
            if a[o:o + len(old)] != old: raise SystemExit('A.BIN 자리 다름 %X' % ad)
            a[o:o + len(new)] = new
        open(os.path.join(OUT, 'A.BIN'), 'wb').write(a)
        open(os.path.join(OUT, 'BINDPIC.DAT'), 'wb').write(bindpic())
        import disc, sentowak_kr                                       # 전투 메뉴 그림(BINDFACE 안 SENTOWAK.B8, 제자리)
        bf = bytearray(disc.read('BINDFACE.DAT', disc.bin_path(0)))
        o = sentowak_kr.OFF
        if bytes(bf[o:o + sentowak_kr.SIZE]) != open(os.path.join(DISC, 'SENTOWAK.B8'), 'rb').read(): raise SystemExit('SENTOWAK 자리 다름')
        bf[o:o + sentowak_kr.SIZE] = sentowak_kr.build(bytes(bf[o:o + sentowak_kr.SIZE]))[0]
        open(os.path.join(OUT, 'BINDFACE.DAT'), 'wb').write(bf)
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
        nd = krenc.encode_mes(d, kod, pages=nm != 'START.MES')    # 저장 경고 화면은 자동 줄 접기 — 쪽 나눔 안 함
        if small:
            if lits and nm in ('RESET.MES', 'SENTO.MES'):
                for b, new in lits.items():
                    o, n = b'\x06' + b + b'\x06', b'\x06' + new + b'\x06'
                    if nd.count(o): nl += nd.count(o); nd = nd.replace(o, n)
            nd, c = loop2(nd)
            if c != d.count(LOOP_OLD) or c == 0: raise SystemExit('등록 반복문 %s %d' % (nm, c))
            nb += c
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
