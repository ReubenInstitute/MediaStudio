#!/usr/bin/env python3
"""
Export psalm audio and videos.
Run from the Studio/ folder with:

	PYTHONPATH=/root/WORK/Libraries:/root/WORK/MediaLibraries:/root/WORK/Scriptures:/root/WORK/StyledScriptures python3 export.py [type] psalm... [--cache]

	export.py 8 46 75 --cache    all four files of each psalm, the batch
	export.py score 117          only the vertical video with music (the smallest one)
	export.py library 117        only the landscape video, no music (YouTube)
	export.py score-audio 117    only the mp3 with music     → output/psalms+/
	export.py library-audio 117  only the bare narration mp3 → output/psalms/

Without a type all four are exported. Files are overwritten, unless --cache is
given: then a file that already exists is skipped, so an interrupted batch can
be started again with the same command and continues where it stopped.
Files are written as name.part.ext and renamed when complete, so a file that
exists is a finished one.
"""

import sys
from pathlib import Path

from Bible import Bible
from Psalms import Psalms
import Asset
from Audio import PsalmAudio
from Video import PsalmVideo
from Overlay import PsalmCover
import Media

TYPES = ("score", "library", "score-audio", "library-audio")

def usage(message):
	sys.exit(f"{message}\nusage: export.py [{'|'.join(TYPES)}] psalm... [--cache]")

def main():
	args = sys.argv[1:]
	cache = "--cache" in args
	args = [arg for arg in args if arg != "--cache"]
	types = TYPES
	if args and not args[0].isdigit():
		if args[0] not in TYPES:
			usage(f"unknown type '{args[0]}'")
		types = (args.pop(0),)
	if not args:
		usage("no psalm numbers")
	if not all(arg.isdigit() and 1 <= int(arg) <= 150 for arg in args):
		usage("psalm numbers go from 1 to 150")

	bible = Bible()
	psalms = Psalms(bible)

	for num in map(int, args):
		print(f"\n── Psalm {num} ──")
		psalm = psalms[num - 1]

		if "score-audio" in types or "library-audio" in types:
			PsalmCover(psalm, Media.SD).export()

		items = []
		for music, folder in ((False, Asset.LIBRARY_AUDIO_FOLDER), (True, Asset.SCORE_AUDIO_FOLDER)):
			audio = PsalmAudio(psalm, music=music)
			items.append(("score-audio" if music else "library-audio", "Score audio" if music else "Library audio",
					Path(folder) / f"{audio.basename}.mp3", audio))
		library = PsalmVideo(psalm, size=Media.HDH)
		score = PsalmVideo(psalm, size=Media.SDV, music=True)
		items.append(("library", "Library H", library.filename, library))
		items.append(("score", "Score V", score.filename, score))

		for type, name, filename, item in items:
			if type not in types:
				continue
			if cache and Path(filename).exists():
				print(f"  {name} already exists, skipping")
				continue
			print(f"  Generating {name} …")
			item.export()

	print("\n✅ Export complete.")

if __name__ == "__main__":
	main()
