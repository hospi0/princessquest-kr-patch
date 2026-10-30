# -*- coding: utf-8 -*-
"""MES 대사 추출(2026-10-30) — tools/mesparse.py(해석기 역분석 파서)로 문장 단계 대사 조각만 뽑는다.
  work/text/script.tsv : 번호 · 파일 · 오프셋 · 원본바이트(hex) · JP · KO   (출현마다 한 줄 — 재삽입 기준)
  work/text/uniq.tsv   : JP · 출현수 · 첫 위치 · KO                       (번역 작업용, 같은 원문 한 번)
  my files/tsv/pq_NNN.tsv : 번호 · 위치 · JP · KO — uniq 를 UTF-8 18KB(18×1024, 머리줄 포함) 넘기 전 끊음(사용자 지시 2026-10-30)
  ％ = 줄바꿈(0x8193). 원문 토큰이므로 번역에도 그대로 둔다.
  끝에 라운드트립 검산: script.tsv 의 원본바이트로 전 파일을 다시 조립해 원본과 바이트 동일한지.
  python tools/extract.py"""
import os, sys, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = 18 * 1024


def write_split(folder, stem, head, lines):
    os.makedirs(folder, exist_ok=True)
    chunks = []; cur = []; size = len(head.encode('utf-8'))
    for ln in lines:
        n = len(ln.encode('utf-8'))
        if cur and size + n > SPLIT: chunks.append(cur); cur = []; size = len(head.encode('utf-8'))
        cur.append(ln); size += n
    if cur: chunks.append(cur)
    for i, c in enumerate(chunks, 1):
        with open(os.path.join(folder, '%s_%03d.tsv' % (stem, i)), 'w', encoding='utf-8', newline='\n') as w:
            w.write(head + ''.join(c))
    return len(chunks)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = os.path.join(ROOT, 'work', 'text'); os.makedirs(out, exist_ok=True)
    rows = []; uniq = collections.OrderedDict(); bad = 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc0', '*.MES'))):
        nm = os.path.basename(f); m = mesparse.load(f)
        texts = sorted((a, b) for k, a, b in m.items if k == 'text')
        rebuilt = bytearray(m.d[:m.hdr]); p = m.hdr
        for a, b in texts:
            jp = m.chars(a, b)
            if '\t' in jp or '\n' in jp: raise SystemExit('탭·줄바꿈 든 원문 %s %X' % (nm, a))
            rows.append((nm, a, m.d[a:b].hex(), jp))
            u = uniq.setdefault(jp, [0, '%s:%05X' % (nm, a)]); u[0] += 1
            rebuilt += m.d[p:a] + bytes.fromhex(rows[-1][2]); p = b
        rebuilt += m.d[p:]
        if bytes(rebuilt) != m.d: bad += 1; print('라운드트립 불일치', nm)
    with open(os.path.join(out, 'script.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('번호\t파일\t오프셋\t원본바이트\tJP\tKO\n')
        for i, (nm, a, hx, jp) in enumerate(rows, 1):
            w.write('%05d\t%s\t%05X\t%s\t%s\t\n' % (i, nm, a, hx, jp))
    with open(os.path.join(out, 'uniq.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('JP\t출현수\t첫위치\tKO\n')
        for jp, (n, at) in uniq.items():
            w.write('%s\t%d\t%s\t\n' % (jp, n, at))
    lines = ['%05d\t%s\t%s\t\n' % (i, at, jp) for i, (jp, (n, at)) in enumerate(uniq.items(), 1)]
    nf = write_split(os.path.join(ROOT, 'my files', 'tsv'), 'pq', '번호\t위치\tJP\tKO\n', lines)
    print('my files/tsv 분할', nf, '개')
    print('출현', len(rows), '고유', len(uniq), '고유 글자', sum(len(t) for t in uniq),
          '라운드트립 불일치 파일', bad)


if __name__ == '__main__':
    main()
