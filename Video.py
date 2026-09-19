import os
import ffmpeg
from Overlay import ParashahOverlay, PsalmOverlay, EpisodeOverlay, EpisodeParagraphSlide, PsalmVerseSlide, EpisodeCover
import Media
import Asset
from pathlib import Path

from AudioBible import AudioBible
from Audio import PsalmAudio

ASSETS_FOLDER = "assets"
OUTPUT_FOLDER = "output"
BUILD_FOLDER = "build"


class Video(Asset.Asset):
	FADE_DURATION = 0.5
	BACKGROUND_OPACITY = 0.7

	def __init__(self, size):
		super().__init__(size)

	def export(self):
		Path(self.filename).parent.mkdir(parents=True, exist_ok=True)
		video = self.video_stream
		audio = self.audio_stream
#		full_path = os.path.join(OUTPUT_FOLDER, self.filename)
		ffmpeg.output(
			video, 
			audio, 
			self.filename, 
			vcodec='libx264', 
			preset='veryfast', 
			crf=23, 
			acodec='aac', 
			audio_bitrate='192k', 
			pix_fmt='yuv420p'
		).run(overwrite_output=True)



class EpisodeVideo(Video):
	def __init__(self, episode, size, raw=False):
		super().__init__(size)
		self.episode = episode
		self.raw = raw
		self.audiobible = AudioBible.get_instance()

	@property
	def filename(self):
		suffix = '-raw' if self.raw else ''
		return f'torah-{self.episode.parashah.number:02d}.{self.episode.number:02d}{suffix}.mp4'

	def generate_assets(self):
		overlay = EpisodeOverlay(self.episode, size=self.size)
		overlay.export()
		for paragraph in self.episode.paragraphs:
			slide = EpisodeParagraphSlide(self.episode, paragraph.number, size=self.size)
			print (slide)
			slide.export()

	@property
	def video_stream(self):
		video_nodes = []
		x = 0.001
		for paragraph in self.episode.paragraphs:
			verses_in_paragraph = paragraph.verses
			for i, verse in enumerate(verses_in_paragraph):
				verse_num = verse.number
				audio_duration = self.audiobible.cloned_duration(verse)
				audio_duration += x
				x += 0.001
				is_first_verse = (i == 0)
				is_last_verse = (i == len(verses_in_paragraph) - 1)
				segment_duration = self.FADE_DURATION + audio_duration + self.FADE_DURATION

				base_image_path = os.path.join(BUILD_FOLDER, "images", "parashot",
											   f"{self.episode.parashah.number}.{self.episode.number}.{paragraph.number}.0.png")
				highlight_image_path = os.path.join(BUILD_FOLDER, "images", "parashot",
													f"{self.episode.parashah.number}.{self.episode.number}.{paragraph.number}.{verse_num}.png")

				base_video = ffmpeg.input(base_image_path, loop=1, t=segment_duration)
				base_video = base_video.filter('scale', self.width, self.height)
				base_video = base_video.filter('format', 'rgba')
				if is_first_verse:
					base_video = base_video.filter('fade', type='in', duration=self.FADE_DURATION)
				if is_last_verse:
					base_video = base_video.filter('fade', type='out', start_time=segment_duration - self.FADE_DURATION, duration=self.FADE_DURATION)

				highlight_video = ffmpeg.input(highlight_image_path, loop=1, t=segment_duration)
				highlight_video = highlight_video.filter('scale', self.width, self.height)
				highlight_video = highlight_video.filter('format', 'rgba')
				highlight_video = highlight_video.filter('fade', type='in', alpha=1, duration=self.FADE_DURATION)
				highlight_video = highlight_video.filter('fade', type='out', alpha=1,
														 start_time=segment_duration - self.FADE_DURATION,
														 duration=self.FADE_DURATION)

				verse_video = ffmpeg.overlay(base_video, highlight_video)
				video_nodes.append(verse_video)

		if not video_nodes:
			return ffmpeg.input('anullsrc', f='lavfi', t=self.duration).video.filter('format', 'rgba').filter('geq', r='0', g='0', b='0', a='0')
		video_concat = ffmpeg.concat(*video_nodes, v=1, a=0).node[0]

		video = self.background
		video = ffmpeg.overlay(video, video_concat, format='auto', shortest=1)
		video = ffmpeg.overlay(video, self.overlay, format='auto', shortest=1)
		return video

	@property
	def audio_stream(self):
		from Audio import EpisodeAudio
		episode_audio = EpisodeAudio(self.episode)
		return episode_audio.stream

	@property
	def duration(self):
		total = 0.0
		for paragraph in self.episode.paragraphs:
			for verse in paragraph.verses:
				audio_duration = self.audiobible.cloned_duration(verse)
				total += self.FADE_DURATION + audio_duration + self.FADE_DURATION
		return total

	@property
	def background(self):
		duration = self.duration
		if self.raw:
			background = ffmpeg.input(os.path.join(ASSETS_FOLDER, 'back.mp4'), stream_loop=-1, t=duration)
			background = background.filter('scale', self.width, self.height, force_original_aspect_ratio='increase')
			background = background.filter('crop', w=self.width, h=self.height)
			color_hex = f"#{self.episode.color[0]:02x}{self.episode.color[1]:02x}{self.episode.color[2]:02x}"
			color_overlay = ffmpeg.input(f'color=c={color_hex}:s={self.width}x{self.height}', f='lavfi', t=duration)
			background = ffmpeg.filter([background, color_overlay], 'blend', all_mode='overlay', all_opacity=self.BACKGROUND_OPACITY)
		else:
			background = ffmpeg.input(f'color=c=black:s={self.width}x{self.height}', f='lavfi', t=duration)
		return background

	@property
	def overlay(self):
		duration = self.duration
		title_image_path = f"build/images/parashot/{self.episode.parashah.number:02d}_{self.episode.number:02d}_title.png"
		overlay = ffmpeg.input(title_image_path, loop=1, t=duration)
		overlay = overlay.filter('scale', self.width, self.height)
		overlay = overlay.filter('format', 'rgba')
		overlay = overlay.filter('fade', type='in', start_time=0, duration=self.FADE_DURATION)
		overlay = overlay.filter('fade', type='out', start_time=duration - self.FADE_DURATION, duration=self.FADE_DURATION)
		return overlay

	def export(self):
		self.generate_assets()
		super().export()







class PsalmVideo(Video):
	def __init__(self, psalm, size, music=False, graphics=False):
		super().__init__(size)
		self.psalm = psalm
		self.music = music
		self.graphics = graphics
		self.audiobible = AudioBible.get_instance()


	@property
	def basename(self):
		return f'psalm{self.psalm.number:03d}'

	@property
	def filename(self):
		if self.graphics:
			folder = Asset.CINEMATIC_VIDEO_FOLDER
			folder = folder / Asset.HORIZONTAL_SUBFOLDER if self.landscape else folder
		elif self.music:
			folder = Asset.SCORE_VIDEO_FOLDER
			folder = folder / Asset.HORIZONTAL_SUBFOLDER if self.landscape else folder
		else:
			folder = Asset.LIBRARY_VIDEO_FOLDER
		return str(folder / f'{self.basename}.mp4')

	def generate_assets(self):
		overlay = PsalmOverlay(self.psalm, size=self.size)
		overlay.export()
		for paragraph in self.psalm.paragraphs:
			for verse in paragraph.verses:
				slide = PsalmVerseSlide(self.psalm, paragraph.number, verse.number, size=self.size)
				slide.export()

	@property
	def duration(self):
		psalm_audio = PsalmAudio(self.psalm)
		return psalm_audio.duration

	@property
	def background(self):
		duration = self.duration
		if not self.graphics:
			fog_name = "back-720x1280.mp4" if not self.landscape else "back-1280x720.mp4"
			background = ffmpeg.input(os.path.join(ASSETS_FOLDER, fog_name), stream_loop=-1, t=duration)
			background = background.filter('scale', self.width, self.height, force_original_aspect_ratio='increase')
			background = background.filter('crop', w=self.width, h=self.height)
			color_hex = f"#{self.psalm.color[0]:02x}{self.psalm.color[1]:02x}{self.psalm.color[2]:02x}"
			color_overlay = ffmpeg.input(f'color=c={color_hex}:s={self.width}x{self.height}', f='lavfi', t=duration)
			background = ffmpeg.filter([background, color_overlay], 'blend', all_mode='overlay', all_opacity=self.BACKGROUND_OPACITY)
		else:
			custom_bg = os.path.join(ASSETS_FOLDER, f'{self.psalm.number:03d}.mp4')
			if os.path.exists(custom_bg):
				background = ffmpeg.input(custom_bg, stream_loop=-1, t=duration)
				background = background.filter('scale', self.width, self.height, force_original_aspect_ratio='increase')
				background = background.filter('crop', w=self.width, h=self.height)
			else:
				background = ffmpeg.input(f'color=c=black:s={self.width}x{self.height}', f='lavfi', t=duration)
		return background

	@property
	def overlay(self):
		duration = self.duration
		title_image_path = f"build/images/psalms/{self.psalm.number:03d}_title.png"
		overlay = ffmpeg.input(title_image_path, loop=1, t=duration)
		overlay = overlay.filter('scale', self.width, self.height)
		overlay = overlay.filter('format', 'rgba')
		overlay = overlay.filter('fade', type='in', start_time=0, duration=self.FADE_DURATION)
		overlay = overlay.filter('fade', type='out', start_time=duration - self.FADE_DURATION, duration=self.FADE_DURATION)
		return overlay

	@property
	def video_stream(self):
		audiobible = self.audiobible
		duration = self.duration

		title_dur = audiobible.title_duration(f'psalm{self.psalm.number:03d}.mp3')
		title_total_duration = self.FADE_DURATION + title_dur + self.FADE_DURATION
		title_video = ffmpeg.input(f'nullsrc=s={self.width}x{self.height}:d={title_total_duration}', f='lavfi')
		title_video = title_video.filter('format', 'rgba')
		title_video = title_video.filter('geq', r='0', g='0', b='0', a='0')


		verse_videos = []
		for paragraph in self.psalm.paragraphs:
			for verse in paragraph.verses:
				if not audiobible.has_cloned_audio(verse):
					continue
				audio_duration = audiobible.cloned_duration(verse)
				if audio_duration == 0.0:
					continue
				if audio_duration < self.FADE_DURATION * 2:
					audio_duration = self.FADE_DURATION * 2
				segment_duration = self.FADE_DURATION + audio_duration + self.FADE_DURATION
				image_path = os.path.join(BUILD_FOLDER, "images", "psalms",
										  f"{self.psalm.number}.{paragraph.number}.{verse.number}.png")
				verse_video = ffmpeg.input(image_path, loop=1, t=segment_duration)
				verse_video = verse_video.filter('scale', self.width, self.height)
				verse_video = verse_video.filter('format', 'rgba')
				verse_video = verse_video.filter('fade', type='in', alpha=1, duration=self.FADE_DURATION)
				verse_video = verse_video.filter('fade', type='out', alpha=1,
												 start_time=segment_duration - self.FADE_DURATION,
												 duration=self.FADE_DURATION)
				verse_videos.append(verse_video)

		all_videos = [title_video] + verse_videos
		if not all_videos:
			video_concat = ffmpeg.input('anullsrc', f='lavfi', t=duration).video.filter('format', 'rgba').filter('geq', r='0', g='0', b='0', a='0')
		else:
			video_concat = ffmpeg.concat(*all_videos, v=1, a=0).node[0]

		video = self.background
		video = ffmpeg.overlay(video, video_concat, format='auto', shortest=1)
		video = ffmpeg.overlay(video, self.overlay, format='auto', shortest=1)
		return video

	@property
	def audio_stream(self):
		from Audio import PsalmAudio
		psalm_audio = PsalmAudio(self.psalm, music=self.music)
#		if psalm_audio.music:
#			return psalm_audio.enhanced_stream
#		else:
		return psalm_audio.stream

	def export(self):
		self.generate_assets()
		super().export()
















































class ParashahVideo(Video):
	def __init__(self, parashah, size):
		super().__init__(size)
		self.parashah = parashah
		self.audiobible = AudioBible.get_instance()

	@property
	def filename(self):
		return f'torah-{self.parashah.number:02d}-full-{"h" if self.landscape else "v"}.mp4'

	def save_overlay(self):
		overlay = ParashahOverlay(self.parashah)
		overlay.save(landscape=self.landscape)

	def save_slides(self):
		for episode in self.parashah.episodes:
			for paragraph in episode.paragraphs:
				for slide in paragraph.slides:
					slide.save(landscape=self.landscape)

	@property
	def duration(self):
		total = 0.0
		for episode in self.parashah.episodes:
			total += episode.video.duration
		return total

	@property
	def background(self):
		duration = self.duration
#		if self.imageless:
		background = ffmpeg.input(os.path.join(ASSETS_FOLDER, 'back.mp4'), stream_loop=-1, t=duration)
		background = background.filter('scale', self.width, self.height, force_original_aspect_ratio='increase')
		background = background.filter('crop', w=self.width, h=self.height)
		color_hex = f"#{self.parashah.color[0]:02x}{self.parashah.color[1]:02x}{self.parashah.color[2]:02x}"
		color_overlay = ffmpeg.input(f'color=c={color_hex}:s={self.width}x{self.height}', f='lavfi', t=duration)
		background = ffmpeg.filter([background, color_overlay], 'blend', all_mode='overlay', all_opacity=self.BACKGROUND_OPACITY)
#		else:
#			background = ffmpeg.input(f'color=c=black:s={self.width}x{self.height}', f='lavfi', t=duration)
		return background

	@property
	def overlay(self):
		duration = self.duration
		overlay_path = f"build/images/parashot/{self.parashah.number:02d}_parashah_title.png"
		overlay = ffmpeg.input(overlay_path, loop=1, t=duration)
		overlay = overlay.filter('scale', self.width, self.height)
		overlay = overlay.filter('format', 'rgba')
		overlay = overlay.filter('fade', type='in', start_time=0, duration=self.FADE_DURATION)
		overlay = overlay.filter('fade', type='out', start_time=duration - self.FADE_DURATION, duration=self.FADE_DURATION)
		return overlay



	@property
	def video_stream(self):
		video_nodes = []
		#bible_audio = self.parashah.parashot.bible.audio
		
		for episode in self.parashah.episodes:
			for paragraph in episode.paragraphs:
				for slide in paragraph.slides:
					verses_on_slide = set()
					for line in slide.layout:
						for word in line:
							if hasattr(word, 'verse') and word.verse and word.verse.number not in verses_on_slide:
								verses_on_slide.add(word.verse.number)
					
					verses_on_slide = sorted(verses_on_slide)
					for i, verse_num in enumerate(verses_on_slide):
						verse_obj = None
						for line in slide.layout:
							for word in line:
								if hasattr(word, 'verse') and word.verse and word.verse.number == verse_num:
									verse_obj = word.verse
									break
							if verse_obj:
								break
						book_num = verse_obj.chapter.book.number
						chapter_num = verse_obj.chapter.number
						audio_duration = self.audiobible.cloned_duration(verse_obj)
						
						is_first_verse = (i == 0)
						is_last_verse = (i == len(verses_on_slide) - 1)
						segment_duration = self.FADE_DURATION + audio_duration + self.FADE_DURATION
						
						base_image_path = f"build/images/parashot/{episode.parashah.number:02d}.{episode.number:02d}.{paragraph.number:02d}.{slide.slide:1d}.0.png"
						highlight_image_path = f"build/images/parashot/{episode.parashah.number:02d}.{episode.number:02d}.{paragraph.number:02d}.{slide.slide:1d}.{i+1}.png"
						
						base_video = ffmpeg.input(base_image_path, loop=1, t=segment_duration)
						base_video = base_video.filter('scale', self.width, self.height)
						base_video = base_video.filter('format', 'rgba')
						if is_first_verse:
							base_video = base_video.filter('fade', type='in', duration=self.FADE_DURATION)
						if is_last_verse:
							base_video = base_video.filter('fade', type='out', start_time=segment_duration - self.FADE_DURATION, duration=self.FADE_DURATION)
						
						highlight_video = ffmpeg.input(highlight_image_path, loop=1, t=segment_duration)
						highlight_video = highlight_video.filter('scale', self.width, self.height)
						highlight_video = highlight_video.filter('format', 'rgba')
						highlight_video = highlight_video.filter('fade', type='in', alpha=1, duration=self.FADE_DURATION)
						highlight_video = highlight_video.filter('fade', type='out', alpha=1, start_time=segment_duration - self.FADE_DURATION, duration=self.FADE_DURATION)
						
						verse_video = ffmpeg.overlay(base_video, highlight_video)
						video_nodes.append(verse_video)
						
		return ffmpeg.concat(*video_nodes, v=1, a=0).node[0]

	@property
	def audio_stream(self):
		return ffmpeg.input('output/torah-01.01.mp3')

		audio_nodes = []
		bible_audio = self.parashah.parashot.bible.audio
		
		for episode in self.parashah.episodes:
			for paragraph in episode.paragraphs:
				for slide in paragraph.slides:
					verses_on_slide = set()
					for line in slide.layout:
						for word in line:
							if hasattr(word, 'verse') and word.verse and word.verse.number not in verses_on_slide:
								verses_on_slide.add(word.verse.number)
					
					verses_on_slide = sorted(verses_on_slide)
					for i, verse_num in enumerate(verses_on_slide):
						verse_obj = None
						for line in slide.layout:
							for word in line:
								if hasattr(word, 'verse') and word.verse and word.verse.number == verse_num:
									verse_obj = word.verse
									break
						
						book_num = verse_obj.chapter.book.number
						chapter_num = verse_obj.chapter.number
						
						
						audio_file = bible_audio.cloned_mp3(book_num, chapter_num, verse_num)
						audio_stream = ffmpeg.input(audio_file)#.audio.filter('atrim', duration=audio_duration)
						audio_stream = audio_stream.filter('loudnorm', I=-16, TP=-1.5, LRA=11)
						audio_stream = audio_stream.filter('asetpts', 'PTS-STARTPTS')
						
						silence_before = ffmpeg.input('anullsrc=r=44100:cl=stereo', t=self.FADE_DURATION, f='lavfi')
						silence_after = ffmpeg.input('anullsrc=r=44100:cl=stereo', t=self.FADE_DURATION, f='lavfi')
						
						full_audio = ffmpeg.concat(silence_before.audio, audio_stream, silence_after.audio, v=0, a=1)
						audio_nodes.append(full_audio)
						
		audio_concat = ffmpeg.concat(*audio_nodes, v=0, a=1)#.node[0]
		audio_concat = audio_concat.filter('dynaudnorm', f=500, g=31, p=0.75)
		return audio_concat
