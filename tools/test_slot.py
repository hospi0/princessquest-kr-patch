# -*- coding: utf-8 -*-
"""작은 글꼴 슬롯 검산(2026-10-30, 전투 슬롯 400~446 충돌 수정) — work/build/A.BIN 이름 바이트 → 슬롯 함수(0x06006940~0x060069A4) 흉내
  표 안 글자 = 300+번호(원본과 같음) · 표 밖 0xE0~0xFF·0x89~0xA5 = b+428(565~683, 덧붙인 등록 반복문과 일치) · 원본 A.BIN 은 표 안 글자에서 같은 값
  + MES 두 번째 반복문 바이트 확인
  python tools/test_slot.py"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sh2sim as S, smallfont as SF


def slot(a, b):
    m = S.Mem(); m.add(0x06000000, 0x100000)
    for i in range(0, len(a) - 3, 4): m.w32(0x06004000 + i, struct.unpack_from('>I', a, i)[0])
    m.w8(0x060F0000, b); m.w8(0x060F0001, 0)
    r = [0] * 16; r[4] = 0x060F0000; r[12] = 0x06037244
    return S.run(m, 0x06006940, regs=r, stop=0x060069A4)[0][5]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    a0 = open(os.path.join(ROOT, 'work', 'disc0', 'A.BIN'), 'rb').read()
    a1 = open(os.path.join(ROOT, 'work', 'build', 'A.BIN'), 'rb').read()
    ok = True
    for b in SF.TBL:
        if b in (0x20,) and SF.TBL.index(b) != 0: continue
        s0, s1 = slot(a0, b), slot(a1, b)
        if not (s0 == s1 == 300 + SF.TBL.index(b)): print('✗ 표 안', hex(b), s0, s1); ok = False
    ext = SF.EXTRA_B; ss = []
    for b in ext:
        s1 = slot(a1, b); I = SF.cell_of(b); ss.append(s1)
        reg = I + 552 if I < 132 else I + 433                                  # MES 반복문 등록 슬롯
        if s1 != b + 428 or s1 != reg or not 461 <= s1 < 1800: print('✗ 표 밖', hex(b), s1, I, reg); ok = False
    if len(set(ss)) != len(ss) or sorted(SF.cell_of(b) for b in ext) != list(range(100, 161)): print('✗ 겹침'); ok = False
    print('① 표 안 %d자 = 300+번호(원본과 같음) · 표 밖 %d자 = b+428 (%d~%d) = 등록 슬롯' % (len(SF.TBL), len(ext), min(ss), max(ss)), ok)
    d = open(os.path.join(ROOT, 'work', 'build', 'PRO01.MES'), 'rb').read()
    c2 = all(d.count(bytes.fromhex(h)) == 1 for h in ('04100f4908079328030104', '04100f49080b1328030104', '04100f49080b8728030104', '0823a34920', '081bc74920'))
    print('② PRO01 반복문 셋(I<100 300+I · I<132 552+I · I<161 433+I)', c2); ok &= c2
    print('★전체', '통과' if ok else '실패'); return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
