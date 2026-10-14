# Design mySports Reels (gültig ab 14.10.2026)

Quelle: «Organic – mySports Social Media Designvorlagen» (PSD). Gilt für alle Formate (Interview, Tore-Splitscreen, Kombi).
Umgesetzt in `vorlage/brand_text.py`; die Render-Skripte holen alle Masse von dort.

## Farben (immer Vollfarbe, keine Deckkraft)
- Sunrise Red #DA291C: Titelbox, Scorebar (Teams), Torschütze, Trennlinie, Namensbox Bauchbinde
- Kicker-Text #CA291C (gemäss PSD)
- Ice White #FFFFFF: Kicker-Box, Resultat-Box, Club-Box der Bauchbinde, Text auf Rot und Schwarz
- Schwarz #000000: nur Interview-Untertitel (zusammen mit der Bauchbinde) und Verlauf unten.
  Schwarze Boxen nie als dritte Hierarchiestufe für andere Infos verwenden.

## Typografie (Figtree)
| Element | Schnitt | Grösse | Farbe |
|---|---|---|---|
| Titel (rote Box) | Bold | 76 px | weiss |
| Kicker (weisse Box) | Bold | 46 px | #CA291C |
| Scorebar Resultat (weisse Box) | ExtraBold | 84 px, Laufweite −25 | rot |
| Scorebar Teams (rote Box) | Bold | 54 px | weiss |
| Torschütze (rote Box) | Bold | 46 px, Box 69 px hoch | weiss |
| Bauchbinde Name (rote Box) / Club (weisse Box) | Bold | 76 / 46 px | weiss / rot |
| Untertitel (schwarze Box) | Regular | 44 px, Box 69 px hoch | weiss |

## Safe Zone 9:16 Organic (Reels)
Oben 252 px, seitlich je 94 px, unten 465 px. Alle Elemente liegen darin.
Ausnahme: mySports-Logo, unten zentriert, darf ausserhalb liegen.

## Tore-Splitscreen
- Zwei Clips übereinander, je 1080 × 957 px
- Trennlinie Sunrise Red, 6 px, y 957–963
- Scorebar auf der Linie: **das Resultat** steht exakt auf x 540, Home links und Away rechts direkt daran.
  Lange Clubnamen verlängern die Scorebar nur nach links bzw. rechts. Aussenecken 14 px gerundet.
- Torschütze zentriert auf x 540, 10 px unter der Scorebar: Minute, Initial + Name, Situation,
  z. B. «46' A. Honka (PP)», «32' D. Lammer (EN)»
- Titel oben bei x 125 / y 252: Kicker gibt den Kontext («1:3 hinten.»), Titel erzählt die Szene («Dann kam Honka.»).
  In der Spec: `"headline": ["Kicker", "Titel"]`. Kurz halten, beide Zeilen müssen in die Safe Zone passen.

## Interview
- Bauchbinde ab x 86 / y 952: weisse Box Club (z. B. «HC Davos»), rote Box Vor- und Nachname. Während des ganzen Clips sichtbar.
  In der Spec: `"tag": "Vorname Nachname, Club"`. Bei langen Namen wird der Vorname abgekürzt.
- Untertitel ab x 86 / y 1176: schwarze Boxen 100 %, je Zeile eine Box, 10 px Abstand, max. 3 Zeilen.
  Lieber mehrere kurze Zeilen als eine lange. Kein Text über dem Gesicht.
- Positionen wie in der PSD: nicht verschieben, nicht skalieren.
- Unten ein schwarzer Verlauf (ab y 1350) für die Lesbarkeit.
