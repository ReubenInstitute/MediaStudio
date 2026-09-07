import os
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageFilter
from Asset import Asset
from Text import Word
import Hebrew
from fontTools.ttLib import TTFont

from pathlib import Path

FONT_FOLDER = "fonts"
_extreme_chars_cache = {}


def _get_extreme_chars(filename):
	if filename in _extreme_chars_cache:
		return _extreme_chars_cache[filename]

	font_path = Path(FONT_FOLDER) / filename
	pil_font = ImageFont.truetype(str(font_path), 80)

	tt = TTFont(font_path)
	cmap = tt.getBestCmap()

	def has_glyph(s):
		return all(ord(c) in cmap for c in s)

	temp_image = PILImage.new('RGB', (1000, 1000))
	canvas = ImageDraw.Draw(temp_image)

	top_extreme = ""
	min_top_y = 10000
	for letter in Hebrew.LETTERS:
		if not has_glyph(letter):
			continue
		for cant in Hebrew.UPPER_CANTILLATIONS:
			if not has_glyph(cant):
				continue
			test_text = letter + cant
			bbox = canvas.textbbox((500, 500), test_text, font=pil_font, direction="rtl")
			if bbox and bbox[1] < min_top_y:
				min_top_y = bbox[1]
				top_extreme = test_text

	bottom_extreme = ""
	max_bottom_y = -10000
	for letter in Hebrew.LETTERS:
		if not has_glyph(letter):
			continue
		for diac in Hebrew.DIACRITICS + Hebrew.HATAFS:
			if not has_glyph(diac):
				continue
			test_text = letter + diac
			bbox = canvas.textbbox((500, 500), test_text, font=pil_font, direction="rtl")
			if bbox and bbox[3] > max_bottom_y:
				max_bottom_y = bbox[3]
				bottom_extreme = test_text

	extreme_chars = top_extreme + bottom_extreme
	_extreme_chars_cache[filename] = extreme_chars
	return extreme_chars


class Image(Asset):
	def __init__(self, size):
		super().__init__(size)
		self._image = PILImage.new('RGBA', size, (0, 0, 0, 0))

	def export(self):
		os.makedirs(os.path.dirname(self.filename), exist_ok=True)
		image = self.image
		if self.filename.endswith("jpg"):
			image = self.image.convert('RGB')
		image.save(self.filename)


	@staticmethod
	def add_shadow(image):
		alpha = image.getchannel('A')
		pad = 4 + 4*1 + 5*2
		pad = 20
		shadow_size = (alpha.width + pad*2, alpha.height + pad*2)
		shadow_mask = PILImage.new('L', shadow_size, 0)
		shadow_mask.paste(alpha, (pad, pad))
		for _ in range(4):
			shadow_mask = shadow_mask.filter(ImageFilter.MaxFilter(3))
		shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(5))
		crop_x = (shadow_size[0] - (alpha.width + 8)) // 2
		crop_y = (shadow_size[1] - (alpha.height + 8)) // 2
		shadow_mask = shadow_mask.crop((crop_x, crop_y, crop_x + alpha.width + 8, crop_y + alpha.height + 8))
		shadow_image = PILImage.new('RGBA', (alpha.width + 8, alpha.height + 8), (0, 0, 0, 250))
		shadow_image.putalpha(shadow_mask)
		composite = shadow_image.copy()
		composite.paste(image, (4, 4), image)
		return composite




	@staticmethod
	def bbox(xy, text, font_filename, font_size, direction=None):
		temp_img = PILImage.new('RGB', (1, 1))
		temp_canvas = ImageDraw.Draw(temp_img)
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		extreme_chars = _get_extreme_chars(font_filename)
		if not extreme_chars:
			return temp_canvas.textbbox(xy, text, font=font, direction=direction)
		full_bbox = temp_canvas.textbbox(xy, text + extreme_chars, font=font, direction=direction)
		text_bbox = temp_canvas.textbbox(xy, text, font=font, direction=direction)
		return (text_bbox[0], full_bbox[1], text_bbox[2], full_bbox[3])


	def draw_text(self, xy, text, font_filename, font_size, color=None, shadow=True, anchor=None, direction=None):
		actual_color = color if color is not None else "#FFFFFF"
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		extreme_chars = _get_extreme_chars(font_filename)
	
		# Use a temporary canvas for measurement
		temp_measure = PILImage.new('RGB', (1, 1))
		temp_canvas = ImageDraw.Draw(temp_measure)
		text_bbox = temp_canvas.textbbox((0, 0), text, font=font, anchor=None, direction=direction)
		full_bbox = temp_canvas.textbbox((0, 0), text + extreme_chars, font=font, anchor=None, direction=direction)

		# Create a temporary image for the text layer
		temp_image = PILImage.new('RGBA', (text_bbox[2] - text_bbox[0], full_bbox[3] - full_bbox[1]), (0, 0, 0, 0))
		temp_draw = ImageDraw.Draw(temp_image)
	
		if anchor == "mm":
			temp_draw.text((0, -full_bbox[1]), text, fill=actual_color, font=font, direction=direction)
		else:
			temp_draw.text((0, -full_bbox[1]), text, fill=actual_color, font=font, direction=direction)
	
		if not shadow:
			if anchor == "mm":
				self._image.paste(temp_image, (int(xy[0] - (text_bbox[2] - text_bbox[0]) / 2), int(xy[1] - (full_bbox[3] - full_bbox[1]) / 2)), temp_image)
			else:
				self._image.paste(temp_image, (int(xy[0]), int(xy[1])), temp_image)
			return

		shadowed_image = self.add_shadow(temp_image)

		if anchor == "mm":
			self._image.paste(shadowed_image, (int(xy[0] - (shadowed_image.width / 2)), int(xy[1] - (shadowed_image.height / 2))), shadowed_image)
		else:
			self._image.paste(shadowed_image, (int(xy[0] - 4), int(xy[1] - 4)), shadowed_image)




class Plate(Image):
	def __init__(self, size):
		super().__init__(size)

	@staticmethod
	def expand(lines, font_filename, width, height):
		font_size = 200
		best_font = ImageFont.load_default()
		while font_size > 20:
			try:
				current_font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
			except IOError:
				current_font = ImageFont.load_default()
			total_height = 0
			max_line_width = 0
			for line in lines:
				text = ' '.join(word.text for word in line)
				box = Image.bbox((0, 0), text, font_filename, font_size)
				total_height += (box[3] - box[1]) * 1.3
				max_line_width = max(max_line_width, box[2] - box[0])
			if total_height < height * 0.9 and max_line_width < width * 0.9:
				best_font = current_font
				break
			font_size -= 1
		return best_font

	@staticmethod
	def wrap(words, font_filename, font_size, width):
		if not words:
			return []
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		space_width = Image.bbox((0, 0), ' ', font_filename, font_size)[2]
		results = []
		current_line = []
		current_width = 0
		for word in words:
			word_width = Image.bbox((0, 0), word.text, font_filename, font_size)[2]
			if current_line and current_width + space_width + word_width > width:
				results.append(current_line)
				current_line = [word]
				current_width = word_width
			else:
				if current_line:
					current_width += space_width
				current_line.append(word)
				current_width += word_width
		if current_line:
			results.append(current_line)
		return results

	def draw_left_aligned(self, x, y, width, words, font_filename, font_size, color, rtl=False, verse=None):
		if rtl:
			words = list(reversed(words))
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		space_width = Image.bbox((0, 0), ' ', font_filename, font_size)[2]
		current_x = x
		for word in words:
			word_width = Image.bbox((0, 0), word.text, font_filename, font_size)[2]
			self.draw_text((int(current_x), int(y)), word.text, font_filename, font_size,
						   color=("#ffff00" if verse and word.verse.number == verse else color),
						   shadow=True, direction="rtl" if rtl else "ltr")
			current_x += word_width + space_width

	def draw_right_aligned(self, x, y, width, words, font_filename, font_size, color, rtl=False, verse=None):
		if rtl:
			words = list(reversed(words))
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		space_width = Image.bbox((0, 0), ' ', font_filename, font_size)[2]
		total_width = sum(Image.bbox((0, 0), word.text, font_filename, font_size)[2] for word in words)
		total_width += space_width * (len(words) - 1)
		current_x = x + width - total_width
		for word in words:
			word_width = Image.bbox((0, 0), word.text, font_filename, font_size)[2]
			self.draw_text((int(current_x), int(y)), word.text, font_filename, font_size,
						   color=("#ffff00" if verse and word.verse.number == verse else color),
						   shadow=True, direction="rtl" if rtl else "ltr")
			current_x += word_width + space_width

	def draw_justified(self, x, y, width, words, font_filename, font_size, color, rtl=False, verse=None):
		if rtl:
			words = list(reversed(words))
		if not words:
			return
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		total_word_width = sum(Image.bbox((0, 0), word.text, font_filename, font_size)[2] for word in words)
		num_gaps = len(words) - 1
		if num_gaps > 0:
			extra_space = (width - total_word_width) / num_gaps
			spacing = extra_space
		else:
			spacing = 0
		current_x = x
		for i, word in enumerate(words):
			word_width = Image.bbox((0, 0), word.text, font_filename, font_size)[2]
			self.draw_text((int(current_x), int(y)), word.text, font_filename, font_size,
						   color=("#ffff00" if verse and word.verse.number == verse else color),
						   shadow=True, direction="rtl" if rtl else "ltr")
			current_x += word_width + spacing

	def draw_centered(self, x, y, width, words, font_filename, font_size, color, rtl=False, verse=None):
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		if verse is None:
			text = ' '.join(word.text for word in words)
			bbox = Image.bbox((0, 0), text, font_filename, font_size)
			text_width = bbox[2] - bbox[0]
			center_x = x + (width - text_width) // 2
			self.draw_text((int(center_x), int(y)), text, font_filename, font_size,
						   color=color, shadow=True, direction="rtl" if rtl else "ltr")
		else:
			if rtl:
				words = list(reversed(words))
			space_width = Image.bbox((0, 0), ' ', font_filename, font_size)[2]
			total_width = sum(Image.bbox((0, 0), word.text, font_filename, font_size)[2] for word in words)
			total_width += space_width * (len(words) - 1)
			current_x = x + (width - total_width) // 2
			for word in words:
				word_width = Image.bbox((0, 0), word.text, font_filename, font_size)[2]
				self.draw_text((int(current_x), int(y)), word.text, font_filename, font_size,
							   color=("#ffff00" if word.verse and word.verse.number == verse else color),
							   shadow=True, direction="rtl" if rtl else "ltr")
				current_x += word_width + space_width
