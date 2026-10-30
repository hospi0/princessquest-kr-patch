# -*- coding: utf-8 -*-
"""MES 스크립트 파서(2026-10-30, A.BIN 해석기 역분석 기준) — 문장 단위로 끝까지 읽고 대사 조각을 뽑는다.
  근거(램 주소 = A.BIN+0x06004000):
    문장 분기 0x06004574: b<=6 → 표 0x060046D0, b>0x60 → 글자, 0x0A~0x1A → 표 0x06006B84
    글자 0x06006A98: b>=0x80 → 파일 글자표 u16, 0x61~0x7F → (b+0x20)<<8|다음바이트 (SJIS)
    식 0x06008C8C: RPN, 30~3F·07 x·08 xx·09 xxx·40~5A 변수·20~2F 연산자(2D·2F 는 수 토큰 하나 더), 03 에서 끝
    인수 0x06008998: 06 문자열 06 | 01 블록(0x06008954 순진한 01/00 깊이 세기) | 식, 02 로 이음(최대 20)
  python tools/mesparse.py            → 전 파일 파싱 검산
  python tools/mesparse.py <MES>      → 문장 덤프"""
import os, struct, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ParseError(Exception): pass


class Mes:
    def __init__(s, data):
        s.d = data; n = struct.unpack('<H', data[:2])[0]
        s.hdr = n; s.table = data[2:n]          # n = 길이 칸 2바이트 포함
        s.items = []          # (종류, 시작, 끝) — 'text' 는 대사 조각
        s.pairs = {}          # 블록 01 위치 → 짝 00 위치(파서 기준)
        s.unclosed = []       # 파일 끝까지 안 닫힌 블록

    def chars(s, a, b):
        o = []; i = a; d = s.d
        while i < b:
            x = d[i]
            if x >= 0x80:
                k = (x - 0x80) * 2
                o.append(s.table[k:k + 2].decode('cp932')); i += 1
            else:
                o.append(bytes([x + 0x20, d[i + 1]]).decode('cp932')); i += 2
        return ''.join(o)

    # ---- 식 ----
    def num(s, i):
        x = s.d[i]
        if 0x30 <= x <= 0x3F: return i + 1
        if x == 7: return i + 2
        if x == 8: return i + 3
        if x == 9: return i + 4
        return i + 1          # 0x06008FAC: 그 밖은 1바이트 먹고 0

    def expr(s, i):
        d = s.d
        if d[i] == 3: return i + 1
        while True:
            x = d[i]
            if 0x30 <= x <= 0x3F: i += 1
            elif x == 7: i += 2
            elif x == 8: i += 3
            elif x == 9: i += 4
            elif 0x40 <= x <= 0x5A: i += 1
            elif 0x20 <= x <= 0x2F:
                i += 1
                if x in (0x2D, 0x2F): i = s.num(i)
            else: raise ParseError('식 안 낯선 바이트 %02X @%X' % (x, i))
            if d[i] == 3: return i + 1

    def skipblock(s, i):        # 게임과 똑같이 순진하게
        d = s.d
        while d[i] != 1: i += 1
        st = i; i += 1; depth = 1
        while depth:
            if i >= len(d): s.unclosed.append(st); return st, i     # FIN01: 블록 안에서 다음 MES 로 넘어가 닫는 00 이 없음(원본 그대로)
            if d[i] == 1: depth += 1
            elif d[i] == 0: depth -= 1
            i += 1
        return st, i

    def args(s, i, choice=False):
        d = s.d; n = 0
        while True:
            x = d[i]
            if x == 6:
                j = d.index(6, i + 1); s.items.append(('str', i, j + 1)); i = j + 1
            elif x == 1:
                st = i; i = s.block(i, choice)
            elif x in (7, 8, 9) or 0x20 <= x <= 0x5A:
                i = s.expr(i)
            else:
                return i            # 인수 없음
            n += 1
            if d[i] == 2 and n < 20: i += 1; continue
            return i

    # ---- 블록: 01 문장들 00 ----
    def block(s, i, choice=False):
        if s.d[i] != 1: raise ParseError('블록 01 아님 %02X @%X' % (s.d[i], i))
        st, en = s.skipblock(i)
        j = s.stmts(i + 1, choice=choice)
        if j != en: raise ParseError('블록 짝 불일치 @%X 파서 %X 게임 %X' % (i, j, en))
        s.pairs[st] = en - 1
        return en

    def stmts(s, i, top=False, choice=False):
        d = s.d
        while i < len(d):
            x = d[i]
            if x == 0:
                if top: i += 1; continue
                return i + 1
            if x in (1,):
                i = s.block(i); continue
            if x in (2, 3, 5):
                i += 1; continue
            if x == 4:
                s.items.append(('call', i, i + 2)); i = s.args(i + 2, choice=d[i + 1] == 0x13); continue   # 04 13 = 선택지
            if x == 6:
                j = d.index(6, i + 2); s.items.append(('str6', i, j + 1)); i = j + 1; continue
            if x > 0x60:
                a = i
                while i < len(d) and d[i] > 0x60:
                    i += 1 if d[i] >= 0x80 else 2
                s.items.append(('text', a, i)); continue
            if x == 0x0A:
                i = s.num(i + 1)
                while True:
                    i = s.expr(i)
                    if d[i] == 2: i += 1; continue
                    break
                continue
            if x == 0x0B:
                i = s.expr(i + 1)
                while True:
                    i = s.expr(i)
                    if d[i] == 2: i += 1; continue
                    break
                continue
            if x in (0x0C, 0x0D):
                i += 2
                if x == 0x0D: i = s.expr(i)     # 0x06006C4C: 변수 · 첨자 식 · 값 식(02 로 이어 씀)
                while True:
                    i = s.expr(i)
                    if d[i] == 2: i += 1; continue
                    break
                continue
            if x == 0x0E:
                i = s.expr(i + 1); continue
            if x == 0x0F and choice:          # 0x06008ABC: 선택지 항목 앞 조건식
                i = s.expr(i + 1); continue
            if x == 0x0F:
                i = s.expr(i + 1); i = s.block(i)
                while i < len(d) and d[i] == 2:
                    i += 1
                    if d[i] == 0x0F: i = s.expr(i + 1); i = s.block(i)
                    else: i = s.block(i); break
                continue
            if 0x10 <= x <= 0x1A:
                i = s.args(i + 1); continue
            raise ParseError('문장 낯선 바이트 %02X @%X' % (x, i))
        return i

    def parse(s):
        end = s.stmts(s.hdr, top=True)
        if end != len(s.d): raise ParseError('끝 %X != 길이 %X' % (end, len(s.d)))
        return s


def load(p): return Mes(open(p, 'rb').read()).parse()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) > 1:
        m = load(sys.argv[1])
        for k, a, b in m.items:
            if k == 'text': print('%05X %s' % (a, m.chars(a, b)))
        sys.exit()
    ok = 0; tot = 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc0', '*.MES'))):
        try:
            m = load(f); t = [x for x in m.items if x[0] == 'text']
            tot += sum(len(m.chars(a, b)) for _, a, b in t); ok += 1
            print('OK  ', os.path.basename(f), '대사 조각', len(t))
        except (ParseError, IndexError, UnicodeDecodeError, ValueError) as e:
            print('FAIL', os.path.basename(f), e)
    print('통과', ok, '글자', tot)
