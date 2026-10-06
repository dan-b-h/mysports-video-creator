"""mySports-Textelemente als transparente 1080x1920-PNGs.
Vorgaben: Figtree, Sunrise Red #DA291C 80 %, Radius 15, Abstand 4 px,
Untertitel links mind. 134 px, Unterkante 465 px über dem Bildrand."""
from PIL import Image, ImageDraw, ImageFont
import os
BRAND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '03_Brand')
FONT_SUB = os.path.join(BRAND, 'Figtree-Bold.ttf')   # Standard ab 01.10.2026 (vorher Medium + 1 px Kontur)
FONT_NAME = os.path.join(BRAND, 'Figtree-ExtraBold.ttf')
FONT_LIGHT = os.path.join(BRAND, 'Figtree-Regular.ttf')
RED = (0xDA, 0x29, 0x1C, int(255 * 0.8))
RED_SOLID = (0xDA, 0x29, 0x1C, 255)
WHITE = (255, 255, 255, 255)
W, H = 1080, 1920
SIDE, BOTTOM, GAP, RADIUS, PADX = 134, 465, 4, 15, 18
SUB_SIZE, NAME_SIZE, NAME_GAP = 52, 52, 16
SUB_BOTTOM = H - BOTTOM

def bold(font):
    """Nur noch für alte Specs mit Figtree Medium: 1 px Kontur. Standard ist Figtree Bold ohne Kontur."""
    return {'stroke_width': 1, 'stroke_fill': None} if 'Medium' in getattr(font, 'path', '') else {}

def wrap(text, font, maxw):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if font.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines

def draw_lines(img, lines, font, x, y0, boxh, bg, fg):
    d = ImageDraw.Draw(img)
    asc, desc = font.getmetrics()
    for i, l in enumerate(lines):
        if not l:
            continue
        y = y0 + i * (boxh + GAP)
        w = int(font.getlength(l)) + 2 * PADX
        d.rounded_rectangle([x, y, x + w, y + boxh], radius=RADIUS, fill=bg)
        d.text((x + PADX, y + (boxh - (asc + desc)) // 2), l, font=font, fill=fg, **bold(font))

def sub_lines(text):
    font = ImageFont.truetype(FONT_SUB, SUB_SIZE)
    return wrap(text, font, W - 2 * SIDE - 2 * PADX)

def block_height(n, size):
    boxh = int(size * 1.3)
    return n * boxh + (n - 1) * GAP

def layout(texts):
    """Feste Positionen: Spielername oben, Untertitel darunter; Unterkante des höchsten Blocks bei 1455."""
    maxn = max(len(sub_lines(t)) for t in texts)
    sub_top = SUB_BOTTOM - block_height(maxn, SUB_SIZE)
    name_top = sub_top - NAME_GAP - int(NAME_SIZE * 1.3)
    return sub_top, name_top

def subtitle_states(text, y0):
    """Liefert eine Liste von PNG-Bildern: Wort für Wort aufgebaut, Zeilen fest positioniert."""
    font = ImageFont.truetype(FONT_SUB, SUB_SIZE)
    lines = sub_lines(text)
    boxh = int(SUB_SIZE * 1.3)
    words_per_line = [l.split() for l in lines]
    states, shown = [], []
    for li, ws in enumerate(words_per_line):
        for wi in range(len(ws)):
            partial = [' '.join(words_per_line[j]) for j in range(li)] + [' '.join(ws[:wi + 1])]
            partial += [''] * (len(lines) - len(partial))
            img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            draw_lines(img, partial, font, SIDE, y0, boxh, RED, WHITE)
            states.append(img)
    return states

def name_tag(text, y):
    font = ImageFont.truetype(FONT_NAME, NAME_SIZE)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_lines(img, [text], font, SIDE, y, int(NAME_SIZE * 1.3), WHITE, RED_SOLID)
    return img
