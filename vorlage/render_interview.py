"""Interview-Clip 9:16 im mySports-Design, Untertitel Wort für Wort, weiche Übergänge.
Aufruf: python3 06_Vorlage/render_interview.py spec.json ausgabe.mp4"""
import sys, json, subprocess, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brand_text import subtitle_states, name_tag, layout
XF = 0.5          # Überblendung zwischen Interviewteilen (s)
LOGO_SHIFT = 200  # Logo-PNG liegt bei y 1534-1609, verschoben auf 1734-1809
spec_path, out = sys.argv[1], sys.argv[2]
spec = json.load(open(spec_path, encoding='utf-8'))
FPS = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', spec['source']], capture_output=True, text=True).stdout.strip() or '25'
XF = spec.get('xfade', XF)
pngdir = os.path.splitext(spec_path)[0] + '_png'; os.makedirs(pngdir, exist_ok=True)
segs = spec['segments']; lens = [e - s for s, e in segs]
if spec.get('allow_over_30'):   # nur mit ausdrücklicher Freigabe von Dan
    print(f'ACHTUNG: Quelle {sum(lens):.2f} s – über der 30-s-Regel (allow_over_30)')
else:
    assert sum(lens) <= 30.0 + 1e-6, 'Quelle über 30 s'
starts, acc = [], 0.0
for L in lens: starts.append(acc); acc += L
def shift(t):  # Zeit ohne Überblendung -> Zeit mit Überblendung
    k = max(i for i, s in enumerate(starts) if t >= s - 1e-6)
    return round(t - k * XF, 3)
SUB_TOP, NAME_TOP = layout([c['text'] for c in spec['cues']])
name_tag(spec['tag'], NAME_TOP).save(f'{pngdir}/tag.png')
inputs = ['-i', spec['source'], '-i', '03_Brand/mySports.png', '-i', f'{pngdir}/tag.png']
f = []
for i, (s, e) in enumerate(segs):
    if spec.get('video_h'):   # herausgezoomt: Bild oben (Höhe video_h), unten unscharf verlängert -> Gesicht weiter weg vom Text
        VH = spec['video_h']; CW = round(1080 * 1080 / VH / 2) * 2
        cx = spec['crop_x'] + 304 - CW // 2
        f.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,split[fg{i}][bg{i}]")
        f.append(f"[bg{i}]crop=608:1080:{spec['crop_x']}:0,scale=1080:1920,boxblur=40:2,eq=brightness=-0.08[bb{i}]")
        f.append(f"[fg{i}]crop={CW}:1080:{cx}:0,scale=1080:{VH}[ff{i}]")
        f.append(f"[bb{i}][ff{i}]overlay=0:0,setsar=1,fps={FPS}[v{i}]")
    else:
        f.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,crop=608:1080:{spec['crop_x']}:0,scale=1080:1920,setsar=1,fps={FPS}[v{i}]")
    f.append(f'[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}]')
lv, la, off = 'v0', 'a0', 0.0
for i in range(1, len(segs)):
    off += lens[i - 1] - XF
    f.append(f'[{lv}][v{i}]xfade=transition=fade:duration={XF}:offset={off:.3f}[vx{i}]')
    f.append(f'[{la}][a{i}]acrossfade=d={XF}[ax{i}]')
    lv, la = f'vx{i}', f'ax{i}'
total = sum(lens) - XF * (len(segs) - 1)
TAIL = spec.get('tail', 0.0)   # Standbild + Stille am Schluss (zählt nicht als Quellmaterial), damit der letzte Satz nicht abrupt endet
FO = spec.get('fade_out', 0.3)   # Ausblenden am Schluss; kurz halten, wenn der letzte Satz knapp endet
f.append(f'[{la}]afade=t=in:d=0.04,afade=t=out:st={total-FO:.3f}:d={FO},apad=pad_dur={TAIL}[aout]')
if TAIL:
    f.append(f'[{lv}]tpad=stop_mode=clone:stop_duration={TAIL}[vtail]'); lv = 'vtail'
total_out = total + TAIL
f.append(f'[{lv}][1:v]overlay=0:{LOGO_SHIFT}[b1]'); f.append('[b1][2:v]overlay=0:0[b2]')
last, k = 'b2', 3
MIN_FULL = 0.9   # ganzer Satz mind. so lange vollständig sichtbar (s)
HOLD = 0.6       # Untertitel bleibt nach Sprechende noch stehen, bis der nächste beginnt
cues = spec['cues']
report = []
for i, c in enumerate(cues):
    states = subtitle_states(c['text'], SUB_TOP)
    wt = [shift(t) for t in c['word_t']][:len(states)]
    end = shift(c['e'])
    nxt = shift(cues[i + 1]['s']) if i + 1 < len(cues) else total + TAIL
    end = min(max(end, end + HOLD), nxt - 0.05, total + TAIL)
    if i + 1 == len(cues): end = total + TAIL   # letzter Satz bleibt bis zum Schluss stehen
    if wt[-1] > end - MIN_FULL:  # Einblendung stauchen, damit alles lesbar wird
        t0 = wt[0]; tgt = max(t0 + 0.1, end - MIN_FULL)
        wt = [t0 + (t - t0) * (tgt - t0) / (wt[-1] - t0) for t in wt]
    report.append(f"{c['id']}: {len(states)} Woerter, voll sichtbar {end - wt[-1]:.1f} s")
    for j, img in enumerate(states):
        p = f"{pngdir}/{c['id']}_{j:02d}.png"; img.save(p)
        t0 = wt[j]; t1 = wt[j + 1] if j + 1 < len(states) else end
        inputs += ['-i', p]
        f.append(f"[{last}][{k}:v]overlay=0:0:enable='between(t,{t0},{t1-0.001:.3f})'[c{k}]"); last = f'c{k}'; k += 1
fs = os.path.splitext(spec_path)[0] + '_filter.txt'
open(fs, 'w').write(';'.join(f))
cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex_script', fs, '-map', f'[{last}]', '-map', '[aout]',
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
       '-movflags', '+faststart', out]
print('\n'.join(report))
subprocess.run(cmd, check=True); print(f'ok {out} ({total_out:.1f} s, Quelle {sum(lens):.2f} s)')
