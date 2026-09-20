
import os
import ffmpeg
from pathlib import Path
from mutagen.id3 import ID3, TIT2, COMM, TPE1, TPUB, TYER, TLAN, TRCK, TALB, TCOP

import HebrewNumbers
import Media

from AudioBible import AudioBible
#from BiblePsalms import BiblePsalm
import Asset


AUDIO_FOLDER = "audio"
ASSETS_FOLDER = 'assets'
OUTPUT_FOLDER = "output"

FADE_DURATION = 0.5


class PsalmAudio:

	def __init__(self, psalm, music=False):
		self.psalm = psalm
		self.audiobible = AudioBible.get_instance()
		self.music = music

	@property
	def basename(self):
		return f'psalm{self.psalm.number:03d}'

	@property
	def segments(self):
		segments_list = []

		title_path = Asset.TITLES_FOLDER / f'psalm{self.psalm.number:03d}.mp3'
		title_seg = ffmpeg.concat(
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
			ffmpeg.input(title_path).audio.filter('asetpts', 'PTS-STARTPTS'),
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
			v=0, a=1
		)
		segments_list.append(title_seg)

		for paragraph in self.psalm.paragraphs:
			for verse in paragraph.verses:
				mp3 = self.audiobible.cloned_mp3(verse)
				verse_seg = ffmpeg.concat(
					ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
					ffmpeg.input(mp3).filter('asetpts', 'PTS-STARTPTS'),
					ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
					v=0, a=1
				)
				segments_list.append(verse_seg)

		return segments_list

	@property
	def duration(self):
		total = 0.0
		title_dur = self.audiobible.title_duration(f'psalm{self.psalm.number:03d}.mp3')
		total += Asset.FADE_DURATION + title_dur + Asset.FADE_DURATION
		for verse in self.psalm.verses:
			dur = self.audiobible.cloned_duration(verse)
			total += Asset.FADE_DURATION + dur + Asset.FADE_DURATION
		return total

	@property
	def stream(self):
		narration = ffmpeg.concat(*self.segments, v=0, a=1).node[0]
		if not self.music:
			return narration

		music_file = Asset.ASSETS_FOLDER / f'{self.psalm.number:03d}.mp3'
		if not music_file.exists():
			return narration

		track = ffmpeg.input(music_file).audio
		title_dur = Asset.FADE_DURATION + self.audiobible.title_duration(f'psalm{self.psalm.number:03d}.mp3') + Asset.FADE_DURATION
		total_dur = self.duration
		delay_ms = int(title_dur * 1000)

		music = track.filter('adelay', f'{delay_ms}|{delay_ms}')
		music = music.filter('atrim', duration=total_dur)
		music = music.filter('volume', 0.2)
		music = music.filter('afade', type='in', start_time=0, duration=0.5)
		FOUT = 1.5
		fade_out_start = total_dur - FOUT - title_dur
		music = music.filter('afade', type='out', start_time=fade_out_start, duration=FOUT)

		return ffmpeg.filter([narration, music], 'amix', inputs=2, duration='shortest')

	def set_tags(self, filename):
		common_tags = {
			'title': f'מזמור {HebrewNumbers.hebrew_fancy_number(self.psalm.number)}',
			'artist': 'מכון ראובן',
			'publisher': 'מכון ראובן',
			'year': 2026,
			'month': 5,
			'track_index': self.psalm.number,
			'num_tracks': 150,
			'album': 'תהילים',
			'language': 'heb',
		}

		comments = [
			'קריינות: אברהם שמואלוב (הוקלט בשנות ה‑70), שוחזרה באמצעות ElevenLabs. סדרת תהילים של מכון ראובן.',
			'קריינות: אברהם שמואלוב (הוקלט בשנות ה‑70), שוחזרה באמצעות ElevenLabs. מוזיקת רקע: Suno AI v5. סדרת תהילים של מכון ראובן.'
		]

		cover_path = Asset.LIBRARY_COVERS_FOLDER / Asset.SQUARE_SUBFOLDER / f'psalm{self.psalm.number:03d}.jpg'

		tags = dict(common_tags)
		tags['image'] = str(cover_path)
		tags['comments'] = comments[0] if not self.music else comments[1]

		Media.set_id3_tags(filename, tags)

	def export(self):
		folder = Asset.LIBRARY_AUDIO_FOLDER if not self.music else Asset.SCORE_AUDIO_FOLDER
		os.makedirs(folder, exist_ok=True)
		filename = folder / f'{self.basename}.mp3'
		ffmpeg.output(self.stream, str(filename), acodec='mp3').overwrite_output().run()
		self.set_tags(filename)

	def export_sln(self):
		folder = Asset.LIBRARY_AUDIO_FOLDER if not self.music else Asset.SCORE_AUDIO_FOLDER
		os.makedirs(folder, exist_ok=True)
		filename = folder / f'{self.basename}.sln'
		ffmpeg.output(self.stream, str(filename), acodec='pcm_s16le', ar='8000', ac=1, f='s16le').overwrite_output().run()







class ODSPsalmAudio:
	FADE_DURATION = 0.5

	def __init__(self, psalm):
		self.psalm = psalm
		self.audiobible = AudioBible.get_instance()
	
	@property
	def basename(self):
		return f'psalm{self.psalm.number:03d}'
	
	@property
	def music(self):
		music_file = os.path.join(ASSETS_FOLDER, f'{self.psalm.number:03d}.mp3')
		if os.path.exists(music_file):
			return ffmpeg.input(music_file).audio
		return None

	@property
	def segments(self):
		segments_list = []
	
		# Title
		title_path = Path(AUDIO_FOLDER) / 'titles' / f'psalm{self.psalm.number:03d}.mp3'
		title_seg = ffmpeg.concat(
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
			ffmpeg.input(title_path).audio.filter('asetpts', 'PTS-STARTPTS'),
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
			v=0, a=1
		)
		segments_list.append(title_seg)
	
		# Verses
		for paragraph in self.psalm.paragraphs:
			#for slide_index, slide in enumerate(paragraph.slides, 1):
			for verse in paragraph.verses:
				#verse = paragraph.verses[slide_index - 1]
				mp3 = self.audiobible.cloned_mp3(verse)
				verse_seg = ffmpeg.concat(
					ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
					ffmpeg.input(mp3)#.audio
						.filter('asetpts', 'PTS-STARTPTS'),
					ffmpeg.input('anullsrc=r=44100:cl=stereo', t=Asset.FADE_DURATION, f='lavfi').audio,
					v=0, a=1
				)
				segments_list.append(verse_seg)
	
		return segments_list




	@property
	def duration(self):
		total = 0.0
		title_dur = self.audiobible.title_duration(f'psalm{self.psalm.number:03d}.mp3')
		total += Asset.FADE_DURATION + title_dur + Asset.FADE_DURATION
		for verse in self.psalm.verses:
			dur = self.audiobible.cloned_duration(verse)
			total += Asset.FADE_DURATION + dur + Asset.FADE_DURATION
		return total

	@property
	def stream(self):
		segments = ffmpeg.concat(*self.segments, v=0, a=1).node[0]
		return segments

	@property
	def enhanced_stream(self):
		bare = self.stream
		if self.music:
			duration = self.duration
			music = self.music.filter('atrim', duration=duration)
			music = music.filter('volume', 0.2)
			music = music.filter('afade', type='in', start_time=0, duration=0.5)
			music = music.filter('afade', type='out', start_time=duration - 1.5, duration=1.5)
			mixed = ffmpeg.filter([bare, music], 'amix', inputs=2, duration='shortest')
			return mixed
		return bare




	@property
	def enhanced_stream(self):
		bare = self.stream
		if self.music:
			# length of the title segment (fade in + title audio + fade out)
			title_dur = Asset.FADE_DURATION + self.audiobible.title_duration(f'psalm{self.psalm.number:03d}.mp3') + Asset.FADE_DURATION
			total_dur = self.duration
	
			# delay the music so it starts exactly when verse 1 begins
			delay_ms = int(title_dur * 1000)
			music = self.music.filter('adelay', f'{delay_ms}|{delay_ms}')
			music = music.filter('atrim', duration=total_dur)
	
			music = music.filter('volume', 0.2)
			# fade in at the moment the music actually starts (t=0 in the delayed stream)
			music = music.filter('afade', type='in', start_time=0, duration=0.5)
			# fade out near the end of the psalm (relative to the delayed stream)
			fade_out_start = total_dur - 1.5 - title_dur
			music = music.filter('afade', type='out', start_time=fade_out_start, duration=1.5)
	
			mixed = ffmpeg.filter([bare, music], 'amix', inputs=2, duration='shortest')
			return mixed
		return bare




	def set_tags(self, filename, bare=False):
		common_tags = {
			'title': f'מזמור {HebrewNumbers.hebrew_fancy_number(self.psalm.number)}',
			'artist': 'מכון ראובן',
			'publisher': 'מכון ראובן',
			'year': 2026,
			'month': 5,
			'track_index': self.psalm.number,
			'num_tracks': 150,
			'album': 'תהילים',
			'language': 'heb',
		}

		comments = [
			'קריינות: אברהם שמואלוב (הוקלט בשנות ה‑70), שוחזרה באמצעות ElevenLabs. סדרת תהילים של מכון ראובן.',
			'קריינות: אברהם שמואלוב (הוקלט בשנות ה‑70), שוחזרה באמצעות ElevenLabs. מוזיקת רקע: Suno AI v5. סדרת תהילים של מכון ראובן.'
		]

		cover_path = os.path.join(OUTPUT_FOLDER, f'psalms/covers/psalm{self.psalm.number:03d}.jpg')

		tags = dict(common_tags)
		tags['image'] = cover_path
		tags['comments'] = comments[0] if bare else comments[1]

		Media.set_id3_tags(filename, tags)

	def export(self, bare=False):
		stream_to_export = self.stream if bare else (self.enhanced_stream if self.music else self.stream)
		suffix = '-bare' if bare else ''
		filename = os.path.join(OUTPUT_FOLDER, f'{self.basename}{suffix}.mp3')
		ffmpeg.output(stream_to_export, filename, acodec='mp3').overwrite_output().run()
		self.set_tags(filename, bare=bare)

	def export_sln(self, bare=False):
		stream_to_export = self.stream if bare else (self.enhanced_stream if self.music else self.stream)
		suffix = '-bare' if bare else ''
		filename = os.path.join(OUTPUT_FOLDER, f'{self.basename}{suffix}.sln')
		ffmpeg.output(stream_to_export, filename, acodec='pcm_s16le', ar='8000', ac=1, f='s16le').overwrite_output().run()



class ParashahAudio():
	def __init__(self, parashah):
		self.parashah = parashah

	@property
	def basename(self):
		return f'parashah-{self.parashah.number:02d}'

	def set_id3_tags(self, filename):
		audio = ID3()
		audio.add(TIT2(encoding=3, text=self.parashah.hebrew_name))
		audio.add(COMM(encoding=3, lang='heb', desc='', text=''))
		audio.add(TPE1(encoding=3, text='מכון ראובן'))
		audio.add(TPUB(encoding=3, text='מכון ראובן'))
		audio.add(TYER(encoding=3, text='2025'))
		audio.add(TLAN(encoding=3, text='heb'))
		audio.add(TRCK(encoding=3, text=f'{self.parashah.number:02d}/54'))
		audio.add(TALB(encoding=3, text='פרשת השבוע'))
		audio.add(TCOP(encoding=3, text=''))
		audio.save(filename, v2_version=3)

	def export_mp3(self):
		Asset.TORAH_FOLDER.mkdir(parents=True, exist_ok=True)
		files = []
		for episode in self.parashah.episodes:
			episode_audio = EpisodeAudio(episode)
			if not episode_audio.filename.exists():
				episode_audio.export_mp3()
			files.append(episode_audio.filename)
		list_file = Path("build") / f'{self.basename}.txt'
		list_file.parent.mkdir(parents=True, exist_ok=True)
		list_file.write_text(''.join(f"file '{f.resolve()}'\n" for f in files))
		filename = Asset.TORAH_FOLDER / f'{self.basename}.mp3'
		ffmpeg.input(str(list_file), f='concat', safe=0).output(str(filename), c='copy').run(overwrite_output=True)
		self.set_id3_tags(filename)


"""

class PsalmsBookAudio:
	def __init__(self, psalms):
		self.psalms = psalms
		self.book_num = psalms[0].volume  # 1–5

	@property
	def _title_segment(self):
		from Media import get_duration
		title_path = os.path.join('titles', f'book{self.book_num}.mp3')
		title_duration = get_duration(title_path)
		return ffmpeg.concat(
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			ffmpeg.input(title_path).audio.filter('asetpts', 'PTS-STARTPTS'),
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			v=0, a=1
		)

	@property
	def _title_duration(self):
		from Media import get_duration
		title_path = os.path.join('titles', f'book{self.book_num}.mp3')
		return 0.5 + get_duration(title_path) + 0.5

	@property
	def segments(self):
		segs = [self._title_segment]
		for psalm in self.psalms:
			segs.extend(psalm.audio.segments)
		return segs

	@property
	def duration(self):
		return self._title_duration + sum(psalm.audio.duration for psalm in self.psalms)

	def export_mp3(self, filename):
		audio_concat = ffmpeg.concat(*self.segments, v=0, a=1).node[0]
		ffmpeg.output(audio_concat, filename, acodec='mp3').overwrite_output().run()
		self._set_id3_tags(filename)

	def _set_id3_tags(self, filename):
		from Media import set_id3_tags
		first = self.psalms[0].number
		last = self.psalms[-1].number
		book_names = ["ספר ראשון", "ספר שני", "ספר שלישי", "ספר רביעי", "ספר חמישי"]
		book_hebrew = book_names[self.book_num - 1]
		title = f"תהילים {book_hebrew} (מזמורים {first}–{last})"
		tags = {
			'title': title,
			'artist': 'מכון ראובן',
			'publisher': 'מכון ראובן',
			'time': '2026',
			'track_index': self.book_num,
			'num_tracks': 5,
			'album': 'תהילים',
			'language': 'heb',
		}
		set_id3_tags(filename, tags)

class PsalmsCompleteAudio:
	def __init__(self, bible):
		self.bible = bible

	@property
	def _book_files(self):
		return [
			'output/psalms-book1.mp3',
			'output/psalms-book2.mp3',
			'output/psalms-book3.mp3',
			'output/psalms-book4.mp3',
			'output/psalms-book5.mp3'
		]

	@property
	def _title_segment(self):
		from Media import get_duration
		title_path = os.path.join('titles', 'psalms.mp3')
		title_duration = get_duration(title_path)
		return ffmpeg.concat(
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			ffmpeg.input(title_path).audio.filter('asetpts', 'PTS-STARTPTS'),
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			v=0, a=1
		)

	@property
	def _title_duration(self):
		from Media import get_duration
		title_path = os.path.join('titles', 'psalms.mp3')
		return 0.5 + get_duration(title_path) + 0.5

	@property
	def segments(self):
		segs = [self._title_segment]
		for path in self._book_files:
			segs.append(ffmpeg.input(path).audio)
		return segs

	@property
	def duration(self):
		from Media import get_duration
		total = self._title_duration
		for path in self._book_files:
			total += get_duration(path)
		return total

	def export_mp3(self, filename):
		audio_concat = ffmpeg.concat(*self.segments, v=0, a=1).node[0]
		ffmpeg.output(audio_concat, filename, acodec='mp3').overwrite_output().run()
		self._set_id3_tags(filename)

	def _set_id3_tags(self, filename):
		from Media import set_id3_tags
		tags = {
			'title': 'תהילים השלם',
			'artist': 'מכון ראובן',
			'publisher': 'מכון ראובן',
			'time': '2026',
			'album': 'תהילים',
			'language': 'heb',
			'track_index': 1,
			'num_tracks': 1,
		}
		set_id3_tags(filename, tags)

class DailyPsalmsAudio:
	FOUR_WEEKS = [
		[1, 18, 49],
		[78, 93],
		[37, 107],
		[68, 73, 97],
		[22, 65, 109],
		[89, 102, 117],
		[35, 69, 74, 106, 147],
		[40, 44, 77, 100, 134],
		[38, 71, 88, 101],
		[9, 55, 82, 139],
		[27, 105, 118],
		[50, 80, 104],
		[34, 59, 84, 136],
		[103, 119],
		[25, 51, 86, 90],
		[10, 45, 79, 145],
		[33, 66, 94, 135],
		[17, 52, 83, 92, 144],
		[7, 57, 81, 91, 132],
		[39, 72, 85, 96, 116],
		[19, 41, 42, 56, 75, 76, 87, 95, 98, 99, 115, 131, 143],
		[5, 32, 48, 60, 110, 140],
		[21, 31, 58, 62, 141, 148],
		[15, 30, 36, 46, 63, 108, 137],
		[2, 4, 47, 53, 64, 112, 128, 146],
		[16, 26, 28, 43, 54, 61, 111, 142],
		[6, 8, 24, 67, 70, 122, 126, 138, 149],
		[3, 11, 12, 13, 14, 20, 23, 29, 113, 114, 124, 125, 127, 129, 130, 150]
	]

	def __init__(self, bible, week, day):
		self.bible = bible
		self.week = week
		self.day = day
		self.day_index = (week - 1) * 7 + (day - 1)

	@property
	def psalm_numbers(self):
		return self.FOUR_WEEKS[self.day_index]

	@property
	def psalms(self):
		return [self.bible.psalms[number - 1] for number in self.psalm_numbers]

	@property
	def title_segment(self):
		from Media import get_duration
		title_path = os.path.join('titles', f'week{self.week}_day{self.day}.mp3')
		title_duration = get_duration(title_path)
		return ffmpeg.concat(
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			ffmpeg.input(title_path).audio.filter('asetpts', 'PTS-STARTPTS'),
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			v=0, a=1
		)

	@property
	def title_duration(self):
		from Media import get_duration
		title_path = os.path.join('titles', f'week{self.week}_day{self.day}.mp3')
		return 0.5 + get_duration(title_path) + 0.5

	@property
	def segments(self):
		segs = [self.title_segment]
		for psalm in self.psalms:
			segs.extend(psalm.audio.segments)
		return segs

	@property
	def duration(self):
		return self.title_duration + sum(psalm.audio.duration for psalm in self.psalms)

	def export_mp3(self, filename):
		audio_concat = ffmpeg.concat(*self.segments, v=0, a=1).node[0]
		ffmpeg.output(audio_concat, filename, acodec='mp3').overwrite_output().run()
		self._set_id3_tags(filename)

	def _set_id3_tags(self, filename):
		from Media import set_id3_tags
		week_names = ["ראשון", "שני", "שלישי", "רביעי"]
		day_names = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "ששי", "שבת"]
		title = f"שבוע {week_names[self.week-1]}, יום {day_names[self.day-1]}"
		tags = {
			'title': title,
			'artist': 'מכון ראובן',
			'publisher': 'מכון ראובן',
			'time': '2026',
			'album': 'תהילים - מחזור ארבעה שבועות',
			'language': 'heb',
			'track_index': self.day_index + 1,
			'num_tracks': 28,
		}
		set_id3_tags(filename, tags)

class FourWeekCompleteAudio:
	def __init__(self):
		pass

	@property
	def _daily_files(self):
		files = []
		for week in range(1, 5):
			for day in range(1, 8):
				files.append(f'output/daily/week{week}_day{day}.mp3')
		return files

	@property
	def _title_segment(self):
		from Media import get_duration
		title_path = os.path.join('titles', 'psalms.mp3')
		title_duration = get_duration(title_path)
		return ffmpeg.concat(
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			ffmpeg.input(title_path).audio.filter('asetpts', 'PTS-STARTPTS'),
			ffmpeg.input('anullsrc=r=44100:cl=stereo', t=0.5, f='lavfi').audio,
			v=0, a=1
		)

	@property
	def _title_duration(self):
		from Media import get_duration
		title_path = os.path.join('titles', 'psalms.mp3')
		return 0.5 + get_duration(title_path) + 0.5

	@property
	def segments(self):
		segs = [self._title_segment]
		for path in self._daily_files:
			segs.append(ffmpeg.input(path).audio)
		return segs

	@property
	def duration(self):
		from Media import get_duration
		total = self._title_duration
		for path in self._daily_files:
			total += get_duration(path)
		return total

	def export_mp3(self, filename):
		audio_concat = ffmpeg.concat(*self.segments, v=0, a=1).node[0]
		ffmpeg.output(audio_concat, filename, acodec='mp3').overwrite_output().run()
		self._set_id3_tags(filename)

	def _set_id3_tags(self, filename):
		from Media import set_id3_tags
		tags = {
			'title': 'תהילים - מחזור ארבעה שבועות',
			'artist': 'מכון ראובן',
			'publisher': 'מכון ראובן',
			'time': '2026',
			'album': 'תהילים',
			'language': 'heb',
			'track_index': 1,
			'num_tracks': 1,
		}
		set_id3_tags(filename, tags)







"""















class EpisodeAudio:

	def __init__(self, episode):
		self.episode = episode
		self.audiobible = AudioBible.get_instance()

	@property
	def basename(self):
		#slug = self.episode.parashah.slug
		return f"{self.episode.parashah.number:02d}.{self.episode.number:02d}"

	@property
	def segments(self):
		segments = []
		for verse in self.episode.verses:
			mp3 = self.audiobible.cloned_mp3(verse)
			#if not mp3.exists():
			#	continue
			audio_duration = self.audiobible.cloned_duration(verse)
			#if audio_duration <= 0:
			#	continue
			verse_seg = ffmpeg.concat(
				ffmpeg.input('anullsrc=r=44100:cl=stereo', t=FADE_DURATION, f='lavfi').audio,
				ffmpeg.input(mp3).audio.filter('asetpts', 'PTS-STARTPTS'),
				ffmpeg.input('anullsrc=r=44100:cl=stereo', t=FADE_DURATION, f='lavfi').audio,
				v=0, a=1
			)
			segments.append(verse_seg)
		return segments

	@property
	def duration(self):
		total = 0.0
		for verse in self.episode.verses:
			dur = self.audiobible.cloned_duration(verse)
			#if dur <= 0:
			#	continue
			total += FADE_DURATION + dur + FADE_DURATION
		return total

	@property
	def stream(self):
		return ffmpeg.concat(*self.segments, v=0, a=1).node[0]

	@property
	def filename(self):
		return Asset.TORAH_FOLDER / f'{self.basename}.mp3'

	def export_mp3(self):
		self.filename.parent.mkdir(parents=True, exist_ok=True)
		ffmpeg.output(self.stream, filename=str(self.filename), acodec='mp3').overwrite_output().run()
