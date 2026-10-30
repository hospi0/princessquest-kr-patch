# -*- coding: utf-8 -*-
"""동영상(CPK) 소리 받아쓰기(2026-10-30, 벌크 슬래시 tools/asr_movie.py 꼴) — work/movie/wav/*.wav(16 kHz 모노)
   → work/movie/asr.tsv (movie·start·end·no_speech·JP)   ★VAD 끔(짧은 외침 버려짐 방지)
   C:\\claude\\utils\\whisper-venv\\Scripts\\python.exe tools/asr_movie.py"""
import glob, os, sys, wave
import numpy as np
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HINT = 'ウィロー、ウィル、タピオカ、マドレーヌ、ブラウニィ、カスタード、ジェラード、ミルフィーユ、チェロス、パンナコッタ、ペピー、カシス、ディルマ法王国、ラリアン、ソーダレス、ノースランド、ロウレス、ギムリア。'   # 대본 고유명사(첫 판에서 프롬프트를 그대로 읊는 환각이 있어 낱말 목록으로)
m = WhisperModel('large-v3', device='cuda', compute_type='float16')


def load(p):
    w = wave.open(p)
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


with open(os.path.join(ROOT, 'work', 'movie', 'asr.tsv'), 'w', encoding='utf-8', newline='\n') as fo:
    fo.write('movie\tstart\tend\tno_speech\tJP\n')
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'movie', 'wav', '*.wav'))):
        n = os.path.basename(p)[:-4]; x = load(p)
        seg, _ = m.transcribe(x, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False,
                              initial_prompt=HINT, word_timestamps=True)
        k = 0
        for s in seg:
            t = s.text.strip()
            if not t: continue
            if 'ご視聴' in t or 'ウィル、タピオカ' in t: continue          # 위스퍼 환각(끝 무음·프롬프트 읊기)
            a, b = (s.words[0].start, s.words[-1].end) if s.words else (s.start, s.end)   # 낱말 시각이 구간 시각보다 정확
            fo.write('%s\t%.2f\t%.2f\t%.2f\t%s\n' % (n, a, b, s.no_speech_prob, t)); k += 1
        print(n, '%.1fs' % (len(x) / 16000), '조각', k, 'peak %.2f' % np.abs(x).max())
print('끝')
