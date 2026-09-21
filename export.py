#!/usr/bin/env python3
"""
Batch export script for the Psalm buffer (rows 8‑23 in the schedule).
Run from the Studio/ folder with:

	PYTHONPATH=/root/WORK/Libraries:/root/WORK/MediaLibraries:/root/WORK/Scriptures:/root/WORK/StyledScriptures python automate.py

It generates, for every psalm in PSALM_NUMBERS, two audio files and two videos:
- Library audio (bare narration)            → output/psalms/
- Score audio   (narration + music)         → output/psalms+/
- Landscape Library video (horizontal, no music)  → YouTube
- Vertical Score video    (portrait, with music)  → TikTok / Shorts / Instagram

Re‑entrant: checks whether each file already exists; if so, skips it.
With --force, existing files are overwritten instead.
"""

import sys
from pathlib import Path

# Studio‑local imports (the script runs from the Studio folder).
from Bible import Bible
from Psalms import Psalms
import Asset
from Audio import PsalmAudio
from Video import PsalmVideo
from Overlay import PsalmCover
import Media

# ── Psalm list from the buffer (sorted) ──
#PSALM_NUMBERS = [16, 35, 41, 42, 44, 59, 77, 84, 86, 93, 99, 105, 129, 130, 137, 150, 32, 90, 8, 46, 75, 117, 47]
#PSALM_NUMBERS = [32, 90, 8, 46, 75, 117, 47]
#PSALM_NUMBERS = [44, 105, 86, 137, 99, 41, 52, 2, 66, 6, 70, 101, 10, 74, 125, 3]
#[8, 46, 75, 90, 117, 32, 47, 84, 93, 16, 129, 42, 35, 77]
PSALM_NUMBERS = [117]  # test: the shortest psalm

def main():
	force = "--force" in sys.argv
	bible = Bible()
	psalms = Psalms(bible)

	for num in PSALM_NUMBERS:
		print(f"\n── Psalm {num} ──")
		psalm = psalms[num - 1]

		# Square cover – the mp3 tags embed it, so it must exist before the audio.
		PsalmCover(psalm, Media.SD).export()

		# Audio (Library = bare narration, Score = with music).
		for music, folder in ((False, Asset.LIBRARY_AUDIO_FOLDER), (True, Asset.SCORE_AUDIO_FOLDER)):
			audio = PsalmAudio(psalm, music=music)
			if force or not (Path(folder) / f"{audio.basename}.mp3").exists():
				print(f"  Generating {'Score' if music else 'Library'} audio …")
				audio.export()
			else:
				print(f"  {'Score' if music else 'Library'} audio already exists, skipping")

		# Landscape Library video (horizontal, no music) – YouTube.
		lib_h = PsalmVideo(psalm, size=Media.HDH)
		if force or not Path(lib_h.filename).exists():
			print(f"  Generating Library H …")
			lib_h.export()
		else:
			print(f"  Library H already exists, skipping")

		# Vertical Score video (portrait, with music) – TikTok / Shorts / IG.
		score_v = PsalmVideo(psalm, size=Media.SDV, music=True)
		if force or not Path(score_v.filename).exists():
			print(f"  Generating Score V …")
			score_v.export()
		else:
			print(f"  Score V already exists, skipping")

	print("\n✅ Batch complete.")

if __name__ == "__main__":
	main()
