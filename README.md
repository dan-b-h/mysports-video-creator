# mySports Video Creator

Vorlagen von Brain & Heart, mit denen Hockey-Reels für mySports im freigegebenen Design geschnitten werden (9:16, Figtree Bold, Sunrise Red).

[![In Colab öffnen](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dan-b-h/mysports-video-creator/blob/main/notebook/mySports_Video_Creator.ipynb)

## Was hier liegt
- `notebook/mySports_Video_Creator.ipynb` – Colab-Notebook: sichten, transkribieren, Spec speichern, rendern
- `vorlage/` – Render-Skripte
  - `render_goals_split.py` – Tore im Splitscreen, Spielstand auf der Mittellinie
  - `render_interview.py` – Interview im Hochformat mit Untertiteln Wort für Wort
  - `render_combo.py` – zuerst Tore (unten), dann Interview (oben)
  - `brand_text.py` – Textelemente im mySports-Design
  - `audio_tools.py` – Transkription, Sprechpausen, Wortzeiten
- `beispiele/` – freigegebene Specs als Vorlage

## Was nicht hier liegt
Videos, Logo, Schriften, Kader- und Protokolldaten liegen im internen Google Drive (Projektordner «mySports - SOM Organic - Video Creator»). Das Notebook verbindet beides.

## Einmalig einrichten
Damit Colab den Projektordner findet, braucht jede Person eine Verknüpfung in «Meine Ablage»:
im Google Drive den Ordner «mySports - SOM Organic - Video Creator» öffnen, oben auf den Ordnernamen klicken,
«Organisieren» → «Verknüpfung hinzufügen» → «Meine Ablage» wählen.

## Ablauf in Kürze
1. Notebook über den Button oben öffnen, Schritt 1 ausführen (Drive verbinden).
2. Szene und Texte mit dem Gemini-Gem «mySports Video Creator» erarbeiten.
3. Spec vom Gem in Schritt 4 einfügen, in Schritt 5 rendern.
4. Video prüfen, Kundin um Freigabe bitten.

Regel: pro Quelldatei höchstens 30 Sekunden Material, ausser mit ausdrücklicher Freigabe.
