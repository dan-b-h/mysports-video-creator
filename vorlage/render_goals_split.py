"""Tor-Zusammenschnitt 9:16 als Splitscreen: Tore abwechselnd oben / unten.
Die aktive Hälfte läuft, die andere zeigt ein abgedunkeltes Standbild (vorheriges bzw. nächstes Tor).
Spielstand in einer Zeile auf der Trennlinie: Heimteam | Score | Auswärtsteam.
Aufruf: python3 06_Vorlage/render_goals_split.py spec.json ausgabe.mp4
spec: source, headline [..], home, away, segments [{start,end,score,crop_x_rel,sub?}]
      optional: headline_font (Datei in 03_Brand), seam_color (ffmpeg-Farbe), seam_height (px)"""
import sys, json, subprocess, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
from brand_text import bold, draw_lines, FONT_NAME, FONT_SUB, RED, RED_SOLID, WHITE, SIDE, W, H, GAP, RADIUS, PADX
LOGO_SHIFT, HALF = 200, 960
CW, CH, CY = 1012, 900, 175          # Ausschnitt aus 1920x1080 (ohne Einblendung oben), Seitenverhältnis 1080:960
spec_path, out = sys.argv[1], sys.argv[2]
spec = json.load(open(spec_path, encoding='utf-8'))
FPS = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', spec['source']], capture_output=True, text=True).stdout.strip() or '25'
segs = spec['segments']; L = [s['end'] - s['start'] for s in segs]; SRC = sum(L)
INTRO = spec.get('intro', 0.0)   # ruhiger Einstieg mit Standbildern (zählt nicht als Quellmaterial)
T = SRC + INTRO
if spec.get('allow_over_30'):   # nur mit ausdrücklicher Freigabe von Dan
    print(f'ACHTUNG: Quelle {SRC:.2f} s – über der 30-s-Regel (allow_over_30)')
else:
    assert SRC <= 30.0 + 1e-6, f'Quelle {SRC:.1f} s – max. 30 s'
pngdir = os.path.splitext(spec_path)[0] + '_png'; os.makedirs(pngdir, exist_ok=True)

def save(img, name):
    p = f'{pngdir}/{name}.png'; img.save(p); return p

def scorer_label(text, y):
    fs = ImageFont.truetype(FONT_SUB, 48); bh = int(48 * 1.3); sw = int(fs.getlength(text)) + 2 * PADX
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    sx = (W - sw) // 2
    d.rounded_rectangle([sx, y, sx + sw, y + bh], radius=RADIUS, fill=RED)
    a_, de = fs.getmetrics(); d.text((sx + PADX, y + (bh - (a_ + de)) // 2), text, font=fs, fill=WHITE, **bold(fs))
    return img

def score_line(home, score, away):
    """Heimteam | Score | Auswärtsteam in einer Zeile, zentriert auf der Trennlinie; darunter Minute + Torschütze."""
    ft, fb = ImageFont.truetype(FONT_SUB, 52), ImageFont.truetype(FONT_NAME, 84)
    boxh = int(84 * 1.25)
    parts = [(home, ft, RED, WHITE), (score, fb, WHITE, RED_SOLID), (away, ft, RED, WHITE)]
    widths = [int(f.getlength(t)) + 2 * PADX + (8 if f is fb else 0) for t, f, _, _ in parts]
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = (W - widths[1]) // 2 - GAP - widths[0]; y = HALF - boxh // 2   # Score-Feld immer exakt in der Bildmitte
    for (t, f, bg, fg), w in zip(parts, widths):
        d.rounded_rectangle([x, y, x + w, y + boxh], radius=RADIUS, fill=bg)
        tw = int(f.getlength(t)); a_, de = f.getmetrics()
        d.text((x + (w - tw) // 2, y + (boxh - (a_ + de)) // 2), t, font=f, fill=fg, **bold(f))
        x += w + GAP
    return img

head = Image.new('RGBA', (W, H), (0, 0, 0, 0))
HEAD_FONT = os.path.join(os.path.dirname(FONT_SUB), spec.get('headline_font', 'Figtree-Bold.ttf'))   # z. B. Figtree-SemiBold.ttf
draw_lines(head, spec['headline'], ImageFont.truetype(HEAD_FONT, 60), SIDE, 250, int(60 * 1.3), RED, WHITE)
def run(args): subprocess.run(['ffmpeg', '-v', 'error', '-y'] + args, check=True)
def crop(i):
    r = segs[i].get('crop_x_rel', 0.5)
    return f"crop={CW}:{CH}:(iw-{CW})*{r}:{CY},scale=1080:{HALF},setsar=1"
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', FPS]
clips = []
for i, s in enumerate(segs):   # 1) Spielclips pro Tor, 2) Standbilder (erstes / letztes Bild)
    c = f'{pngdir}/play{i}.mp4'
    run(['-ss', str(s['start']), '-t', str(L[i]), '-i', spec['source'], '-vf', crop(i), '-an'] + ENC + [c]); clips.append(c)
    run(['-i', c, '-frames:v', '1', f'{pngdir}/first{i}.png'])                      # exakt erstes Bild des Clips
    run(['-sseof', '-0.5', '-i', c, '-update', '1', f'{pngdir}/last{i}.png'])       # exakt letztes Bild des Clips
DIM = 0.45
def hold(img, dur, name, mode):
    """Standbild: 'end' = Szene friert ein und dunkelt weich ab; 'next' = wartet abgedunkelt und hellt am Ende auf."""
    o = f'{pngdir}/{name}.mp4'
    fade = 'fade=t=in:st=0:d=0.5:alpha=1' if mode == 'end' else f'fade=t=out:st={dur-0.35:.3f}:d=0.35:alpha=1'
    run(['-loop', '1', '-t', f'{dur:.3f}', '-i', img, '-f', 'lavfi', '-i', f'color=black:s=1080x{HALF}:r={FPS}:d={dur:.3f}',
         '-filter_complex', f'[1]format=rgba,colorchannelmixer=aa={DIM},{fade}[k];[0][k]overlay=shortest=1,format=yuv420p'] + ENC + [o])
    return o
top, bot = [], []
if INTRO:
    top.append(hold(f'{pngdir}/first0.png', INTRO, 'intro', 'next'))
for i in range(len(segs)):
    other = hold(f'{pngdir}/first1.png', L[i] + INTRO, f'hold{i}', 'next') if i == 0 else hold(f'{pngdir}/last{i-1}.png', L[i], f'hold{i}', 'end')
    (top if i % 2 == 0 else bot).append(clips[i]); (bot if i % 2 == 0 else top).append(other)
def cat(lst, name):
    o = f'{pngdir}/{name}.mp4'; lf = f'{pngdir}/{name}.txt'
    open(lf, 'w').write(''.join(f"file '{os.path.abspath(x)}'\n" for x in lst))
    run(['-f', 'concat', '-safe', '0', '-i', lf, '-c', 'copy', o]); return o
tv, bv = cat(top, 'top'), cat(bot, 'bottom')
SEAM_COLOR = spec.get('seam_color', 'white@0.9')   # Trennlinie, z. B. '0xDA291C'
SEAM_H = spec.get('seam_height', 4)
inputs = ['-i', tv, '-i', bv, '-i', spec['source'], '-i', '03_Brand/mySports.png', '-i', save(head, 'headline')]
f = ['[0:v][1:v]vstack=inputs=2[stk]', f"[stk]drawbox=x=0:y={HALF - SEAM_H // 2}:w=1080:h={SEAM_H}:color={SEAM_COLOR}:t=fill[stk2]"]
for i, s in enumerate(segs):
    f.append(f"[2:a]atrim={s['start']}:{s['end']},asetpts=PTS-STARTPTS,afade=t=in:d=0.12,afade=t=out:st={L[i]-0.15:.3f}:d=0.15[a{i}]")
f.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={max(INTRO,0.01):.3f}[a_in]')
f.append('[a_in]' + ''.join(f'[a{i}]' for i in range(len(segs))) + f'concat=n={len(segs)+1}:v=0:a=1[aout]')
f.append(f'[stk2][3:v]overlay=0:{LOGO_SHIFT}[b1]'); HEAD_DUR = spec.get('headline_dur', INTRO + 0.8)   # ohne Intro z. B. 2.5 s über dem laufenden Clip
f.append(f"[b1][4:v]overlay=0:0:enable='lt(t,{HEAD_DUR:.2f})'[b2]")
last, k, t0 = 'b2', 5, INTRO
SUB_LEAD = 1.0   # Torschütze erscheint 1 s vor dem Tor
LABEL_Y = HALF + int(84 * 1.25) // 2 + 50   # Torschütze immer 50 px unter dem Spielstand
def ov(img_path, a, b):
    global last, k
    inputs.extend(['-i', img_path])
    f.append(f"[{last}][{k}:v]overlay=0:0:enable='between(t,{a:.3f},{b-0.001:.3f})'[c{k}]"); last = f'c{k}'; k += 1
for i, s in enumerate(segs):
    t1 = t0 + L[i]
    tg = t0 + (s['goal_at'] - s['start']) if 'goal_at' in s else t0
    if tg > t0:   # vor dem Tor: bisheriger Spielstand
        ov(save(score_line(spec['home'], s['prev_score'], spec['away']), f'prev{i}'), t0, tg)
    ov(save(score_line(spec['home'], s['score'], spec['away']), f'score{i}'), tg, t1)
    if s.get('sub'):
        ov(save(scorer_label(s['sub'], LABEL_Y), f'sub{i}'), max(t0, tg - SUB_LEAD), t1)
    t0 = t1
fs = os.path.splitext(spec_path)[0] + '_filter.txt'; open(fs, 'w').write(';'.join(f))
cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex_script', fs, '-map', f'[{last}]', '-map', '[aout]',
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
       '-t', f'{T:.3f}', '-movflags', '+faststart', out]
subprocess.run(cmd, check=True); print(f'ok {out} ({T:.1f} s, Quelle {SRC:.1f} s)')
