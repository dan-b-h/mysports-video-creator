# mySports Video Creator

Vorlagen von Brain & Heart, mit denen Hockey-Reels für mySports im freigegebenen Design geschnitten werden (9:16, Figtree, Sunrise Red #DA291C in Vollfarbe). Die Gestaltung richtet sich nach der PSD-Vorlage «Organic – mySports Social Media Designvorlagen», Details in `vorlage/DESIGN.md`.

[![In Colab öffnen](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dan-b-h/mysports-video-creator/blob/main/notebook/mySports_Video_Creator.ipynb)

## Was hier liegt
- `notebook/mySports_Video_Creator.ipynb` – Colab-Notebook: sichten, transkribieren, Spec speichern, rendern
- `vorlage/` – Render-Skripte
  - `render_goals_split.py` – Tore im Splitscreen, Spielstand auf der Mittellinie
  - `render_interview.py` – Interview im Hochformat mit Untertiteln Wort für Wort
  - `render_combo.py` – zuerst Tore (unten), dann Interview (oben)
  - `brand_text.py` – Textelemente im mySports-Design (alle Masse, Farben und Schriften an einem Ort)
  - `DESIGN.md` – Designregeln: Farben, Typografie, Safe Zone, Scorebar, Bauchbinde, Untertitel
  - `audio_tools.py` – Transkription, Sprechpausen, Wortzeiten
  - `mvc_app.py` – App-Oberfläche (Tore finden, Transkript, Spec prüfen, Feinschliff, Rendern)
- `beispiele/` – freigegebene Specs als Vorlage

## Was nicht hier liegt
Videos, Logo, Schriften, Kader- und Protokolldaten liegen im internen Google Drive (Projektordner «mySports - SOM Organic - Video Creator»). Das Notebook verbindet beides.

Clubnamen (DE/FR/IT, kurz und lang) stehen in `02_Daten/clubnamen.csv` im Drive, aktueller Stand 21.10.2026. Im Video, auf der Scorebar und in der Caption immer «Name kurz» der jeweiligen Sprache verwenden.

## Design in Kürze (seit 14.10.2026)
- **Safe Zone 9:16 Organic:** oben 252 px, seitlich 94 px, unten 465 px. Nur das mySports-Logo darf ausserhalb liegen.
- **Splitscreen:** Scorebar auf der roten Mittellinie, das Resultat steht immer exakt in der Bildmitte. Torschütze darunter, z. B. «55' J. Henry» oder «46' A. Honka (PP)».
- **Titel:** `"headline": ["Kicker", "Titel"]`. Der Kicker gibt den Kontext («Befreiungsschlag.»), der Titel erzählt die Szene («Kloten dreht die Partie.»). Beide kurz halten, damit sie auf je eine Zeile passen. Empfohlen: `"headline_dur": 1.5` (Titel 1,5 s sichtbar).
- **Interview:** Bauchbinde mit Club (weisse Box) und Name (rote Box), Spec-Feld `"tag": "Vorname Nachname, Club"`. Untertitel in schwarzen Boxen, höchstens 3 Zeilen.
- DE und FR bekommen eigene Kicker und Titel, nicht wörtlich übersetzt. Für FR lohnt sich ein Bezug zur Westschweiz (z. B. «Pas de doublé pour Lausanne.»).

## Einmalig einrichten
Damit Colab den Projektordner findet, braucht jede Person eine Verknüpfung in «Meine Ablage»:
im Google Drive den Ordner «mySports - SOM Organic - Video Creator» öffnen, oben auf den Ordnernamen klicken,
«Organisieren» → «Verknüpfung hinzufügen» → «Meine Ablage» wählen.

## Ablauf in Kürze
1. Notebook über den Button oben öffnen, **Abschnitt 1** ausführen (Drive verbinden), dann **🚀 App starten**.
2. In der App: **Tore finden** (Tore-Reels) bzw. **Interview-Transkript** (Interview-/Kombi-Reels).
3. Torliste bzw. Transkript in den Gemini-Gem «mySports Video Creator» kopieren; er liefert Spec und Caption.
4. In der App: **Spec vom Gem** einfügen → **Feinschliff** (Namen, Zeiten, Ausschnitt) → **Rendern**.
5. Video prüfen, Caption mit Collab-Vorschlag (z. B. DE @ehc_kloten_1934, FR @lausannehc_officiel) ergänzen und die Kundin um Freigabe bitten: Inhalt kurz beschreiben, Torschützen/Minuten und Caption-Fakten zur Prüfung auflisten, Ausnahmen bei der 30-Sekunden-Regel offenlegen.
6. Colab beim Schliessen **nicht speichern**.

Dateinamen: Originalvideos z. B. `261020_EHCK_LHC_ONLINE_DE.mp4`; Ausgabe `<JJMMTT>_<DE|FR>_<HEIM>_<GAST>_Tore_Split_vX.mp4` plus `..._Tore_Caption.txt`.

Regel: pro Quelldatei höchstens 30 Sekunden Material, ausser mit ausdrücklicher Freigabe.
