"""Kombi-Reel 9:16: Phase 1 = Tore (untere Hälfte, mit Ton), Phase 2 = Interview (obere Hälfte, mit Ton + Untertitel).
Die jeweils andere Hälfte zeigt ein abgedunkeltes Standbild bzw. die Tore stumm ein zweites Mal.
Aufruf: python3 06_Vorlage/render_combo.py spec.json ausgabe.mp4
spec: goals{source, home, away, segments[{start,end,goal_at,prev_score,score,sub,crop_x_rel}]},
      interview{source, face_x, tag, segments[[s,e]], cues[...] (Clip-Zeit, aus audio_tools wordtimes)},
      headline [..], seam_color"""
import sys, json, subprocess, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import brand_text as BT
from brand_text import (bold, draw_lines, subtitle_states, name_tag, layout, FONT_NAME, FONT_SUB,
                        RED, RED_SOLID, WHITE, SIDE, W, H, GAP, RADIUS, PADX)
LOGO_SHIFT, HALF = 200, 960
CW, CH, CY = 1012, 900, 175
spec_path, out = sys.argv[1], sys.argv[2]
spec = json.load(open(spec_path, encoding='utf-8'))
G, I = spec['goals'], spec['interview']
FPS = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                      '-of', 'csv=p=0', G['source']], capture_output=True, text=True).stdout.strip() or '25'
gsegs = G['segments']; GL = [s['end'] - s['start'] for s in gsegs]; T1 = sum(GL)
isegs = I['segments']; IL = [e - s for s, e in isegs]; T2 = sum(IL)
if spec.get('allow_over_30'):
    print(f'ACHTUNG: Tore {T1:.2f} s / Interview {T2:.2f} s – über 30 s nur mit Freigabe von Dan')
else:
    assert T1 <= 30 + 1e-6 and T2 <= 30 + 1e-6, 'max. 30 s pro Quelldatei'
T = T1 + T2
pngdir = os.path.splitext(spec_path)[0] + '_png'; os.makedirs(pngdir, exist_ok=True)
def run(a): subprocess.run(['ffmpeg', '-v', 'error', '-y'] + a, check=True)
def save(img, n): p = f'{pngdir}/{n}.png'; img.save(p); return p
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', FPS]
DIM = 0.45

def scorer_label(text, y):
    fs = ImageFont.truetype(FONT_SUB, 48); bh = int(48 * 1.3); sw = int(fs.getlength(text)) + 2 * PADX
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); sx = (W - sw) // 2
    d.rounded_rectangle([sx, y, sx + sw, y + bh], radius=RADIUS, fill=RED)
    a_, de = fs.getmetrics(); d.text((sx + PADX, y + (bh - (a_ + de)) // 2), text, font=fs, fill=WHITE, **bold(fs))
    return img
def score_line(home, score, away):
    ft, fb = ImageFont.truetype(FONT_SUB, 52), ImageFont.truetype(FONT_NAME, 84); boxh = int(84 * 1.25)
    parts = [(home, ft, RED, WHITE), (score, fb, WHITE, RED_SOLID), (away, ft, RED, WHITE)]
    widths = [int(f.getlength(t)) + 2 * PADX + (8 if f is fb else 0) for t, f, _, _ in parts]
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = (W - widths[1]) // 2 - GAP - widths[0]; y = HALF - boxh // 2
    for (t, f, bg, fg), w in zip(parts, widths):
        d.rounded_rectangle([x, y, x + w, y + boxh], radius=RADIUS, fill=bg)
        tw = int(f.getlength(t)); a_, de = f.getmetrics()
        d.text((x + (w - tw) // 2, y + (boxh - (a_ + de)) // 2), t, font=f, fill=fg, **bold(f)); x += w + GAP
    return img

# 1) Tore: Clips unten (1080x960)
gclips = []
for i, s in enumerate(gsegs):
    c = f'{pngdir}/goal{i}.mp4'
    run(['-ss', str(s['start']), '-t', str(GL[i]), '-i', G['source'], '-vf',
         f"crop={CW}:{CH}:(iw-{CW})*{s.get('crop_x_rel', 0.5)}:{CY},scale=1080:{HALF},setsar=1", '-an'] + ENC + [c])
    gclips.append(c)
# 2) Interview oben (1080x960): Ausschnitt 1215x1080 um face_x
IW = 1216; ix = max(0, min(1920 - IW, I['face_x'] - IW // 2))
iclips = []
for i, (s, e) in enumerate(isegs):
    c = f'{pngdir}/int{i}.mp4'
    run(['-ss', str(s), '-t', str(e - s), '-i', I['source'], '-vf', f'crop={IW}:1080:{ix}:0,scale=1080:{HALF},setsar=1', '-an'] + ENC + [c])
    iclips.append(c)
run(['-i', iclips[0], '-frames:v', '1', f'{pngdir}/int_first.png'])
def still(img, dur, name, fade):
    o = f'{pngdir}/{name}.mp4'
    fd = 'fade=t=in:st=0:d=0.5:alpha=1' if fade == 'in' else f'fade=t=out:st={dur-0.4:.3f}:d=0.4:alpha=1'
    run(['-loop', '1', '-t', f'{dur:.3f}', '-i', img, '-f', 'lavfi', '-i', f'color=black:s=1080x{HALF}:r={FPS}:d={dur:.3f}',
         '-filter_complex', f'[1]format=rgba,colorchannelmixer=aa={DIM},{fd}[k];[0][k]overlay=shortest=1,format=yuv420p'] + ENC + [o])
    return o
def cat(lst, name):
    o = f'{pngdir}/{name}.mp4'; lf = f'{pngdir}/{name}.txt'
    open(lf, 'w').write(''.join(f"file '{os.path.abspath(x)}'\n" for x in lst))
    run(['-f', 'concat', '-safe', '0', '-i', lf, '-c', 'copy', o]); return o
top = cat([still(f'{pngdir}/int_first.png', T1, 'top_hold', 'out')] + iclips, 'top')
# unten in Phase 2: Tore stumm nochmals, leicht abgedunkelt, Rest als Standbild
if spec.get('bottom_phase2', 'still') == 'still':   # Standbild (letztes Torbild), abgedunkelt
    if spec.get('bottom_still_at'):   # bestimmtes Bild aus der Zusammenfassung (Quellzeit), z. B. Torjubel
        sx = spec.get('bottom_still_crop', 0.5)
        run(['-ss', str(spec['bottom_still_at']), '-i', G['source'], '-frames:v', '1', '-vf',
             f"crop={CW}:{CH}:(iw-{CW})*{sx}:{CY},scale=1080:{HALF},setsar=1", f'{pngdir}/goal_last.png'])
    else:
        run(['-sseof', '-0.5', '-i', gclips[-1], '-update', '1', f'{pngdir}/goal_last.png'])
    bot2 = still(f'{pngdir}/goal_last.png', T2, 'bot_hold', 'in')
else:                                                 # Tore stumm wiederholen
    gl = cat(gclips, 'goals_all'); bot2 = f'{pngdir}/bot2.mp4'
    run(['-stream_loop', '1', '-i', gl, '-t', f'{T2:.3f}', '-vf', 'eq=brightness=-0.12:saturation=0.8', '-an'] + ENC + [bot2])
bot = cat(gclips + [bot2], 'bottom')

# 3) Zusammensetzen
head = Image.new('RGBA', (W, H), (0, 0, 0, 0))
draw_lines(head, spec['headline'], ImageFont.truetype(FONT_SUB, 60), SIDE, 250, int(60 * 1.3), RED, WHITE)
BT.SUB_BOTTOM = spec.get('sub_bottom', BT.SUB_BOTTOM)   # z. B. 920 = Untertitel oben, knapp über der Mittellinie
SUB_TOP, NAME_TOP = layout([c['text'] for c in I['cues']])
if spec.get('name_on_seam'):   # Namensfeld mittig auf der Trennlinie, Untertitel direkt darunter
    nh = int(BT.NAME_SIZE * 1.3); NAME_TOP = HALF - nh // 2; SUB_TOP = NAME_TOP + nh + BT.NAME_GAP
inputs = ['-i', top, '-i', bot, '-i', G['source'], '-i', I['source'], '-i', '03_Brand/mySports.png',
          '-i', save(head, 'headline'), '-i', save(name_tag(I['tag'], NAME_TOP), 'tag')]
seam = spec.get('seam_color', '0xDA291C')
f = ['[0:v][1:v]vstack=inputs=2[stk]', f'[stk]drawbox=x=0:y={HALF-2}:w=1080:h=4:color={seam}:t=fill[stk2]']
for i, s in enumerate(gsegs):
    f.append(f"[2:a]atrim={s['start']}:{s['end']},asetpts=PTS-STARTPTS,afade=t=in:d=0.12,afade=t=out:st={GL[i]-0.15:.3f}:d=0.15[ga{i}]")
for i, (s, e) in enumerate(isegs):
    f.append(f"[3:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.05,afade=t=out:st={IL[i]-0.1:.3f}:d=0.1[ia{i}]")
na = len(gsegs) + len(isegs)
f.append(''.join(f'[ga{i}]' for i in range(len(gsegs))) + ''.join(f'[ia{i}]' for i in range(len(isegs))) + f'concat=n={na}:v=0:a=1[aout]')
f.append(f'[stk2][4:v]overlay=0:{LOGO_SHIFT}[b1]')
f.append(f"[b1][5:v]overlay=0:0:enable='lt(t,{spec.get('headline_dur', 2.5)})'[b2]")
f.append(f"[b2][6:v]overlay=0:0:enable='gte(t,{T1:.3f})'[b3]")
last, k = 'b3', 7
def ov(p, a, b):
    global last, k
    inputs.extend(['-i', p]); f.append(f"[{last}][{k}:v]overlay=0:0:enable='between(t,{a:.3f},{b-0.001:.3f})'[c{k}]"); last = f'c{k}'; k += 1
LABEL_Y = HALF + int(84 * 1.25) // 2 + 50
t0 = 0.0
for i, s in enumerate(gsegs):
    t1 = t0 + GL[i]; tg = t0 + s['goal_at'] - s['start']
    ov(save(score_line(G['home'], s['prev_score'], G['away']), f'prev{i}'), t0, tg)
    ov(save(score_line(G['home'], s['score'], G['away']), f'score{i}'), tg, t1)
    ov(save(scorer_label(s['sub'], LABEL_Y), f'sub{i}'), max(t0, tg - 1.0), t1)
    t0 = t1
cues = I['cues']
for i, c in enumerate(cues):
    states = subtitle_states(c['text'], SUB_TOP); wt = [T1 + t for t in c['word_t']][:len(states)]
    end = T1 + (cues[i + 1]['s'] - 0.05 if i + 1 < len(cues) else T2)
    end = max(end, wt[-1] + 0.9)
    for j, img in enumerate(states):
        a = wt[j]; b = wt[j + 1] if j + 1 < len(states) else end
        ov(save(img, f"{c['id']}_{j:02d}"), a, b)
fs = os.path.splitext(spec_path)[0] + '_filter.txt'; open(fs, 'w').write(';'.join(f))
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex_script', fs, '-map', f'[{last}]', '-map', '[aout]',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
                '-t', f'{T:.3f}', '-movflags', '+faststart', out], check=True)
print(f'ok {out} ({T:.1f} s; Tore {T1:.1f} s, Interview {T2:.1f} s)')
