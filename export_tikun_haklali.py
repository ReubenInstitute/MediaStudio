#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, "/sdcard/LIBS")
sys.path.insert(0, "/sdcard/Scriptures")
sys.path.insert(0, "/sdcard/StyledScriptures")

from Asset import PSALMS_FOLDER, PSALMS_PLUS_FOLDER, HORIZONTAL_SUBFOLDER
import Media

STUDIO_FOLDER = Path(__file__).parent
TEMP_FOLDER = STUDIO_FOLDER / 'temp'
TIKUN_ORDER = [16, 32, 41, 42, 59, 77, 90, 105, 137, 150]

def get_available_psalms():
	available = []
	for num in TIKUN_ORDER:
		vertical_score = PSALMS_PLUS_FOLDER / f'psalm{num:03d}.mp4'
		if vertical_score.exists():
			available.append(num)
#	if len(available) > 1:
#		available = available[:-1]
	return available

def strip_image_track(input_path, output_path):
	"""Copy only the audio stream from an MP3, discarding attached pictures."""
	cmd = [
		'ffmpeg', '-y',
		'-i', str(input_path),
		'-map', '0:a',
		'-c', 'copy',
		str(output_path)
	]
	subprocess.run(cmd, check=True, capture_output=True)

def concat_audio(inputs, output_path):
	"""Concatenate audio-only MP3 files using the concat demuxer."""
	list_file = STUDIO_FOLDER / 'tmp_concat_list.txt'
	with open(list_file, 'w') as f:
		for p in inputs:
			f.write(f"file '{p.resolve()}'\n")

	cmd = [
		'ffmpeg', '-y',
		'-f', 'concat', '-safe', '0',
		'-i', str(list_file),
		'-c', 'copy',
		str(output_path)
	]
	subprocess.run(cmd, check=True)
	list_file.unlink()

def concat_video(inputs, output_path):
	"""Concatenate video files using the concat demuxer."""
	list_file = STUDIO_FOLDER / 'tmp_concat_list.txt'
	with open(list_file, 'w') as f:
		for p in inputs:
			f.write(f"file '{p.resolve()}'\n")

	cmd = [
		'ffmpeg', '-y',
		'-f', 'concat', '-safe', '0',
		'-i', str(list_file),
		'-c', 'copy',
		str(output_path)
	]
	subprocess.run(cmd, check=True)
	list_file.unlink()

def tag_audio(filepath, music=False):
	comments = [
		'קריינות: אברהם שמואלוב (הוקלט בשנות ה‑70), שוחזרה באמצעות ElevenLabs. סדרת תהילים של מכון ראובן.',
		'קריינות: אברהם שמואלוב (הוקלט בשנות ה‑70), שוחזרה באמצעות ElevenLabs. מוזיקת רקע: Suno AI v5. סדרת תהילים של מכון ראובן.'
	]
	tags = {
		'title': 'תיקון הכללי',
		'artist': 'מכון ראובן',
		'publisher': 'מכון ראובן',
		'year': 2026,
		'language': 'heb',
		'comments': comments[1] if music else comments[0],
	}
	Media.set_id3_tags(str(filepath), tags)

def main():
	available = get_available_psalms()
	if not available:
		print("No completed psalms found.")
		return

	print(f"Building Tikun Haklali from psalms: {available}")

	TEMP_FOLDER.mkdir(exist_ok=True)

	# Prepare temporary audio‑only copies
	tmp_lib_audio = []
	tmp_score_audio = []
	for n in available:
		src_lib = PSALMS_FOLDER / f'psalm{n:03d}.mp3'
		dst_lib = TEMP_FOLDER / f'psalm{n:03d}_clean.mp3'
		strip_image_track(src_lib, dst_lib)
		tmp_lib_audio.append(dst_lib)

		src_score = PSALMS_PLUS_FOLDER / f'psalm{n:03d}.mp3'
		dst_score = TEMP_FOLDER / f'psalm{n:03d}_clean.mp3'
		strip_image_track(src_score, dst_score)
		tmp_score_audio.append(dst_score)

	lib_video_inputs   = [PSALMS_FOLDER / f'psalm{n:03d}.mp4' for n in available]
	score_video_inputs = [PSALMS_PLUS_FOLDER / f'psalm{n:03d}.mp4' for n in available]

	out_lib_audio   = PSALMS_FOLDER / 'TikunHaklali.mp3'
	out_score_audio = PSALMS_PLUS_FOLDER / 'TikunHaklali+.mp3'
	out_lib_video   = PSALMS_FOLDER / 'TikunHaklali.mp4'
	out_score_video = PSALMS_PLUS_FOLDER / 'TikunHaklali+.mp4'

	concat_audio(tmp_lib_audio, out_lib_audio)
	tag_audio(out_lib_audio, music=False)

	concat_audio(tmp_score_audio, out_score_audio)
	tag_audio(out_score_audio, music=True)

	concat_video(lib_video_inputs, out_lib_video)
	concat_video(score_video_inputs, out_score_video)

	# Clean up temporary files
	for f in tmp_lib_audio + tmp_score_audio:
		f.unlink(missing_ok=True)
	TEMP_FOLDER.rmdir()

	print("Done.")

if __name__ == '__main__':
	main()
