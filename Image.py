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
	font_path = Path(FONT_FOLDER) / filename
	key = (filename, font_path.stat().st_mtime)
	if key in _extreme_chars_cache:
		return _extreme_chars_cache[key]

	pil_font = ImageFont.truetype(str(font_path), 80)

	tt = TTFont(font_path)
	cmap = tt.getBestCmap()

	def has_glyph(s):
		return all(ord(c) in cmap for c in s)

	temp_image = PILImage.new('RGB', (1000, 1000))
	canvas = ImageDraw.Draw(temp_image)

	top_extreme = ""
	min_top_y = 10000
	for letter in Hebrew.PLAIN_LETTERS:
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
	for letter in Hebrew.PLAIN_LETTERS:
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
	_extreme_chars_cache[key] = extreme_chars
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


	# Two-layer drop shadow: a wide soft glow for separation from the video, and a tight dark core for
	# contact definition. Pure gaussian blur (no dilation, which makes square/blocky edges).
	SHADOW_OFFSET = (2, 3)
	SHADOW_LAYERS = ((7, 150), (2, 200))	# (blur radius, opacity 0-255)
	SHADOW_PAD = 3 * max(r for r, _ in SHADOW_LAYERS) + max(SHADOW_OFFSET)	# gaussian tail is ~3 sigma; keeps it uncut

	@staticmethod
	def add_shadow(image):
		"""Return a bigger RGBA image (grown by SHADOW_PAD on every side) with a soft shadow behind the given image."""
		pad = Image.SHADOW_PAD
		ox, oy = Image.SHADOW_OFFSET
		size = (image.width + pad*2, image.height + pad*2)
		alpha = PILImage.new('L', size, 0)
		alpha.paste(image.getchannel('A'), (pad + ox, pad + oy))
		composite = PILImage.new('RGBA', size, (0, 0, 0, 0))
		for radius, opacity in Image.SHADOW_LAYERS:
			mask = alpha.filter(ImageFilter.GaussianBlur(radius)).point(lambda a: a * opacity // 255)
			layer = PILImage.new('RGBA', size, (0, 0, 0, 0))
			layer.putalpha(mask)
			composite.alpha_composite(layer)
		composite.alpha_composite(image.convert('RGBA'), (pad, pad))
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
			self._image.paste(shadowed_image, (int(xy[0] - self.SHADOW_PAD), int(xy[1] - self.SHADOW_PAD)), shadowed_image)




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
				text = ''.join(word.text + word.spacer for word in line).rstrip()
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
			word_width = Image.bbox((0, 0), word.text + word.spacer.strip(), font_filename, font_size)[2]
			gap = 0 if current_line and current_line[-1].spacer == Hebrew.MAQAF else space_width
			if current_line and current_width + gap + word_width > width:
				results.append(current_line)
				current_line = [word]
				current_width = word_width
			else:
				if current_line:
					current_width += gap
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
		widths = [Image.bbox((0, 0), word.text + word.spacer.strip(), font_filename, font_size)[2] for word in words]
		# a word joined to the next one with a maqaf takes no gap
		gaps = [k for k in range(len(words) - 1) if (words[k + 1] if rtl else words[k]).spacer != Hebrew.MAQAF]
		spacing = (width - sum(widths)) / len(gaps) if gaps else 0
		current_x = x
		for i, word in enumerate(words):
			self.draw_text((int(current_x), int(y)), word.text + word.spacer.strip(), font_filename, font_size,
						   color=("#ffff00" if verse and word.verse.number == verse else color),
						   shadow=True, direction="rtl" if rtl else "ltr")
			current_x += widths[i] + (spacing if i in gaps else 0)

	def draw_centered(self, x, y, width, words, font_filename, font_size, color, rtl=False, verse=None, highlight=None, first=1):
		font = ImageFont.truetype(os.path.join(FONT_FOLDER, font_filename), font_size)
		if verse is None and highlight is None:
			text = ''.join(word.text + word.spacer for word in words).rstrip()
			bbox = Image.bbox((0, 0), text, font_filename, font_size)
			text_width = bbox[2] - bbox[0]
			center_x = x + (width - text_width) // 2
			self.draw_text((int(center_x), int(y)), text, font_filename, font_size,
						   color=color, shadow=True, direction="rtl" if rtl else "ltr")
		else:
			# the number of the word, from first, is what highlight refers to
			numbered = list(enumerate(words, first))
			if rtl:
				numbered = list(reversed(numbered))
			space_width = Image.bbox((0, 0), ' ', font_filename, font_size)[2]
			widths = [Image.bbox((0, 0), word.text + word.spacer.strip(), font_filename, font_size)[2] for _, word in numbered]
			# a word joined to the next one with a maqaf takes no space
			gaps = [0 if (numbered[k + 1][1] if rtl else word).spacer == Hebrew.MAQAF else space_width
					for k, (_, word) in enumerate(numbered[:-1])]
			current_x = x + (width - sum(widths) - sum(gaps)) // 2
			for k, (number, word) in enumerate(numbered):
				if highlight is not None:
					yellow = number == highlight
				else:
					yellow = word.verse and word.verse.number == verse
				self.draw_text((int(current_x), int(y)), word.text + word.spacer.strip(), font_filename, font_size,
							   color="#ffff00" if yellow else color,
							   shadow=True, direction="rtl" if rtl else "ltr")
				current_x += widths[k] + (gaps[k] if k < len(gaps) else 0)
