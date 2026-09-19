#!/usr/bin/env python3
"""
Batch export script for the Psalm buffer (rows 8‑23 in the schedule).
Run from the Studio/ folder with:

	PYTHONPATH=/sdcard/LIBS:/sdcard/Scriptures:/sdcard/StyledScriptures python batch_export.py

It generates covers, audio (Library + Score), and two video variants:
- Landscape Library (horizontal, no music)  → YouTube
- Vertical Score   (portrait, with music)   → TikTok / Shorts / Instagram

Re‑entrant: checks whether each video already exists; if so, skips it.
"""

import sys
from pathlib import Path

# Ensure the foundation packages are importable.
sys.path.insert(0, "/sdcard/LIBS")
sys.path.insert(0, "/sdcard/Scriptures")
sys.path.insert(0, "/sdcard/StyledScriptures")

# Studio‑local imports (the script runs from the Studio folder).
from Bible import Bible
from Psalms import Psalms
from Audio import PsalmAudio
from Video import PsalmVideo
from Overlay import PsalmCover
import Media

# ── Psalm list from the buffer (sorted) ──
#PSALM_NUMBERS = [16, 35, 41, 42, 44, 59, 77, 84, 86, 93, 99, 105, 129, 130, 137, 150, 32, 90, 8, 46, 75, 117, 47]
#PSALM_NUMBERS = [32, 90, 8, 46, 75, 117, 47#]
PSALM_NUMBERS = [44, 105, 86, 137, 99, 41, 52, 2, 66, 6, 70, 101, 10, 74, 125, 3]
#[8, 46, 75, 90, 117, 32, 47, 84, 93, 16, 129, 42, 35, 77]
def main():
	bible = Bible()
	psalms = Psalms(bible)

	for num in PSALM_NUMBERS:
		print(f"\n── Psalm {num} ──")
		psalm = psalms[num - 1]

		# Covers (square, vertical, horizontal) – fast, always regenerate.
		#for size in (Media.SD, Media.SDV, Media.SDH):
		#	cover = PsalmCover(psalm, size)
		#	if cover.image is not None:
		#		cover.export()
		#		print(f"  Cover {size}")

		# Audio – fast, always regenerate.
		#PsalmAudio(psalm).export()				 # Library (bare narration)
		#PsalmAudio(psalm, music=True).export()	 # Score (with Suno)
		#print("  Audio exported")

		# Landscape Library video (horizontal, no music) – YouTube.
		lib_h = PsalmVideo(psalm, size=Media.HDH)
		if not Path(lib_h.filename).exists():
			print(f"  Generating Library H …")
			lib_h.export()
		else:
			print(f"  Library H already exists, skipping")

		# Vertical Score video (portrait, with music) – TikTok / Shorts / IG.
		score_v = PsalmVideo(psalm, size=Media.SDV, music=True)
		if not Path(score_v.filename).exists():
			print(f"  Generating Score V …")
			score_v.export()
		else:
			print(f"  Score V already exists, skipping")

	print("\n✅ Batch complete.")

if __name__ == "__main__":
	main()
