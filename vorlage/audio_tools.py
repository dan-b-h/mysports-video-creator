"""Audio-Werkzeuge für den mySports Video Creator (laufen in der Cloud-Umgebung von Claude).

Einrichtung (einmal pro Sitzung, Modelle kommen von GitHub, Hugging Face ist gesperrt):
    pip install --break-system-packages sherpa-onnx
    curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-turbo.tar.bz2 | tar xj
    curl -sSL -o silero_vad.onnx https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx

Audio vorher auf dem PC extrahieren und in die Cloud holen:
    ffmpeg -i Originalvideos/X.mp4 -vn -ac 1 -ar 16000 04_Arbeitsdateien/<datum>/audio/X.wav

Befehle:
    python3 audio_tools.py transcribe X.wav             -> Satzweise Transkript mit Zeiten
    python3 audio_tools.py window X.wav 12.1 17.5       -> Text eines Zeitfensters (genauer bei Mundart)
    python3 audio_tools.py pauses X.wav [offset]        -> kurze Sprechpausen (für saubere Schnitte)
    python3 audio_tools.py wordtimes X.wav cues.json out.json
        cues.json: {"segments":[[s,e],...], "cues":[{"id","src_s","src_e","text"}], ...}
        -> ergänzt pro Untertitel s/e/word_t in Clip-Zeit (Wort erscheint Mitte der Sprechzeit + 0,2 s)
"""
import sys, json, wave
import numpy as np
import sherpa_onnx

import os
MD = os.environ.get('MODELLE', '.')   # Ordner mit den Modellen (Colab: Drive-Cache)
M = os.path.join(MD, 'sherpa-onnx-whisper-turbo/')
def load(path):
    w = wave.open(path)
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

def recognizer():
    return sherpa_onnx.OfflineRecognizer.from_whisper(encoder=M + 'turbo-encoder.int8.onnx', decoder=M + 'turbo-decoder.int8.onnx',
                                                      tokens=M + 'turbo-tokens.txt', language=os.environ.get('SPRACHE', 'de'), task='transcribe', num_threads=2)

def vad_segments(a, min_silence=0.4, thr=0.5, max_speech=20):
    cfg = sherpa_onnx.VadModelConfig(); cfg.silero_vad.model = os.path.join(MD, 'silero_vad.onnx')
    cfg.silero_vad.min_silence_duration = min_silence; cfg.silero_vad.threshold = thr
    cfg.silero_vad.max_speech_duration = max_speech; cfg.silero_vad.min_speech_duration = 0.05; cfg.sample_rate = 16000
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=900); out = []
    def drain():
        while not vad.empty():
            s = vad.front; out.append((s.start / 16000, (s.start + len(s.samples)) / 16000, s.samples)); vad.pop()
    for i in range(0, len(a), 512):
        vad.accept_waveform(a[i:i + 512]); drain()
    vad.flush(); drain(); return out

def text(rec, samples):
    st = rec.create_stream(); st.accept_waveform(16000, samples); rec.decode_stream(st); return st.result.text.strip()

if __name__ == '__main__':
    cmd, path = sys.argv[1], sys.argv[2]; a = load(path)
    if cmd == 'transcribe':
        rec = recognizer()
        for s, e, smp in vad_segments(a):
            print(f'[{s:6.1f}-{e:6.1f}] {text(rec, smp)}')
    elif cmd == 'window':
        s, e = float(sys.argv[3]), float(sys.argv[4]); print(text(recognizer(), a[int(s * 16000):int(e * 16000)]))
    elif cmd == 'pauses':
        off = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        segs = vad_segments(a, min_silence=0.06)
        print([(round(off + segs[i][1], 2), round(off + segs[i + 1][0], 2)) for i in range(len(segs) - 1)])
    elif cmd == 'wordtimes':
        spec = json.load(open(sys.argv[3], encoding='utf-8')); segs = spec['segments']
        hop = 0.02; n = int(hop * 16000)
        rms = np.array([np.sqrt(np.mean(a[i:i + n] ** 2)) for i in range(0, len(a) - n, n)])
        voiced = rms > max(0.012, np.percentile(rms, 30) * 1.5)
        def clip_t(src):
            off = 0
            for s, e in segs:
                if s - 0.01 <= src <= e + 0.01: return round(off + src - s, 2)
                off += e - s
            raise ValueError(src)
        for c in spec['cues']:
            s, e = c['src_s'], c['src_e']
            idx = np.nonzero(voiced[int(s / hop):int(e / hop)])[0]
            if len(idx) < 0.3 * (e - s) / hop: idx = np.arange(int((e - s) / hop))   # leise Stimme (z. B. Reporter): gleichmässig verteilen
            words = c['text'].split(); wts = np.array([len(x) + 1 for x in words], float)
            mid = (np.cumsum(wts) - wts * 0.5) / wts.sum()
            c['s'], c['e'] = clip_t(s), clip_t(e)
            c['word_t'] = [round(float(min(clip_t(s + idx[min(int(m * len(idx)), len(idx) - 1)] * hop) + 0.2, c['e'] - 0.3)), 2) for m in mid]
        json.dump(spec, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print('ok')
