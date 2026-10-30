# -*- coding: utf-8 -*-
"""MES 시험 해독(2026-10-30 조사용) — 머리 = u16LE 길이 + 그 파일 상용 글자표(SJIS), 본문 바이트:
  0x80~0xFF → 표[b-0x80] / 0x40~0x7F → 2바이트(첫 바이트+0x20 = SJIS 첫 바이트) / 그 밖 = <XX>(명령·인수)
  python tools/mesdec.py <MES> [시작16진 끝16진]"""
import struct, sys


def load(p):
    d = open(p, 'rb').read(); n = struct.unpack('<H', d[:2])[0]
    return d, d[2:2 + n].decode('cp932'), 2 + n


def dec(d, t, a, b):
    o = []; i = a
    while i < b:
        x = d[i]
        if x >= 0x80: o.append(t[x - 0x80] if x - 0x80 < len(t) else '<T%02X>' % x); i += 1
        elif 0x40 <= x < 0x80 and i + 1 < b:
            try: o.append(bytes([x + 0x20, d[i + 1]]).decode('cp932'))
            except UnicodeDecodeError: o.append('<%02X%02X>' % (x, d[i + 1]))
            i += 2
        else: o.append('<%02X>' % x); i += 1
    return ''.join(o)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    d, t, h = load(sys.argv[1])
    a = int(sys.argv[2], 16) if len(sys.argv) > 2 else h
    b = int(sys.argv[3], 16) if len(sys.argv) > 3 else len(d)
    print(dec(d, t, a, b))
