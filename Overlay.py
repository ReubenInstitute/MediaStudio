import os
import io
import ffmpeg
from PIL import Image as PILImage, ImageChops, ImageDraw, ImageFont, ImageFilter
from Image import Image, Plate
from Text import Word
from HebrewNumbers import hebrew_fancy_number
import Hebrew
from Asset import Asset
import Media
from pathlib import Path

OUTPUT_FOLDER = Path("output")
ASSETS_FOLDER = Path("assets")
BUILD_FOLDER = Path("build")




class PsalmCover(Image):
	TITLE_FONT	  = 0.167
	NUMBER_FONT	 = 0.361
	TITLE_Y		 = 0.3646
	NUMBER_Y		= 0.6354
	SAFEZONE_CENTER = 0.458

	def __init__(self, psalm, size, cinematic=False):
		super().__init__(size)
		self.psalm = psalm
		self.cinematic = cinematic

	@property
	def filename(self):
		if self.cinematic:
			base = OUTPUT_FOLDER / 'psalms+'
		else:
			base = OUTPUT_FOLDER / 'psalms'
		f = f'psalm{self.psalm.number:03d}.jpg'
		if self.square:
			return str(base / 'covers' / 'square' / f)
		elif self.landscape:
			return str(base / 'covers' / 'horizontal' / f)
		else:
			return str(base / 'covers' / f)

	@property
	def image(self):
		if self.cinematic:
			bg_path = ASSETS_FOLDER / f"{self.psalm.number:03d}.jpg"
			if not bg_path.exists():
				return None
			background = PILImage.open(bg_path).convert('RGB')
		else:
			if self.square:
				bg_path = ASSETS_FOLDER / "back.jpg"
			elif self.landscape:
				bg_path = ASSETS_FOLDER / "back-1280x720.jpg"
			else:
				bg_path = ASSETS_FOLDER / "back-720x1280.jpg"
			background = PILImage.open(bg_path).convert('RGB')
			color_overlay = PILImage.new('RGB', (self.width, self.height), self.psalm.color)
			background_rgba = background.convert('RGBA')
			color_overlay_rgba = color_overlay.convert('RGBA')
			background = PILImage.blend(background_rgba, color_overlay_rgba, alpha=0.7)
			background = background.filter(ImageFilter.GaussianBlur(2))

		self._image = background

		shorter_side = min(self.width, self.height)

		title_font_size  = int(shorter_side * self.TITLE_FONT)
		number_font_size = int(shorter_side * self.NUMBER_FONT)

		title_text = "תהילים"
		title_bbox = self.bbox((0, 0), title_text, "LulavCLM-Bold.otf", title_font_size)
		title_w = title_bbox[2] - title_bbox[0]
		title_h = title_bbox[3] - title_bbox[1]

		number_text = self.psalm.hebrew_number
		number_bbox = self.bbox((0, 0), number_text, "LulavCLM-Bold.otf", number_font_size)
		number_w = number_bbox[2] - number_bbox[0]
		number_h = number_bbox[3] - number_bbox[1]

		if self.width < self.height:
			block_center_y = int(self.height * self.SAFEZONE_CENTER)
		else:
			block_center_y = self.height // 2

		square_top = block_center_y - shorter_side // 2

		title_x = (self.width - title_w) // 2
		title_y = square_top + int(shorter_side * self.TITLE_Y) - title_h // 2

		number_x = (self.width - number_w) // 2
		number_y = square_top + int(shorter_side * self.NUMBER_Y) - number_h // 2

		self.draw_text((title_x, title_y), title_text, "LulavCLM-Bold.otf", title_font_size,
					   color="#ffff00", shadow=True, direction="rtl")
		self.draw_text((number_x, number_y), number_text, "LulavCLM-Bold.otf", number_font_size,
					   color="#ffffff", shadow=True, direction="rtl")

		return self._image









class EpisodeCover(Image):
	def __init__(self, episode, size):
		super().__init__(size)
		self.episode = episode

	@property
	def filename(self):
		return os.path.join(OUTPUT_FOLDER, f"torah-{self.episode.parashah.number:02d}.{self.episode.number:02d}.png")

	@property
	def image(self):
		video_file = os.path.join(ASSETS_FOLDER, "back.mp4")
		frame_data, _ = (ffmpeg.input(video_file, ss=0)
			.output('pipe:', vframes=1, format='image2', vcodec='png')
			.run(capture_stdout=True, quiet=True)
		)
		background = PILImage.open(io.BytesIO(frame_data)).convert('RGB')
		background = background.resize((self.width, self.height), PILImage.LANCZOS)

		color_overlay = PILImage.new('RGB', (self.width, self.height), self.episode.color)
		background_rgba = background.convert('RGBA')
		color_overlay_rgba = color_overlay.convert('RGBA')
		background = PILImage.blend(background_rgba, color_overlay_rgba, alpha=0.7)
		background = background.filter(ImageFilter.GaussianBlur(2))

		self._image = background

		self.draw_text((self.width // 2, 300), "פרשת", "OpenSansHebrewCondensed-Bold.ttf", 90,
					   color="#ffffff", anchor="mm", direction="rtl")
		self.draw_text((self.width // 2, 400), self.episode.parashah.hebrew_name,
					   "OpenSansHebrewCondensed-Bold.ttf", 90, color="#ffffff", anchor="mm", direction="rtl")
		self.draw_text((self.width // 2, 550), str(self.episode.number),
					   "OpenSansHebrewCondensed-Bold.ttf", 180, color="#ffffff", anchor="mm", direction="rtl")

		title_lines = self.episode.hebrew_title.split('\u2028')
		for i, line in enumerate(title_lines):
			y = 700 + i * 120
			self.draw_text((self.width // 2, y), line, "OpenSansHebrewCondensed-Bold.ttf", 100,
						   color="#ffff00", anchor="mm", direction="rtl")

		return self._image




class EpisodeOverlay(Image):
	def __init__(self, episode, size):
		super().__init__(size)
		self.episode = episode

	@property
	def filename(self):
		return os.path.join(BUILD_FOLDER, "images", "parashot", f"{self.episode.parashah.number:02d}_{self.episode.number:02d}_title.png")

	@property
	def image(self):
		image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		logo = PILImage.open("logo.png").resize((108, 108))
		logo = Image.add_shadow(logo)
		image.paste(logo, (306, 100), logo)
		self._image = image
		self.draw_text((360, 248), f"פרשת {self.episode.parashah.hebrew_name}",
				"OpenSansHebrewCondensed-Bold.ttf", 30, color="#ffffff", anchor="mm", direction="rtl")
		self.draw_text((360, 308), self.episode.hebrew_title.replace('\u2028', ' '),
				"OpenSansHebrewCondensed-Regular.ttf", 60, color="#ffffff", anchor="mm", direction="rtl")
		return self._image




class ParashahOverlay(Image):
	def __init__(self, parashah, size):
		super().__init__(size)
		self.parashah = parashah

	@property
	def filename(self):
		return os.path.join(BUILD_FOLDER, "images", "parashot", f"{self.parashah.number:02d}_parashah_title.png")

	@property
	def image(self):
		image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		logo = PILImage.open("logo.png").resize((108, 108))
		image.paste(logo, (306, 100), logo)
		self._image = image
		self.draw_text((360, 248), f"פרשת {self.parashah.hebrew_name}",
				"OpenSansHebrewCondensed-Bold.ttf", 30, color="#ffffff", anchor="mm", direction="rtl")
		return self._image



class PsalmOverlay(Image):
	def __init__(self, psalm, size):
		super().__init__(size)
		self.psalm = psalm

	@property
	def filename(self):
		return os.path.join(BUILD_FOLDER, "images", "psalms", f"{self.psalm.number:03d}_title.png")

	@property
	def image(self):
		self._image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		if self.landscape:
			LOGO_SIZE = 0.15
			logo_size = int(self.height * LOGO_SIZE)
			logo_x = int(self.width * 0.1)
			TITLE_Y = 0.10
			NUMBER_Y = 0.19
			TITLE_FONTSIZE = int(self.height * 30 / 720)   # previously 30
			NUMBER_FONTSIZE = int(self.height * 60 / 720)  # previously 60
		else:
			LOGO_SIZE = 0.15
			logo_size = int(self.width * LOGO_SIZE)
			logo_x = (self.width - logo_size) // 2
			TITLE_Y = 0.20
			TITLE_Y = 0.17
			NUMBER_Y = 0.24
			NUMBER_Y = 0.23
			TITLE_FONTSIZE = int(self.width * 30 / 720)	# previously 30
			NUMBER_FONTSIZE = int(self.width * 60 / 720)   # previously 60
		LOGO_Y = 0.085
		LOGO_Y = 0.045
		logo_y = int(self.height * LOGO_Y)
		logo = PILImage.open("logo.png").resize((logo_size, logo_size))
		logo = Image.add_shadow(logo)
		self._image.paste(logo, (logo_x, logo_y), logo)
		title_y = int(self.height * TITLE_Y)
		self.draw_text((self.width // 2, title_y), "תהילים",
				"LulavCLM-Bold.otf", TITLE_FONTSIZE,
				color="#ffffff", anchor="mm", direction="rtl")
		number_y = int(self.height * NUMBER_Y)
		self.draw_text((self.width // 2, number_y), f"מזמור {self.psalm.hebrew_number}",
				"LulavCLM-Bold.otf", NUMBER_FONTSIZE,
				color="#ffffff", anchor="mm", direction="rtl")
		return self._image










class NarrationParagraphVersePlate(Plate):
	def __init__(self, layout, verse, size):
		super().__init__(size)
		self.layout = layout
		self.verse = verse

	@property
	def footer(self):
		return ''

	@property
	def highlight(self):
		return self.verse if self.verse != 0 else None

	@property
	def image(self):
		self._image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		header_height = int(self.height * 0.20)
		safe_height = int(self.height * 0.60)
		footer_height = int(self.height * 0.20)
		margin = int(self.width * 0.15)
		available_width = self.width - 2 * margin
		font_size = 50
		layout = [[Word(Hebrew.strip_cantillation(Hebrew.strip_hebrew_punctuation(Hebrew.strip_yhwh(word.text), strip_maqaf=False)), word.verse) for word in line] for line in self.layout]

		temp_canvas = ImageDraw.Draw(PILImage.new('RGB', (1, 1)))
		total_height = 0
		all_sublines = []
		for visual_line in layout:
			sublines = Plate.wrap(visual_line, "SBLHebrew.ttf", font_size, available_width)
			for line_words in sublines:
				if line_words:
					text = ' '.join(word.text for word in line_words)
					box = Image.bbox((0, 0), text, "SBLHebrew.ttf", font_size, direction="rtl")
					line_height = box[3] - box[1]
					total_height += line_height
					all_sublines.append((line_words, line_height))

		current_y = header_height + (safe_height - total_height) // 2
		line_index = 0
		for visual_line in layout:
			sublines = Plate.wrap(visual_line, "SBLHebrew.ttf", font_size, available_width)
			for j, line_words in enumerate(sublines):
				if line_words and line_index < len(all_sublines):
					line_height = all_sublines[line_index][1]
					draw_y = current_y
					if j == len(sublines) - 1:
						self.draw_centered(margin, draw_y, available_width, line_words,
										   "SBLHebrew.ttf", font_size, "#ffffff",
										   rtl=True, verse=self.highlight)
					else:
						self.draw_justified(margin, draw_y, available_width, line_words,
											"SBLHebrew.ttf", font_size, "#ffffff",
											rtl=True, verse=self.highlight)
					current_y += line_height * 1.0
					line_index += 1

		if self.footer:
			self.draw_text((self.width // 2, header_height + safe_height + (footer_height - 200) // 2),
					self.footer, "OpenSansHebrewCondensed-Bold.ttf", 30,
					color="#ffffff", anchor="mm", direction="rtl")
		return self._image


class EpisodeParagraphVersePlate(NarrationParagraphVersePlate):
	FOLDER = "parashot"

	def __init__(self, episode, paragraph, verse, size):
		layout = episode.paragraphs[paragraph-1].layout
		super().__init__(layout, verse, size)
		self.episode = episode
		self.paragraph = paragraph

	@property
	def filename(self):
		return os.path.join(BUILD_FOLDER, "images", self.FOLDER,
							f"{self.episode.parashah.number}.{self.episode.number}.{self.paragraph}.{self.verse}.png")

	@property
	def highlight(self):
		return self.episode.verses[self.verse - 1].number if self.verse != 0 else None

	@property
	def footer(self):
		if self.verse == 0:
			return ''
		verse_obj = self.episode.verses[self.verse - 1]
		book_name = Hebrew.strip_diacritics(verse_obj.chapter.book.hebrew_name)
		chapter_num = verse_obj.chapter.hebrew_fancy_number
		verse_num = verse_obj.hebrew_fancy_number
		return f"ספר {book_name} • פרק {chapter_num} • פסוק {verse_num}"



























class PoemVersePlate(Plate):
	def __init__(self, slide, verse_num, size, highlight=0):
		super().__init__(size)
		self.slide = slide
		self.verse_num = verse_num
		self.highlight = highlight		# number of the word in yellow, 0 for none

	@property
	def footer(self):
		return ''

	@property
	def image(self):
		self._image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))

		header_height = int(self.height * 0.20)
		safe_height = int(self.height * 0.60)
		footer_height = int(self.height * 0.20)
		margin = int(self.width * 0.10)
		available_width = self.width - 2 * margin

		font = Plate.expand(self.slide.layout, "OpenSansHebrewRI-Regular.ttf", available_width, safe_height)

		total_height = 0
		for line in self.slide.layout:
			text = ' '.join(word.text for word in line)
			box = Image.bbox((0, 0), text, "OpenSansHebrewRI-Regular.ttf", font.size)
			total_height += (box[3] - box[1])

		y = header_height + (safe_height - total_height) // 2

		first = 1
		for line in self.slide.layout:
			text = ' '.join(word.text for word in line)
			box = Image.bbox((0, 0), text, "OpenSansHebrewRI-Regular.ttf", font.size)
			line_height = box[3] - box[1]
			self.draw_centered(0, y, self.width, line, "OpenSansHebrewRI-Regular.ttf", font.size, "#ffffff", rtl=True,
					highlight=self.highlight, first=first)
			first += len(line)
			y += line_height


		if self.footer:
			print (self.footer)
			print (len(self.footer))
			self.draw_text((self.width // 2, header_height + safe_height + footer_height // 2),
					self.footer, "OpenSansHebrewCondensed-Bold.ttf", 35,
					color="#ffffff", anchor="mm", direction="rtl")
		return self._image














class PoemArticleOverlay(Asset):
	def __init__(self, article, size):
		super().__init__(size)
		self.article = article

	def save(self):
		image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		filename = f"build/images/articles/{self.article.slug}_title.png"
		os.makedirs(os.path.dirname(filename), exist_ok=True)
		image.save(filename)

class NarrationArticleOverlay(Asset):
	def __init__(self, article, size):
		super().__init__(size)
		self.article = article

	def save(self):
		image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		filename = f"build/images/articles/{self.article.slug}_title.png"
		os.makedirs(os.path.dirname(filename), exist_ok=True)
		image.save(filename)




class PsalmVerseSlide(Asset):
	def __init__(self, psalm, paragraph, verse, size):
		super().__init__(size)
		self.psalm = psalm
		self.paragraph = paragraph
		self.verse = verse

	@property
	def layout(self):
		return self.psalm.paragraphs[self.paragraph-1].layout[self.verse-1]

	def export(self):
		# the plain plate, then one for every word with that word in yellow
		PsalmVersePlate(self, self.size).export()
		for number in range(1, sum(len(line) for line in self.layout) + 1):
			PsalmVersePlate(self, self.size, number).export()


class PsalmVersePlate(PoemVersePlate):
	FOLDER = "psalms"

	def __init__(self, slide, size, highlight=0):
		super().__init__(slide, slide.verse, size, highlight)

	@property
	def filename(self):
		word = f".w{self.highlight}" if self.highlight else ""
		return os.path.join(BUILD_FOLDER, "images", self.FOLDER,
				f"{self.slide.psalm.number}.{self.slide.paragraph}.{self.slide.verse}{word}.png")

	@property
	def footer(self):
		return self.slide.layout[0][0].verse.hebrew_fancy_number



class PsalmVersePreview(Image):
	def __init__(self, slide, size):
		super().__init__(size)
		self.slide = slide

	@property
	def background(self):
		from Video import Video
		still = BUILD_FOLDER / "images" / f"back-{self.width}x{self.height}.png"
		if not still.exists():
			still.parent.mkdir(parents=True, exist_ok=True)
			background = ffmpeg.input(str(ASSETS_FOLDER / f"back-{self.width}x{self.height}.mp4"), ss=5)
			background = background.filter('scale', self.width, self.height, force_original_aspect_ratio='increase')
			background = background.filter('crop', w=self.width, h=self.height)
			background.output(str(still), vframes=1).run(overwrite_output=True, quiet=True)
		background = PILImage.open(still).convert('RGB')
		color = PILImage.new('RGB', background.size, self.slide.psalm.color)
		return PILImage.blend(background, ImageChops.overlay(background, color), Video.BACKGROUND_OPACITY)

	@property
	def image(self):
		self._image = self.background.convert('RGBA')
		self._image.alpha_composite(PsalmOverlay(self.slide.psalm, self.size).image)
		self._image.alpha_composite(PsalmVersePlate(self.slide, self.size).image)
		return self._image



class EpisodeParagraphSlide(Asset):
	def __init__(self, episode, paragraph, size):
		super().__init__(size)
		self.episode = episode
		self.paragraph = paragraph

	def export(self):
		print (f"SIZE {self.size}")
		layout = self.episode.paragraphs[self.paragraph-1].layout
		paragraph = self.episode.paragraphs[self.paragraph-1]
		verses = [self.episode.verses.index(verse) + 1 for verse in paragraph.verses]
		base_plate = EpisodeParagraphVersePlate(self.episode, self.paragraph, verse=0, size=self.size)
		base_plate.export()
		for v in verses:
			plate = EpisodeParagraphVersePlate(self.episode, self.paragraph, verse=v, size=self.size)
			plate.export()













class Slide(Image):
	def __init__(self, layout, size):
		super().__init__(size)
		self.layout = layout

class PoemArticleSlide(Slide):
	def __init__(self, layout, article, paragraph, slide):
		super().__init__(layout)
		self.article = article
		self.paragraph = paragraph
		self.slide = slide

	def save(self, landscape=False):
		self.landscape = landscape
		image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		filename = f"build/images/articles/{self.article:03d}.{self.paragraph:02d}.{self.slide:1d}.{self.verse:1d}.png"
		os.makedirs(os.path.dirname(filename), exist_ok=True)
		image.save(filename)

class NarrationArticleSlide(Slide):
	def __init__(self, layout, article, paragraph, slide):
		super().__init__(layout)
		self.article = article
		self.paragraph = paragraph
		self.slide = slide

	def save(self, landscape=False):
		self.landscape = landscape
		image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		filename = f"build/images/articles/{self.article:03d}.{self.paragraph:02d}.{self.slide:1d}.{self.verse:1d}.png"
		os.makedirs(os.path.dirname(filename), exist_ok=True)
		image.save(filename)





class PsalmSlide(Slide):
	def __init__(self, layout, psalm, paragraph, slide, size):
		super().__init__(layout, size)
		self.psalm = psalm
		self.paragraph = paragraph
		self.slide = slide

	@property
	def filename(self):
		return os.path.join(BUILD_FOLDER, "images", "psalms", f"{self.psalm:03d}.{self.paragraph:02d}.{self.slide:1d}.png")

	@property
	def image(self):
		image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
		self._image = image

		header_height = int(self.height * 0.20)
		safe_height = int(self.height * 0.60)
		footer_height = int(self.height * 0.20)
		margin = int(self.width * 0.10)
		available_width = self.width - 2 * margin

		font = Slide.expand(self.layout, "OpenSansHebrewRI-Regular.ttf", available_width, safe_height)

		total_height = 0
		for line in self.layout:
			text = ' '.join(word.text for word in line)
			box = Image.bbox((0, 0), text, "OpenSansHebrewRI-Regular.ttf", font.size)
			total_height += (box[3] - box[1])

		y = header_height + (safe_height - total_height) // 2
		verse_num = self.layout[0][0].verse.number

		for line in self.layout:
			text = ' '.join(word.text for word in line)
			box = Image.bbox((0, 0), text, "OpenSansHebrewRI-Regular.ttf", font.size)
			line_height = box[3] - box[1]
			self.draw_centered_slide(0, y, self.width, line, "OpenSansHebrewRI-Regular.ttf", font.size, "#ffff00", rtl=True, verse=verse_num)
			y += line_height

		if self.layout and self.layout[0] and self.layout[0][0] and self.layout[0][0].verse:
			verse_num = self.layout[0][0].verse.hebrew_number
			self.draw_text((self.width // 2, header_height + safe_height + footer_height // 2), verse_num,
						   "OpenSansHebrewCondensed-Bold.ttf", 35, color="#ffffff", anchor="mm", direction="rtl")

		return self._image




class ParashahSlide(Slide):
	def __init__(self, layout, parashah, episode, paragraph, slide):
		super().__init__(layout)
		self.parashah = parashah
		self.episode = episode
		self.paragraph = paragraph
		self.slide = slide

	def save(self, landscape=False):
		self.landscape = landscape
		verses = set()
		for line in self.layout:
			for word in line:
				if hasattr(word, 'verse') and word.verse:
					verses.add(word.verse.number)
		verses = sorted(verses)
		header_height = int(self.height * 0.20)
		safe_height = int(self.height * 0.60)
		footer_height = int(self.height * 0.20)
		margin = int(self.width * 0.15)
		available_width = self.width - 2 * margin
		font_size = 50
		base_filename = f"build/images/parashot/{self.parashah:02d}.{self.episode:02d}.{self.paragraph:02d}.{self.slide:1d}.0.png"
		os.makedirs(os.path.dirname(base_filename), exist_ok=True)
		temp_canvas = ImageDraw.Draw(PILImage.new('RGB', (1, 1)))
		total_height = 0
		all_sublines = []
		for visual_line in self.layout:
			sublines = Image.wrap(visual_line, "TaameyFrankCLM-Medium.ttf", font_size, available_width)
			for line_words in sublines:
				if line_words:
					text = ' '.join(word.text for word in line_words)
					box = Image.bbox(temp_canvas, (0, 0), text, "TaameyFrankCLM-Medium.ttf", font_size, direction="rtl")
					line_height = box[3] - box[1]
					total_height += line_height
					all_sublines.append((line_words, line_height))
		for i, verse_num in enumerate([0] + list(verses)):
			image = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
			canvas = ImageDraw.Draw(image)
			current_y = header_height + (safe_height - total_height) // 2
			line_index = 0
			for visual_line in self.layout:
				sublines = Image.wrap(visual_line, "TaameyFrankCLM-Medium.ttf", font_size, available_width)
				for j, line_words in enumerate(sublines):
					if line_words and line_index < len(all_sublines):
						line_height = all_sublines[line_index][1]
						draw_y = current_y
						if j == len(sublines) - 1:
							Image.draw_centered_slide(canvas, margin, draw_y, available_width, line_words, "TaameyFrankCLM-Medium.ttf", font_size, "#ffffff", rtl=True, verse=verse_num if verse_num != 0 else None)
						else:
							Image.draw_justified_slide(canvas, margin, draw_y, available_width, line_words, "TaameyFrankCLM-Medium.ttf", font_size, "#ffffff", rtl=True, verse=verse_num if verse_num != 0 else None)
						current_y += line_height * 1.0
						line_index += 1
			if verse_num != 0:
				verse_obj = None
				for line in self.layout:
					for word in line:
						if hasattr(word, 'verse') and word.verse and word.verse.number == verse_num:
							verse_obj = word.verse
							break
					if verse_obj:
						break
				if verse_obj:
					book_name = Hebrew.strip_diacritics(verse_obj.chapter.book.hebrew_name)
					chapter_num = verse_obj.chapter.hebrew_fancy_number
					verse_num_display = verse_obj.hebrew_fancy_number
					footer_text = f"ספר {book_name} • פרק {chapter_num} • פסוק {verse_num_display}"
				else:
					footer_text = f"פסוק {hebrew_fancy_number(verse_num)}"
				Image.draw_text(canvas, (self.width // 2, header_height + safe_height + (footer_height - 200) // 2), footer_text, "OpenSansHebrewCondensed-Bold.ttf", 30, color="#ffffff", anchor="mm", direction="rtl")
			if verse_num == 0:
				image.save(base_filename)
			else:
				highlight_filename = f"build/images/parashot/{self.parashah:02d}.{self.episode:02d}.{self.paragraph:02d}.{self.slide:1d}.{i}.png"
				image.save(highlight_filename)

