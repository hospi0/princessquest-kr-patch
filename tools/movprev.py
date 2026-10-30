# -*- coding: utf-8 -*-
"""동영상 자막 미리보기(2026-10-30) — work/movie/subs.tsv(movie·start·end·JP·KO) → work/movie/prev/<이름>.mp4
  원본 CPK(320×240 Cinepak) 를 640×480 으로 키워 아래에 한글(나눔고딕 Bold), 그 위에 작게 받아쓴 일본어(확인용)를 굽는다.
  python tools/movprev.py [이름…]"""
import os, sys, csv, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
FONTDIR = r'C:\claude\utils\font\nanum-gothic'
MOV = os.path.join(ROOT, 'work', 'movie')

HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 640
PlayResY: 480
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KO,NanumGothic,26,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,20,20,18,1
Style: JP,NanumGothic,15,&H00A0E0FF,&H00A0E0FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1,0,8,20,20,8,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(t):
    cs = int(round(t * 100)); return '%d:%02d:%02d.%02d' % (cs // 360000, cs // 6000 % 60, cs // 100 % 60, cs % 100)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = list(csv.DictReader(open(os.path.join(MOV, 'subs.tsv'), encoding='utf-8'), delimiter='\t'))
    names = sys.argv[1:] or sorted({r['movie'] for r in rows})
    out = os.path.join(MOV, 'prev'); os.makedirs(out, exist_ok=True)
    for nm in names:
        rs = [r for r in rows if r['movie'] == nm]
        ass = os.path.join(out, nm + '.ass')
        with open(ass, 'w', encoding='utf-8-sig') as w:
            w.write(HEAD)
            for r in rs:
                a, b = float(r['start']), max(float(r['end']), float(r['start']) + 1.0)
                w.write('Dialogue: 0,%s,%s,KO,,0,0,0,,%s\n' % (ts(a), ts(b), r['KO']))
                w.write('Dialogue: 0,%s,%s,JP,,0,0,0,,%s\n' % (ts(a), ts(b), r['JP']))
        vf = "scale=640:480:flags=neighbor,subtitles=%s.ass:fontsdir='%s'" % (nm, FONTDIR.replace('\\', '/').replace(':', '\\:'))
        cmd = [FF, '-v', 'error', '-y', '-i', os.path.join(MOV, 'cpk', nm + '.CPK'), '-vf', vf,
               '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', nm + '.mp4']
        r = subprocess.run(cmd, cwd=out)
        print(nm, '자막', len(rs), 'OK' if r.returncode == 0 else '실패')


if __name__ == '__main__':
    main()
