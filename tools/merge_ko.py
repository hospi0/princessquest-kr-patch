# -*- coding: utf-8 -*-
r"""번역 병합(2026-10-30) — my files/프퀘/*.tsv(하스피 번역, 읽기만) → work/text/uniq.tsv KO 열 + work/text/merge_report.tsv
  검사·정리(하스피 승인 2026-10-30):
   - 원문 대조: 번호 4,549 전부·원문 JP 그대로인지
   - 이름 통일: ウィロー=윌로 · ジェラード=제라드 · チェロス=체로스 · マロン=마롱 · シェリー=셰리 · シャルロット=샤를로트 · 宮廷士=궁정사
     女の子(화자)=여자애 · 女魔導士=여마도사 · シスター=시스터 — 받침이 바뀌면 뒤 조사도 고침
   - ウィロー殿 = 윌로 님(«공» → «님», 그 원문 줄에서만)
   - 화자 기호: 병사A·병사 A → 병사Ａ(원문처럼 붙여 쓰고 전각) · 본문 반각 영숫자 → 전각(글꼴 칸이 전각만)
   - 토큰: ％·「」『』 개수 원문과 같게(TOKEN_FIX 손질 목록) — 어긋나면 중단
   - 18칸(원문 그 조각 최장 줄이 더 길면 그 길이) 넘는 줄 → 낱말 경계에서 다음 줄로(조각 4줄 안), 못 넣으면 보고
   - STAFF.MES(엔딩 스태프 롤) = 원본 유지(KO 비움 — 스태프 롤 규칙) · START.MES(저장 경고) 는 자동 줄 접기라 줄 나눔 안 함 · 자모 ㅡ → ―
  python tools/merge_ko.py"""
import os, sys, csv, glob, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import krenc

WIDTH, MAXLINES = 18, 4
NAMES = [('윌로우', '윌로'), ('젤라드', '제라드'), ('첼로스', '체로스'), ('츄로스', '체로스'), ('추로스', '체로스'),
         ('마론', '마롱'), ('쉐리', '셰리'), ('샬롯', '샤를로트'), ('궁정관', '궁정사'), ('궁정 관리', '궁정사'), ('여자 마도사', '여마도사')]
SPEAKER = {'女の子': '여자애', 'シスター': '시스터'}
# 지명·아이템(2026-10-30 하스피 «ㄱㄱ») — 그 원문 낱말이 든 줄에서만(ブロードソード 는 다른 아이템이라 제외)
COND = [('ディルマ', '딜마', '디르마'), ('ラリアン', '랄리안', '라리안'), ('ギムリア', '김리아', '기무리아'), ('ロードソード', '브로드소드', '로드소드')]
# 손질 목록(토큰 어긋남) — 번호: 고친 KO
TOKEN_FIX = {
    909: '밤에 돌아다니는 걸 봤다는 얘기도 있어요~％왠지 실망이에요~」',
    3514: '커스터드％「윌~짱~,％놀~자~!!」',
    3515: '윌％「어, 커스터드,％무슨 일이야?」',
    3863: '몸도 꽤％편해졌으니,％직접 받으러 가겠습니다」',
    4063: '아무리 여자라도,％더는 봐줄 필요％없어요.',
    1247: '체로스％「여자였다니…',
    3749: '…또 어디선가％낮잠이라도 주무시겠지.％늘 그러시거든.',
    3861: '마들렌％「제가 받으러 갈 테니％윌로 님은 여기서 쉬고 계세요',
    1553: '……응?……％『나』라니이이!!」',
    1558: '남자일 때의 당신의 여동생％『윌』로서％모두에게 소개해 두겠어요」',
    2658: '마스터％「『술은 백약의 으뜸』이라고,％적당히 마시면 몸에 아주 좋아.',
    4522: '카트리지 ＲＡＭ에 새％기록을 저장할 빈 용량이％없습니다.％　　％새 기록을 저장하려면,％',
}
HAN0 = 0xAC00


def has_batchim(ch):
    return '가' <= ch <= '힣' and (ord(ch) - HAN0) % 28 != 0


JOSA = [('이', '가'), ('은', '는'), ('을', '를'), ('과', '와'), ('으로', '로'), ('이야', '야'), ('이에요', '예요'), ('이여', '여'), ('아', '야')]


def rename(text, old, new):
    """old → new, 받침 유무가 바뀌면 바로 뒤 조사도 고침"""
    ob, nb = has_batchim(old[-1]), has_batchim(new[-1])
    if ob == nb: return text.replace(old, new)
    pairs = [(a, b) if ob else (b, a) for a, b in JOSA]          # (old 쪽 조사, new 쪽 조사)
    pairs.sort(key=lambda p: -len(p[0]))
    def sub(m):
        rest = m.group(1)
        for a, b in pairs:
            if rest.startswith(a) and not ('가' <= rest[len(a):len(a) + 1] <= '힣' and a in ('이', '아')):
                return new + b + rest[len(a):]
        return new + rest
    return re.sub(re.escape(old) + r'((?:[가-힣]{0,3})?)', sub, text)


def zen(s):
    return ''.join(chr(ord(c) + 0xFEE0) if ('A' <= c <= 'Z' or 'a' <= c <= 'z' or '0' <= c <= '9') else c for c in s)


def wlen(seg):
    return len(krenc.squeeze(seg.replace(' ', '　')))


def rewrap(ko, jp):
    segs = ko.split('％')
    jmax = max(len(p) for p in jp.split('％'))
    lim = max(WIDTH, jmax)
    head = 1 if re.match(r'^[^％「」]{1,14}％「', jp) else 0
    i = head; changed = False
    while i < len(segs):
        s = segs[i]
        if wlen(s) <= lim: i += 1; continue
        cut = None
        for k in range(len(s) - 1, 0, -1):                       # 넘지 않는 가장 긴 앞부분을 공백에서
            if s[k] == ' ' and wlen(s[:k]) <= lim: cut = k; break
        if cut is None: return ko, 'cut'
        a, b = s[:cut], s[cut + 1:]
        segs[i] = a
        if i + 1 < len(segs) and not segs[i + 1].startswith('「'):
            segs[i + 1] = b + ' ' + segs[i + 1].lstrip(' ')
        else:
            segs.insert(i + 1, b)
        changed = True; i += 1
    if len(segs) > max(MAXLINES, jp.count('％') + 1): return ko, 'lines'
    return '％'.join(segs), ('wrap' if changed else '')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    up = os.path.join(ROOT, 'work', 'text', 'uniq.tsv')
    U = list(csv.DictReader(open(up, encoding='utf-8'), delimiter='\t'))
    rows = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'my files', '프퀘', '*.tsv'))):
        for r in csv.DictReader(open(f, encoding='utf-8-sig'), delimiter='\t'):
            rows[int(r['번호'])] = (r['위치'], r['JP'], r['KO'])
    assert len(rows) == len(U) and all(rows[i + 1][1] == U[i]['JP'] for i in range(len(U))), '원문·번호 어긋남'
    rep = []; cnt = collections.Counter(); left = []
    for n in sorted(rows):
        w, jp, ko0 = rows[n]; ko = TOKEN_FIX.get(n, ko0)
        if n in TOKEN_FIX: cnt['토큰 손질'] += 1
        if w.startswith('STAFF.MES'):
            U[n - 1]['KO'] = ''; cnt['스태프 롤 원본'] += 1; continue
        m = re.match(r'^([^％「」]{1,12})％「', jp)
        if m and m.group(1) in SPEAKER:
            ko = re.sub(r'^[^％「」]{1,14}(?=％「)', SPEAKER[m.group(1)], ko)
        if m and re.match(r'^女の子[Ａ-Ｚα-ω]', m.group(1)):
            ko = re.sub(r'^(?:소녀|여자아이)(?= ?[A-Za-zＡ-Ｚα-ω])', '여자애', ko)
        for a, b in NAMES: ko = rename(ko, a, b)
        for term, a_, b_ in COND:
            if term in jp.replace('ブロードソード', ''): ko = rename(ko, a_, b_)
        if 'ウィロー殿' in jp: ko = re.sub(r'윌로 공(?![격략부작포평개])', '윌로 님', ko)
        ko = re.sub(r'^([^％「」]{1,14}?) ?([A-Za-zＡ-Ｚ])(?=％「)', lambda mm: mm.group(1) + zen(mm.group(2)), ko)   # 화자 기호 붙여 쓰고 전각
        ko = zen(ko).replace('—', '―').replace('ㅡ', '―').replace('S·', 'Ｓ・').replace('M·', 'Ｍ・').replace('Ｓ·', 'Ｓ・').replace('Ｍ·', 'Ｍ・')
        ko = re.sub(r' *％ *', '％', ko)                     # 줄바꿈 앞뒤 반각 공백(줄 첫머리 빈칸) 지움
        for t in '％「」『』':
            if jp.count(t) != ko.count(t): raise SystemExit('토큰 %s 어긋남 %d «%s» / «%s»' % (t, n, jp, ko))
        ko2, why = (ko, '') if w.startswith('START.MES') else rewrap(ko, jp)   # 저장 경고 화면은 자동 줄 접기(원문 52자 줄)
        if why in ('cut', 'lines'): left.append((n, w, why, ko))
        elif why: cnt['줄 다시 나눔'] += 1
        ko = ko2
        try:
            for ch in krenc.squeeze(ko.replace(' ', '　')): krenc.code_of(ch) if not ('가' <= ch <= '힣') else None
        except ValueError as e: left.append((n, w, str(e), ko))
        if ko != ko0: rep.append((n, w, jp, ko0, ko)); cnt['바뀐 줄'] += 1
        U[n - 1]['KO'] = ko
    with open(up, 'w', encoding='utf-8', newline='\n') as o:
        o.write('JP\t출현수\t첫위치\tKO\n')
        for r in U: o.write('%s\t%s\t%s\t%s\n' % (r['JP'], r['출현수'], r['첫위치'], r['KO']))
    with open(os.path.join(ROOT, 'work', 'text', 'merge_report.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\tJP\t받은 KO\t병합 KO\n')
        for x in rep: o.write('%d\t%s\t%s\t%s\t%s\n' % x)
    print(dict(cnt))
    print('남은 문제', len(left))
    for x in left[:40]: print('  ', x)


if __name__ == '__main__':
    main()
