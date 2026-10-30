# -*- coding: utf-8 -*-
"""대사 PoC 입력 만들기(2026-10-30) → work/build/KANJI.FON · work/build/PRO01.MES (그다음 tools/discbuild.py)
  확인 화면: 스테이트 «이름있는 대사»(PRO01, 성문 앞 윌로 대사) — 원문 「ウィロー％「はぁ～、ここか・・・・・」」
  안 옮긴 일본어 줄은 poc 모드(원본 SJIS 유지) — 한자 칸은 한글로 덮여 깨져 보이는 게 정상
  python tools/poc.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krenc, mesparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KO = {('PRO01.MES', 0x068EB): '윌로％「하아～、여기인가・・・・・」'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = os.path.join(ROOT, 'work', 'build'); os.makedirs(out, exist_ok=True)
    orig = open(os.path.join(ROOT, 'work', 'disc0', 'KANJI.FON'), 'rb').read()
    open(os.path.join(out, 'KANJI.FON'), 'wb').write(krenc.build_font(orig))
    for nm in sorted({f for f, _ in KO}):
        d = open(os.path.join(ROOT, 'work', 'disc0', nm), 'rb').read()
        m = mesparse.Mes(d).parse()
        starts = {a for k, a, b in m.items if k == 'text'}
        ko = {a: t for (f, a), t in KO.items() if f == nm}
        for a in ko: assert a in starts, '대사 시작 아님 %s %X' % (nm, a)
        nd = krenc.encode_mes(d, ko, poc=True)
        open(os.path.join(out, nm), 'wb').write(nd)
        print(nm, len(d), '→', len(nd), 'B (한도 0x10000)')
    print('완료 →', out)


if __name__ == '__main__':
    main()
