"""mySports Video Creator – App-Oberfläche für Colab (Gradio).

Start im Notebook:  import mvc_app; mvc_app.start(PROJEKT)
Alle Pfade sind relativ zum Projektordner im Drive (Originalvideos, 04_Arbeitsdateien, 05_Ausgabe).
"""
import os, re, json, glob, shutil, subprocess, time
import numpy as np
from PIL import Image, ImageDraw

V = os.path.dirname(os.path.abspath(__file__))          # Ordner mit den Render-Skripten
FORMATE = {'Tore-Splitscreen': ('render_goals_split.py', 'Spielhighlights'),
           'Interview': ('render_interview.py', 'Interview'),
           'Kombi Tore + Interview': ('render_combo.py', 'Interview')}


class Hinweis(Exception):
    """Fehler mit verständlicher Meldung für das Team."""


# ───────────────────────── Hilfen ─────────────────────────
def laenge(q):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', q],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def einzelbild(q, t, w=640, h=360):
    b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(max(t, 0)), '-i', q, '-frames:v', '1', '-vf', f'scale={w}:{h}',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    if len(b) < w * h * 3:
        return np.zeros((h, w, 3), np.uint8)
    return np.frombuffer(b[:w * h * 3], np.uint8).reshape(h, w, 3)


def mmss(s):
    return f'{int(s // 60)}:{s % 60:04.1f}'


def datum_aus(dateiname):
    m = re.match(r'(\d{6})_', os.path.basename(dateiname or ''))
    return m.group(1) if m else time.strftime('%y%m%d')


def videos():
    return sorted(os.path.basename(p) for p in glob.glob('Originalvideos/*') if p.lower().endswith(('.mp4', '.mov')))


def specs():
    return sorted(os.path.relpath(p, '04_Arbeitsdateien') for p in glob.glob('04_Arbeitsdateien/*/*.json')
                  if not p.endswith('_torliste.json'))


def rahmen_tor(r, b=640):      # Ausschnitt wie render_goals_split.py (1016x900 ab y=175 in 1920x1080)
    f = b / 1920; cw = 1016 * f; x = r * (b - cw)
    return [x, 175 * f, x + cw, 175 * f + 900 * f]


def rahmen_interview(crop_x, b=640):
    f = b / 1920
    return [crop_x * f, 0, (crop_x + 608) * f, 1080 * f - 1]


# ───────────────────────── Tor-Finder ─────────────────────────
FPS, X0, Y0, W, H = 5, 640, 60, 640, 120                # Ausschnitt der mySports-Anzeige (1920x1080)
HEIM, GAST = (172, 46, 36, 32), (432, 46, 36, 32)       # Torzahlen
BALKEN, UHR = (238, 54, 160, 15), (245, 10, 80, 20)     # magenta Balken (Anzeige sichtbar), Matchuhr


def _box(a, b):
    x, y, w, h = b
    return a[y:y + h, x:x + w]


def _hell(a, b):
    return _box(a, b).astype(int).min(2) > 200


def _sichtbar(a):
    m = _box(a, BALKEN).astype(int)
    return ((m[..., 0] > 120) & (m[..., 2] > 95) & (m[..., 1] < 60)).mean() > 0.6


def _anzeige(video):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', video, '-vf', f'fps={FPS},scale=1920:1080,crop={W}:{H}:{X0}:{Y0}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    i = 0
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield i / FPS, np.frombuffer(b, np.uint8).reshape(H, W, 3)
        i += 1


def _seite(video, t):
    """Wo sich die Spieler vor dem Tor ballen -> Vorschlag für den Bildausschnitt (0 = links, 1 = rechts)."""
    werte = []
    for dt in (-1.0, -0.6, -0.2):
        a = einzelbild(video, t + dt, 480, 270).astype(int)
        eis = a.min(2) > 170
        zeilen = [y for y in range(a.shape[0]) if eis[y].mean() > 0.35]
        if not zeilen:
            continue
        nicht = ~eis[min(zeilen):max(zeilen) + 1]
        s = nicht.mean(0) ** 2
        if s.sum() > 0:
            werte.append(float((np.arange(len(s)) * s).sum() / s.sum() / len(s)))
    x = float(np.median(werte)) if werte else 0.5
    return round(min(max(round(x * 20) / 20, 0.15), 0.85), 2)


def finde_tore(video, datum):
    """Misst Torzeitpunkte (Spielstand-Wechsel + Uhr-Stopp) und Schnitte. Speichert die Torliste und gibt Text + Bilder zurück."""
    if not os.path.exists(video):
        raise Hinweis(f'Video «{video}» nicht gefunden.')
    dauer = laenge(video)
    stand, kand, wechsel, uhr, uhr_lauf, weg = {'heim': None, 'gast': None}, {}, [], None, [], -99.0
    for t, a in _anzeige(video):
        if not _sichtbar(a):
            kand, uhr, weg = {}, None, t
            continue
        u = _hell(a, UHR)
        if uhr is not None and (u != uhr).mean() > 0.02:
            uhr_lauf.append(t)
        uhr = u
        for team, b in (('heim', HEIM), ('gast', GAST)):
            z = _hell(a, b)
            if stand[team] is None:
                stand[team] = z
                continue
            if (z != stand[team]).mean() > 0.03:
                k = kand.get(team)
                if k is None or (z != k[1]).mean() >= 0.03:
                    kand[team] = [t, z, 1]
                else:
                    k[2] += 1
                    if k[2] >= FPS:          # 1 s stabil = echter Wechsel
                        wechsel.append((k[0], team, k[0] - weg < 0.5))
                        stand[team] = z
                        kand.pop(team)
            else:
                kand.pop(team, None)
    if not wechsel:
        raise Hinweis('Keine Tore gefunden. Ist die mySports-Spielstandanzeige im Video zu sehen?')
    r = subprocess.run(['ffmpeg', '-nostats', '-i', video, '-vf', "scale=480:-2,select='gt(scene,0.25)',showinfo",
                        '-an', '-f', 'null', '-'], capture_output=True, text=True)
    schnitte = sorted(float(x) for x in re.findall(r'pts_time:([0-9.]+)', r.stderr))
    h_, g_, tore = 0, 0, []
    for t, team, unsicher in wechsel:
        vorher = f'{h_}:{g_}'
        h_, g_ = (h_ + 1, g_) if team == 'heim' else (h_, g_ + 1)
        stopp = [c for c in uhr_lauf if t - 8 <= c <= t]
        goal_at = round(stopp[-1] - 0.4, 1) if stopp else round(t - 1.0, 1)
        davor = [c for c in schnitte if c <= goal_at - 1.0]
        danach = [c for c in schnitte if c >= goal_at + 2.0]
        einst = davor[-1] if davor else 0.0
        ende = min(danach[0] - 0.1, goal_at + 7.0) if danach else min(goal_at + 5.0, dauer - 0.1)
        tore.append({'nr': len(tore) + 1, 'goal_at': goal_at, 'start': round(max(goal_at - 3.5, einst + 0.1, 0), 1),
                     'end': round(ende, 1), 'einstellung_ab': round(einst + 0.1, 1), 'prev_score': vorher,
                     'score': f'{h_}:{g_}', 'team': team, 'crop_x_rel': _seite(video, goal_at),
                     'hinweis': 'Anzeige war vorher ausgeblendet, Tor evtl. nicht im Video' if unsicher else ''})
    name = os.path.splitext(os.path.basename(video))[0]
    os.makedirs(f'04_Arbeitsdateien/{datum}', exist_ok=True)
    pfad = f'04_Arbeitsdateien/{datum}/{name}_torliste.json'
    json.dump({'source': video, 'dauer': dauer, 'tore': tore}, open(pfad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    zeilen = [f'Torliste {name}.mp4 (gemessen in Colab, Videolänge {mmss(dauer)})']
    for t in tore:
        zeilen.append(f"Tor {t['nr']}: goal_at {t['goal_at']} s ({mmss(t['goal_at'])}) · Szene {t['start']}–{t['end']} s · "
                      f"{t['prev_score']} → {t['score']} ({t['team']}) · crop_x_rel {t['crop_x_rel']}"
                      + (f" · {t['hinweis']}" if t['hinweis'] else ''))
    zeilen += ['Spielstand gezählt ab 0:0. Torschützen und Minuten bitte aus dem SRF-Ticker ergänzen.',
               'Szenen enden vor dem nächsten Schnitt im Video. Beim Prüfen der Spec verlängert die App den Anlauf automatisch, bis 30 s erreicht sind.']
    text = '\n'.join(zeilen)
    open(pfad.replace('.json', '.txt'), 'w', encoding='utf-8').write(text)
    bilder = []
    for t in tore:
        im = Image.fromarray(einzelbild(video, t['goal_at'] - 0.3))
        ImageDraw.Draw(im).rectangle(rahmen_tor(t['crop_x_rel']), outline=(255, 0, 80), width=4)
        bilder.append((im, f"Tor {t['nr']} · {t['prev_score']} → {t['score']} · {t['goal_at']} s"))
    return text, bilder


# ───────────────────────── Transkript ─────────────────────────
NOETIG = ['sherpa-onnx-whisper-turbo/turbo-encoder.int8.onnx', 'sherpa-onnx-whisper-turbo/turbo-decoder.int8.onnx',
          'sherpa-onnx-whisper-turbo/turbo-tokens.txt', 'silero_vad.onnx']
LOKAL = '/content/modelle' if os.path.isdir('/content') else '/tmp/mvc_modelle'


def _komplett(d):
    return os.path.exists(f'{d}/.fertig') and all(os.path.exists(f'{d}/{f}') for f in NOETIG)


def _modelle():
    subprocess.run('pip -q install sherpa-onnx', shell=True, check=True)
    if _komplett(LOKAL):
        return
    shutil.rmtree(LOKAL, ignore_errors=True)
    os.makedirs(LOKAL)
    rel = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models'
    r = subprocess.run(['bash', '-c', f'set -o pipefail; cd {LOKAL} && curl -fsSL {rel}/sherpa-onnx-whisper-turbo.tar.bz2 | tar xj '
                        f'--exclude="*/test_wavs*" && curl -fsSL -o silero_vad.onnx {rel}/silero_vad.onnx'])
    if r.returncode == 0 and all(os.path.exists(f'{LOKAL}/{f}') for f in NOETIG):
        open(f'{LOKAL}/.fertig', 'w').close()
    elif _komplett('_modelle'):
        shutil.rmtree(LOKAL, ignore_errors=True)
        shutil.copytree('_modelle', LOKAL)
    else:
        raise Hinweis('Spracherkennung konnte nicht geladen werden. Nochmals versuchen.')


def _wav(video, datum):
    wav = f"04_Arbeitsdateien/{datum}/audio/{os.path.splitext(os.path.basename(video))[0]}.wav"
    if not os.path.exists(wav):
        os.makedirs(os.path.dirname(wav), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
    return wav


def transkript(video, datum, sprache):
    _modelle()
    wav = _wav(video, datum)
    env = dict(os.environ, MODELLE=LOKAL, SPRACHE=sprache)
    r = subprocess.run(['python3', f'{V}/audio_tools.py', 'transcribe', wav], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise Hinweis('Transkription fehlgeschlagen: ' + r.stderr[-500:])
    txt = '\n'.join(l for l in r.stdout.splitlines() if not l.startswith('/project'))
    open(wav.replace('.wav', '_Transkript.txt'), 'w', encoding='utf-8').write(txt)
    pausen = subprocess.run(['python3', f'{V}/audio_tools.py', 'pauses', wav], capture_output=True, text=True, env=env).stdout
    return f'Transkript {os.path.basename(video)} (Zeiten in Sekunden)\n{txt}\n\nSprechpausen (für saubere Schnitte):\n{pausen}'


# ───────────────────────── Spec ─────────────────────────
ZEITFELDER = {'start', 'end', 'goal_at', 'src_s', 'src_e', 'bottom_still_at'}


def _sek(v):
    if isinstance(v, str) and ':' in v:
        m, s_ = v.strip().split(':')
        return round(int(m) * 60 + float(s_.replace(',', '.')), 2)
    if isinstance(v, str):
        return float(v.replace(',', '.'))
    return v


def _umrechnen(x, k=None):
    if isinstance(x, dict):
        return {a: (_sek(b) if a in ZEITFELDER else _umrechnen(b, a)) for a, b in x.items()}
    if isinstance(x, list):
        if k == 'segments' and x and isinstance(x[0], list):
            return [[_sek(a) for a in t] for t in x]
        return [_umrechnen(v, k) for v in x]
    return x


def spec_aus_text(text):
    """Sucht die Spec in der Gem-Antwort (auch mit ```json und Begleittext) und rechnet Zeiten in Sekunden um."""
    roh = (text or '').strip()
    if '{' not in roh or '}' not in roh:
        raise Hinweis('Keine Spec gefunden. Bitte den JSON-Codeblock vom Gem einfügen.')
    roh = roh[roh.index('{'):roh.rindex('}') + 1]
    try:
        spec = json.loads(roh)
    except json.JSONDecodeError as f:
        zeile = roh.splitlines()[f.lineno - 1] if f.lineno <= len(roh.splitlines()) else ''
        raise Hinweis(f'Die Spec ist kein gültiges JSON (Zeile {f.lineno}, Zeichen {f.colno}): …{zeile[max(0, f.colno - 40):f.colno + 40]}…')
    try:
        return _umrechnen(spec)
    except ValueError as f:
        raise Hinweis(f'Eine Zeitangabe ist nicht lesbar ({f}). Format: "1:39.5" oder 99.5.')


def format_von(spec):
    return 'Kombi Tore + Interview' if 'goals' in spec else ('Interview' if 'cues' in spec else 'Tore-Splitscreen')


def _teile(spec):
    return [spec['goals'], spec['interview']] if 'goals' in spec else [spec]


def pruefe(spec, datum):
    """Prüft Quellen und Zeiten, gleicht mit der Torliste ab und passt Szenen an. Gibt Protokoll-Zeilen zurück."""
    log = []
    if not [t.get('source') for t in _teile(spec) if t.get('source')]:
        raise Hinweis('In der Spec fehlt das Quellvideo ("source").')
    for t in _teile(spec):
        q = t.get('source')
        if not q:
            continue
        if not os.path.exists(q):
            raise Hinweis(f'Video «{q}» nicht gefunden.')
        d = laenge(q)
        for seg in t.get('segments', []):
            a, b = (seg['start'], seg['end']) if isinstance(seg, dict) else seg
            if b > d:
                raise Hinweis(f'Szene {a}–{b} s liegt ausserhalb des Videos (Länge {d:.1f} s).')
            if isinstance(seg, dict) and 'goal_at' in seg and not a <= seg['goal_at'] <= b:
                raise Hinweis(f'Tor bei {seg["goal_at"]} s liegt nicht in der Szene {a}–{b} s ({seg.get("sub", "")}).')
    for t in _teile(spec):
        if not t.get('source'):
            continue
        segs = [s for s in t.get('segments', []) if isinstance(s, dict) and 'goal_at' in s]
        if not segs:
            continue
        tl = f"04_Arbeitsdateien/{datum}/{os.path.splitext(os.path.basename(t['source']))[0]}_torliste.json"
        if not os.path.exists(tl):
            log.append('ℹ️ Keine Torliste gefunden. Tipp: zuerst «Tore finden» für dieses Video.')
            continue
        gem = json.load(open(tl, encoding='utf-8'))['tore']
        paar = []
        for s in segs:
            tor = min(gem, key=lambda x: abs(x['goal_at'] - s['goal_at']))
            if abs(tor['goal_at'] - s['goal_at']) > 2.0:
                raise Hinweis(f'Tor bei {s["goal_at"]} s ({s.get("sub", "")}) passt zu keinem gemessenen Tor. '
                              f'Laut Tor-Finder: {", ".join(str(x["goal_at"]) for x in gem)} s.')
            paar.append((s, tor))
        if spec.get('auto_schnitt', True) is False:
            continue
        for s, tor in paar:
            s['goal_at'], s['end'] = tor['goal_at'], tor['end']
        budget = 60.0 if spec.get('allow_over_30') else 29.5
        vor = [3.5] * len(paar)
        ober = [max(3.5, min(12.0, tor['goal_at'] - tor.get('einstellung_ab', 0))) for _, tor in paar]
        rest = budget - sum(s['end'] - s['goal_at'] for s, _ in paar) - sum(vor)
        if rest < 0:
            log.append(f'⚠️ Szenen zusammen {budget - rest:.1f} s, also über 30 s. Ein Tor weglassen oder kürzen.')
        plus = max(0.0, min(rest, ober[0] - vor[0]))
        vor[0] += plus
        rest -= plus
        while rest > 0.05:
            offen = [k for k in range(1, len(paar)) if vor[k] < ober[k] - 0.05]
            if not offen:
                break
            an = rest / len(offen)
            for k in offen:
                p = min(an, ober[k] - vor[k])
                vor[k] += p
                rest -= p
        for (s, _), v in zip(paar, vor):
            s['start'] = round(s['goal_at'] - v, 1)
        log.append('✂️ Szenen an die Schnitte im Video angepasst, Anlauf verlängert.')
    return log


def wortzeiten(teil, datum):
    """Untertitel src_s/src_e -> Clip-Zeiten und Wortzeiten. Rechnet neu, wenn ein Untertitel keine passenden Wortzeiten hat."""
    cues = teil.get('cues') or []
    if not cues or all('word_t' in c and len(c['word_t']) == len(c['text'].split()) for c in cues):
        return teil
    for c in cues:
        for k in ('s', 'e', 'word_t'):
            c.pop(k, None)
    subprocess.run('pip -q install sherpa-onnx', shell=True, check=True)
    wav = _wav(teil['source'], datum)
    tin, tout = '/tmp/mvc_cues_in.json', '/tmp/mvc_cues_out.json'
    json.dump(teil, open(tin, 'w', encoding='utf-8'), ensure_ascii=False)
    r = subprocess.run(['python3', f'{V}/audio_tools.py', 'wordtimes', wav, tin, tout], capture_output=True, text=True)
    if r.returncode != 0:
        raise Hinweis('Wortzeiten konnten nicht berechnet werden: ' + r.stderr[-400:])
    return json.load(open(tout, encoding='utf-8'))


def speichere(spec, datum, name):
    if 'interview' in spec:
        spec['interview'] = wortzeiten(spec['interview'], datum)
    elif 'cues' in spec:
        spec = wortzeiten(spec, datum)
    pfad = f'04_Arbeitsdateien/{datum}/{name}.json'
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    json.dump(spec, open(pfad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return spec, pfad


# ───────────────────────── Tabellen für den Feinschliff ─────────────────────────
TOR_SPALTEN = ['Start (s)', 'Tor bei (s)', 'Ende (s)', 'Stand vorher', 'Stand nachher', 'Torschütze', 'Ausschnitt 0–1']
INT_SPALTEN = ['Start (s)', 'Ende (s)']
UT_SPALTEN = ['Nr', 'Untertitel']


def tabellen(spec):
    f = format_von(spec)
    g = spec.get('goals', spec) if f != 'Interview' else {}
    i = spec.get('interview', spec) if f != 'Tore-Splitscreen' else {}
    tore = [[s['start'], s.get('goal_at', s['start']), s['end'], s.get('prev_score', ''), s.get('score', ''),
             s.get('sub', ''), s.get('crop_x_rel', 0.5)] for s in g.get('segments', []) if isinstance(s, dict)]
    teile = [[a, b] for a, b in i.get('segments', [])] if i else []
    ut = [[str(c.get('id', k)), c['text']] for k, c in enumerate(i.get('cues', []))] if i else []
    return tore, teile, ut, (i.get('tag', '') if i else ''), (spec.get('headline', []) + ['', ''])[:2]


def _zeilen(df):
    if df is None:
        return []
    if hasattr(df, 'values'):
        return [list(r) for r in df.values.tolist()]
    if isinstance(df, dict) and 'data' in df:
        return [list(r) for r in df['data']]
    return [list(r) for r in df]


def _leer(x):
    return x is None or (isinstance(x, str) and not x.strip()) or (isinstance(x, float) and x != x)


def aus_tabellen(spec, tore, teile, ut, tag, t1, t2):
    """Übernimmt die Werte aus dem Feinschliff in eine Kopie der Spec."""
    spec = json.loads(json.dumps(spec))
    if 'headline' in spec or t1 or t2:
        spec['headline'] = [x for x in ((t1 or '').strip(), (t2 or '').strip()) if x]
    f = format_von(spec)
    try:
        if f != 'Interview':
            g = spec.get('goals', spec)
            alt = [s for s in g.get('segments', []) if isinstance(s, dict)]
            neu = []
            for k, r in enumerate(_zeilen(tore)):
                if _leer(r[0]):
                    continue
                s = dict(alt[k]) if k < len(alt) else {}
                s.update(start=float(r[0]), goal_at=float(r[1]), end=float(r[2]), prev_score=str(r[3]), score=str(r[4]),
                         sub=str(r[5]), crop_x_rel=min(max(float(r[6]), 0.0), 1.0))
                neu.append(s)
            g['segments'] = neu
        if f != 'Tore-Splitscreen':
            i = spec.get('interview', spec)
            i['segments'] = [[float(a), float(b)] for a, b in _zeilen(teile) if not _leer(a)]
            if tag:
                i['tag'] = tag
            texte = {str(r[0]): str(r[1]) for r in _zeilen(ut)}
            for k, c in enumerate(i.get('cues', [])):
                c['text'] = texte.get(str(c.get('id', k)), c['text'])
    except (TypeError, ValueError) as e:
        raise Hinweis(f'In der Tabelle steht ein ungültiger Wert ({e}). Zeiten als Zahl in Sekunden, z. B. 96.1.')
    spec['auto_schnitt'] = False          # Handkorrektur nicht mehr automatisch überschreiben
    return spec


def vorschau(spec):
    bilder = []
    f = format_von(spec)
    if f != 'Interview':
        g = spec.get('goals', spec)
        for k, s in enumerate(x for x in g['segments'] if isinstance(x, dict)):
            for name, t in (('Start', s['start']), ('Tor', s.get('goal_at', s['start']) - 0.3), ('Ende', s['end'] - 0.2)):
                im = Image.fromarray(einzelbild(g['source'], t))
                ImageDraw.Draw(im).rectangle(rahmen_tor(s.get('crop_x_rel', 0.5)), outline=(255, 0, 80), width=4)
                bilder.append((im, f'Szene {k + 1} · {name} {t:.1f} s'))
    if f != 'Tore-Splitscreen':
        i = spec.get('interview', spec)
        cx = i.get('crop_x', i.get('face_x', 960) - 304)
        for k, (a, b) in enumerate(i['segments']):
            for name, t in (('Start', a), ('Ende', b - 0.2)):
                im = Image.fromarray(einzelbild(i['source'], t))
                ImageDraw.Draw(im).rectangle(rahmen_interview(cx), outline=(255, 0, 80), width=4)
                bilder.append((im, f'Interview-Teil {k + 1} · {name} {t:.1f} s'))
    return bilder


def gesamtlaenge(spec):
    s = 0.0
    for t in _teile(spec):
        for seg in t.get('segments', []):
            a, b = (seg['start'], seg['end']) if isinstance(seg, dict) else seg
            s += b - a
    return s


# ───────────────────────── Rendern ─────────────────────────
def rendere(spec_pfad, datum, ausgabe, fmt=None):
    spec = json.load(open(spec_pfad, encoding='utf-8'))
    skript, ordner = FORMATE[fmt or format_von(spec)]
    ausgabe = os.path.splitext(os.path.basename((ausgabe or '').strip()))[0] or 'reel'
    ziel = f'05_Ausgabe/{datum}/{ordner}/{ausgabe}.mp4'
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    r = subprocess.run(['python3', f'{V}/{skript}', spec_pfad, ziel], capture_output=True, text=True)
    if r.returncode != 0:
        raise Hinweis('Rendern fehlgeschlagen: ' + (r.stderr or r.stdout)[-800:])
    return ziel, r.stdout.strip()


def ausgabe_vorschlag(spec, name):
    q = os.path.splitext(os.path.basename(_teile(spec)[0].get('source', '')))[0].replace('_INTERVIEWS', '').replace('_Interviews', '')
    teile = q.split('_')
    sprache = teile[-1] if teile and teile[-1] in ('DE', 'FR', 'IT') else 'DE'
    spiel = '_'.join(x for x in teile if x not in ('DE', 'FR', 'IT'))
    datum = spiel[:6]
    rest = spiel[7:]
    art = {'Tore-Splitscreen': 'Tore_Split', 'Interview': 'Interview', 'Kombi Tore + Interview': 'Kombi'}[format_von(spec)]
    version = name.split('_')[-1] if re.match(r'v\d+$', name.split('_')[-1]) else 'v1'
    return f'{datum}_{sprache}_{rest}_{art}_{version}'


# ───────────────────────── Oberfläche ─────────────────────────
def _textbox_kopierbar(gr, **kw):
    """Textfeld mit Kopier-Knopf (Gradio 4/5: show_copy_button, Gradio 6: buttons)."""
    try:
        return gr.Textbox(buttons=['copy'], **kw)
    except TypeError:
        return gr.Textbox(show_copy_button=True, **kw)


def app():
    import gradio as gr

    def fehler(f):
        raise gr.Error(str(f), duration=None)

    with gr.Blocks(title='mySports Video Creator', theme=gr.themes.Soft(primary_hue='red')) as demo:
        gr.Markdown('# 🏒 mySports Video Creator\n'
                    '**① Tore finden** (bzw. Transkript) → Liste in den Gem kopieren → **② Spec vom Gem** einfügen → **③ Feinschliff & Rendern**')
        spec_state, pfad_state = gr.State({}), gr.State('')

        with gr.Tab('① Tore finden'):
            gr.Markdown('Für **Tore-Reels**. Misst im Video, wann der Spielstand umspringt (ca. 1 Minute). Die Torliste danach in den Gem kopieren.')
            with gr.Row():
                v1 = gr.Dropdown(videos(), label='Video aus Originalvideos', scale=4)
                n1 = gr.Button('↻ Liste neu laden', scale=1)
            b1 = gr.Button('Tore finden', variant='primary')
            o1 = _textbox_kopierbar(gr, label='Torliste (für den Gem)', lines=8)
            g1 = gr.Gallery(label='Moment des Tors · roter Rahmen = Ausschnitt im Reel', columns=3, height='auto')

        with gr.Tab('① Interview-Transkript'):
            gr.Markdown('Für **Interview- und Kombi-Reels**. Das Transkript danach in den Gem kopieren. Beim ersten Mal pro Sitzung ca. 1–2 Minuten.')
            with gr.Row():
                v2 = gr.Dropdown(videos(), label='Interview-Video', scale=4)
                s2 = gr.Dropdown(['de', 'fr', 'en', 'it'], value='de', label='Sprache', scale=1)
                n2 = gr.Button('↻', scale=0)
            b2 = gr.Button('Transkribieren', variant='primary')
            o2 = _textbox_kopierbar(gr, label='Transkript (für den Gem)', lines=14)

        with gr.Tab('② Spec vom Gem'):
            gr.Markdown('Die **ganze Antwort des Gems** einfügen. Die App sucht die Spec heraus, prüft sie und passt die Szenen an die Schnitte im Video an.')
            t3 = gr.Textbox(label='Antwort bzw. Spec vom Gem', lines=12, placeholder='{ "source": "Originalvideos/…", … }')
            with gr.Row():
                d3 = gr.Textbox(label='Datum (JJMMTT) – leer = aus dem Videonamen')
                m3 = gr.Textbox(label='Name der Spec – z. B. gshc_split_v1')
            b3 = gr.Button('Prüfen und speichern', variant='primary')
            o3 = gr.Markdown()

        with gr.Tab('③ Feinschliff & Rendern'):
            with gr.Row():
                l4 = gr.Dropdown(specs(), label='Gespeicherte Spec (Datum/Name)', scale=4)
                n4 = gr.Button('↻', scale=0)
                b4l = gr.Button('Laden', scale=1)
            info4 = gr.Markdown()
            with gr.Row():
                tt1 = gr.Textbox(label='Titel Zeile 1')
                tt2 = gr.Textbox(label='Titel Zeile 2')
            tor4 = gr.Dataframe(headers=TOR_SPALTEN, datatype=['number'] * 3 + ['str'] * 3 + ['number'], interactive=True,
                                label='Tor-Szenen (Zeiten in Sekunden ab Videobeginn; Ausschnitt 0 = links, 1 = rechts)',
                                col_count=(7, 'fixed'))
            tag4 = gr.Textbox(label='Name über den Untertiteln (nur Interview / Kombi)')
            teil4 = gr.Dataframe(headers=INT_SPALTEN, datatype=['number', 'number'], interactive=True,
                                 label='Interview-Teile (Sekunden)', col_count=(2, 'fixed'))
            ut4 = gr.Dataframe(headers=UT_SPALTEN, datatype=['str', 'str'], interactive=True,
                               label='Untertitel (nur den Text ändern)', col_count=(2, 'fixed'))
            with gr.Row():
                bv = gr.Button('🖼 Vorschau-Bilder')
                bs = gr.Button('💾 Änderungen speichern')
            g4 = gr.Gallery(label='Start / Tor / Ende je Szene · roter Rahmen = Ausschnitt im Reel', columns=3, height='auto')
            with gr.Row():
                a4 = gr.Textbox(label='Dateiname des Videos', scale=4)
                br = gr.Button('🎬 Rendern (ca. 2–3 Min.)', variant='primary', scale=1)
            o4 = gr.Markdown()
            vid4 = gr.Video(label='Ergebnis', height=520)
            dl4 = gr.File(label='Download')

        ausgaben = [spec_state, pfad_state, info4, tt1, tt2, tor4, tag4, teil4, ut4, a4, l4]
        felder = [spec_state, pfad_state, tt1, tt2, tor4, tag4, teil4, ut4]

        def fuellen(spec, pfad, meldung):
            tore, teile, ut, tag, (h1, h2) = tabellen(spec)
            datum = os.path.basename(os.path.dirname(pfad))
            name = os.path.splitext(os.path.basename(pfad))[0]
            laenge_ = gesamtlaenge(spec)
            txt = (f"{meldung}\n\n**{format_von(spec)}** · Spec `{datum}/{name}` · Gesamtlänge Quelle **{laenge_:.1f} s**"
                   + (' ⚠️ über 30 s' if laenge_ > 30.05 and not spec.get('allow_over_30') else ''))
            return (spec, pfad, txt, h1, h2, tore or None, tag, teile or None, ut or None, ausgabe_vorschlag(spec, name),
                    gr.update(choices=specs(), value=f'{datum}/{name}.json'))

        def los1(v):
            if not v:
                fehler('Bitte zuerst ein Video wählen.')
            try:
                return finde_tore(f'Originalvideos/{v}', datum_aus(v))
            except Hinweis as f:
                fehler(f)

        def los2(v, s):
            if not v:
                fehler('Bitte zuerst ein Video wählen.')
            try:
                return transkript(f'Originalvideos/{v}', datum_aus(v), s)
            except Hinweis as f:
                fehler(f)

        def los3(text, datum, name):
            try:
                spec = spec_aus_text(text)
                datum = (datum or '').strip() or datum_aus(_teile(spec)[0].get('source', ''))
                name = re.sub(r'[^A-Za-z0-9_-]+', '_', (name or '').strip()) or f"{format_von(spec).split()[0].lower()}_v1"
                log = pruefe(spec, datum)
                spec, pfad = speichere(spec, datum, name)
            except Hinweis as f:
                fehler(f)
            meldung = '✅ Gespeichert. Weiter im Tab **③ Feinschliff & Rendern**.' + ''.join('  \n' + x for x in log)
            return (meldung,) + fuellen(spec, pfad, meldung)

        def laden(wahl):
            if not wahl:
                fehler('Bitte eine Spec wählen.')
            pfad = f'04_Arbeitsdateien/{wahl}'
            return fuellen(json.load(open(pfad, encoding='utf-8')), pfad, '📂 Geladen.')

        def sammeln(spec, pfad, h1, h2, tore, tag, teile, ut):
            if not pfad:
                fehler('Zuerst eine Spec prüfen (Tab ②) oder hier laden.')
            try:
                return aus_tabellen(spec, tore, teile, ut, tag, h1, h2)
            except Hinweis as f:
                fehler(f)

        def bilder(*werte):
            return vorschau(sammeln(*werte))

        def sichern(*werte):
            neu = sammeln(*werte)
            pfad = werte[1]
            try:
                neu, pfad = speichere(neu, os.path.basename(os.path.dirname(pfad)), os.path.splitext(os.path.basename(pfad))[0])
            except Hinweis as f:
                fehler(f)
            return fuellen(neu, pfad, '💾 Änderungen gespeichert.')

        def render(*werte):
            *felder_, ausgabe = werte
            neu = sammeln(*felder_)
            pfad = felder_[1]
            datum = os.path.basename(os.path.dirname(pfad))
            try:
                neu, pfad = speichere(neu, datum, os.path.splitext(os.path.basename(pfad))[0])
                if gesamtlaenge(neu) > 30.05 and not neu.get('allow_over_30'):
                    raise Hinweis(f'Die Szenen sind zusammen {gesamtlaenge(neu):.1f} s lang. Erlaubt sind höchstens 30 s pro Quelldatei.')
                ziel, log = rendere(pfad, datum, ausgabe)
            except Hinweis as f:
                fehler(f)
            return f'✅ Fertig: `{ziel}` (liegt im Drive)  \n{log}', ziel, ziel

        n1.click(lambda: gr.update(choices=videos()), None, v1)
        n2.click(lambda: gr.update(choices=videos()), None, v2)
        n4.click(lambda: gr.update(choices=specs()), None, l4)
        b1.click(los1, v1, [o1, g1])
        b2.click(los2, [v2, s2], o2)
        b3.click(los3, [t3, d3, m3], [o3] + ausgaben)
        b4l.click(laden, l4, ausgaben)
        bv.click(bilder, felder, g4)
        bs.click(sichern, felder, ausgaben)
        br.click(render, felder + [a4], [o4, vid4, dl4])
    return demo


def start(projekt=None, port=7860):
    """Im Projektordner starten und die App in Colab anzeigen (nur für die angemeldete Person erreichbar)."""
    if projekt:
        os.chdir(projekt)
    demo = app()
    kw = dict(server_port=port, share=False, inline=False, prevent_thread_lock=True, quiet=True, allowed_paths=[os.getcwd()])
    try:
        demo.queue().launch(show_api=False, **kw)
    except TypeError:
        demo.queue().launch(**kw)
    try:
        from google.colab import output
        output.serve_kernel_port_as_window(port, anchor_text='👉 mySports Video Creator in neuem Tab öffnen')
        output.serve_kernel_port_as_iframe(port, height=1200)
    except ImportError:
        print(f'App läuft auf http://127.0.0.1:{port}')
    return demo
