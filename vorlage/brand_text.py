"""mySports-Gestaltung (Organic, 9:16, 1080x1920) als transparente PNGs.

Vorgaben «mySports Social Media Designvorlagen» (Stand Oktober 2026):
- Farben: Sunrise Red #DA291C (Titelbox, Scorebar, Trennlinie), Kicker-Text #CA291C, Ice White #FFFFFF,
  Schwarz #000000 nur für Interview-Untertitel und den Verlauf unten. Alle Boxen in Vollfarbe (100 %).
- Schrift Figtree: Titel Bold 76 (rote Box), Kicker Bold 46 #CA291C (weisse Box), Resultat ExtraBold 84
  Laufweite -25 (weisse Box), Teams Bold 54 (rote Box), Torschütze Bold 46 (rote Box, 69 hoch),
  Untertitel Regular 44 (schwarze Box, 69 hoch).
- Safe Zone Reels Organic: oben 252, seitlich 94, unten 465 px. Logo darf ausserhalb liegen (unten zentriert).
- Splitscreen: zwei Clips je 1080x957, Trennlinie 6 px (y 957–963), Scorebar auf der Linie mit dem Resultat
  exakt auf x 540, Torschütze 10 px darunter. Titel (Kicker + Titel) ab x 125 / y 252.
- Interview (PSD): Bauchbinde ab x 86 / y 952 (weiss: Club, rot: Vor- und Nachname), Untertitel ab x 86 / y 1176,
  max. 3 Zeilen, 10 px Abstand, kein Text über dem Gesicht.
"""
from PIL import Image, ImageDraw, ImageFont
import os

BRAND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '03_Brand')
FONT_BOLD = os.path.join(BRAND, 'Figtree-Bold.ttf')
FONT_EXTRABOLD = os.path.join(BRAND, 'Figtree-ExtraBold.ttf')
FONT_REGULAR = os.path.join(BRAND, 'Figtree-Regular.ttf')

RED = (0xDA, 0x29, 0x1C, 255)          # Sunrise Red, Vollfarbe
KICKER_RED = (0xCA, 0x29, 0x1C, 255)   # Kicker-Text gemäss PSD
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
W, H = 1080, 1920
SAFE_TOP, SAFE_SIDE, SAFE_BOTTOM = 252, 94, 465
RADIUS = 14

# Splitscreen
CLIP_H = 957                        # Höhe je Clip
LINE_Y, LINE_H = 957, 6             # Trennlinie y 957–963
SEAM_MID = LINE_Y + LINE_H // 2     # 960
# Titelblock
TITLE_X, TITLE_Y = 125, 252
TITLE_SIZE, TITLE_BOX, TITLE_PADX = 76, 113, 26
KICKER_SIZE, KICKER_BOX, KICKER_PADX = 46, 69, 18
BLOCK_GAP = 8
# Scorebar
SCORE_SIZE, SCORE_TRACK, TEAM_SIZE, BAR_H = 84, -25, 54, 112
SCORE_PADX, TEAM_PADX = 26, 26
SCORER_SIZE, SCORER_BOX, SCORER_PADX, SCORER_GAP = 46, 69, 18, 10
# Interview
LOWER_X, LOWER_Y = 86, 952          # Bauchbinde
SUB_X, SUB_Y = 86, 1176             # Untertitel
SUB_SIZE, SUB_BOX, SUB_PADX, SUB_GAP, SUB_MAX_LINES = 44, 69, 18, 10, 3
SUB_MAXW = W - SAFE_SIDE - SUB_X    # bis an den rechten Rand der Safe Zone


def font(path, size):
    return ImageFont.truetype(path, size)


def leer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def _cap(f):
    """Höhe der Grossbuchstaben – für optisch zentrierten Text in den Boxen."""
    b = f.getbbox('H', anchor='ls')
    return -b[1]


def textbreite(text, f, track=0):
    if not track:
        return f.getlength(text)
    sp = f.size * track / 1000
    return sum(f.getlength(c) for c in text) + sp * (len(text) - 1)


def text_in_box(d, x, y, w, boxh, text, f, fg, track=0, mitte=True):
    """Text vertikal (Versalhöhe) und optional horizontal zentriert in die Box schreiben."""
    tw = textbreite(text, f, track)
    tx = x + (w - tw) / 2 if mitte else x
    base = y + boxh / 2 + _cap(f) / 2
    if not track:
        d.text((tx, base), text, font=f, fill=fg, anchor='ls')
        return
    sp = f.size * track / 1000
    for c in text:
        d.text((tx, base), c, font=f, fill=fg, anchor='ls')
        tx += f.getlength(c) + sp


def box(d, x, y, text, f, boxh, padx, bg, fg, ecken=(True, True, True, True), track=0):
    w = int(round(textbreite(text, f, track) + 2 * padx))
    d.rounded_rectangle([x, y, x + w, y + boxh], radius=RADIUS, fill=bg, corners=ecken)
    text_in_box(d, x, y, w, boxh, text, f, fg, track)
    return w


def umbrechen(text, f, maxw):
    zeilen, akt = [], ''
    for wort in text.split():
        t = (akt + ' ' + wort).strip()
        if f.getlength(t) <= maxw or not akt:
            akt = t
        else:
            zeilen.append(akt); akt = wort
    zeilen.append(akt)
    return zeilen


# ───────────── Titelblock: Kicker (weiss) + Titel (rot) ─────────────
def titelblock(zeilen, x=TITLE_X, y=TITLE_Y):
    """zeilen = [Kicker, Titel] oder [Titel]. Kicker gibt den Kontext, Titel erzählt die Szene."""
    img = leer(); d = ImageDraw.Draw(img)
    zeilen = [z for z in zeilen if z]
    if not zeilen:
        return img
    kicker, titel = (zeilen[0], ' '.join(zeilen[1:])) if len(zeilen) > 1 else (None, zeilen[0])
    if kicker:
        box(d, x, y, kicker, font(FONT_BOLD, KICKER_SIZE), KICKER_BOX, KICKER_PADX, WHITE, KICKER_RED)
        y += KICKER_BOX + BLOCK_GAP
    ft = font(FONT_BOLD, TITLE_SIZE)
    for z in umbrechen(titel, ft, W - SAFE_SIDE - x - 2 * TITLE_PADX):
        box(d, x, y, z, ft, TITLE_BOX, TITLE_PADX, RED, WHITE)
        y += TITLE_BOX + BLOCK_GAP
    return img


# ───────────── Scorebar: Home | Resultat | Away ─────────────
def scorebar(home, resultat, away, mitte_y=SEAM_MID, mit_torschuetze=None):
    """Resultat (weiss) exakt auf x 540, Home links und Away rechts direkt daran, nur Aussenecken gerundet.
    Optional Torschütze zentriert 10 px darunter."""
    img = leer(); d = ImageDraw.Draw(img)
    fs, ft = font(FONT_EXTRABOLD, SCORE_SIZE), font(FONT_BOLD, TEAM_SIZE)
    sw = int(round(textbreite(resultat, fs, SCORE_TRACK) + 2 * SCORE_PADX))
    hw = int(round(ft.getlength(home) + 2 * TEAM_PADX))
    aw = int(round(ft.getlength(away) + 2 * TEAM_PADX))
    y = int(mitte_y - BAR_H / 2)
    sx = W // 2 - sw // 2
    d.rounded_rectangle([sx - hw, y, sx, y + BAR_H], radius=RADIUS, fill=RED, corners=(True, False, False, True))
    d.rounded_rectangle([sx + sw, y, sx + sw + aw, y + BAR_H], radius=RADIUS, fill=RED, corners=(False, True, True, False))
    d.rectangle([sx, y, sx + sw, y + BAR_H], fill=WHITE)
    text_in_box(d, sx - hw, y, hw, BAR_H, home, ft, WHITE)
    text_in_box(d, sx + sw, y, aw, BAR_H, away, ft, WHITE)
    text_in_box(d, sx, y, sw, BAR_H, resultat, fs, RED, track=SCORE_TRACK)
    if mit_torschuetze:
        torschuetze(mit_torschuetze, y + BAR_H + SCORER_GAP, d)
    return img


def torschuetze(text, y, d=None):
    img = None
    if d is None:
        img = leer(); d = ImageDraw.Draw(img)
    f = font(FONT_BOLD, SCORER_SIZE)
    w = int(round(f.getlength(text) + 2 * SCORER_PADX))
    box(d, W // 2 - w // 2, y, text, f, SCORER_BOX, SCORER_PADX, RED, WHITE)
    return img


def torschuetze_y(mitte_y=SEAM_MID):
    return int(mitte_y - BAR_H / 2) + BAR_H + SCORER_GAP


# ───────────── Interview: Bauchbinde + Untertitel ─────────────
def name_club(tag, name=None, club=None):
    """«Vorname Nachname, Club» -> (Name, Club)."""
    if name or club:
        return name or '', club or ''
    teile = [t.strip() for t in (tag or '').split(',', 1)]
    return teile[0], (teile[1] if len(teile) > 1 else '')


def _kurzname(name, f, maxw):
    """Bei langen Namen den Vornamen abkürzen (Jonah Neuenschwander -> J. Neuenschwander)."""
    if f.getlength(name) <= maxw:
        return name
    t = name.split()
    return (t[0][0] + '. ' + ' '.join(t[1:])) if len(t) > 1 else name


def bauchbinde(name, club, x=LOWER_X, y=LOWER_Y):
    """Weisse Box mit Club, darunter rote Box mit Vor- und Nachname. Während des ganzen Clips sichtbar."""
    img = leer(); d = ImageDraw.Draw(img)
    if club:
        box(d, x, y, club, font(FONT_BOLD, KICKER_SIZE), KICKER_BOX, KICKER_PADX, WHITE, KICKER_RED)
        y += KICKER_BOX + BLOCK_GAP
    fn = font(FONT_BOLD, TITLE_SIZE)
    if name:
        box(d, x, y, _kurzname(name, fn, W - SAFE_SIDE - x - 2 * TITLE_PADX), fn, TITLE_BOX, TITLE_PADX, RED, WHITE)
    return img


def bauchbinde_hoehe(club=True):
    return (KICKER_BOX + BLOCK_GAP if club else 0) + TITLE_BOX


def untertitel_zeilen(text):
    return umbrechen(text, font(FONT_REGULAR, SUB_SIZE), SUB_MAXW - 2 * SUB_PADX)


def untertitel_zustaende(text, x=SUB_X, y=SUB_Y):
    """PNG pro Wort: Untertitel bauen sich Wort für Wort auf, jede Zeile in einer eigenen schwarzen Box."""
    f = font(FONT_REGULAR, SUB_SIZE)
    zeilen = untertitel_zeilen(text)
    if len(zeilen) > SUB_MAX_LINES:
        print(f'⚠️  Untertitel hat {len(zeilen)} Zeilen (max. {SUB_MAX_LINES}): «{text[:60]}…» – besser aufteilen')
    woerter = [z.split() for z in zeilen]
    zust = []
    for zi, ws in enumerate(woerter):
        for wi in range(len(ws)):
            sichtbar = [' '.join(woerter[j]) for j in range(zi)] + [' '.join(ws[:wi + 1])]
            img = leer(); d = ImageDraw.Draw(img)
            for k, z in enumerate(sichtbar):
                box(d, x, y + k * (SUB_BOX + SUB_GAP), z, f, SUB_BOX, SUB_PADX, BLACK, WHITE)
            zust.append(img)
    return zust


def verlauf_unten(start=1350, staerke=0.55):
    """Schwarzer Verlauf unten (für Lesbarkeit von Untertiteln und Logo im Interview)."""
    img = leer(); px = img.load()
    for y in range(start, H):
        a = int(255 * staerke * ((y - start) / (H - start)) ** 1.2)
        for x in range(W):
            px[x, y] = (0, 0, 0, a)
    return img
