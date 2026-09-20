from pathlib import Path

FADE_DURATION = 0.5

AUDIO_FOLDER	= Path("audio")
ASSETS_FOLDER   = Path("assets")
OUTPUT_FOLDER   = Path("output")

TITLES_FOLDER   = AUDIO_FOLDER / "titles"

PSALMS_FOLDER	  = OUTPUT_FOLDER / "psalms"
PSALMS_PLUS_FOLDER = OUTPUT_FOLDER / "psalms+"
TORAH_FOLDER	   = OUTPUT_FOLDER / "torah"

LIBRARY_VIDEO_FOLDER   = PSALMS_FOLDER
SCORE_VIDEO_FOLDER	 = PSALMS_PLUS_FOLDER
CINEMATIC_VIDEO_FOLDER = PSALMS_PLUS_FOLDER / "cinematic"

LIBRARY_AUDIO_FOLDER = PSALMS_FOLDER
SCORE_AUDIO_FOLDER   = PSALMS_PLUS_FOLDER

LIBRARY_COVERS_FOLDER	 = PSALMS_FOLDER / "covers"
PSALMS_PLUS_COVERS_FOLDER = PSALMS_PLUS_FOLDER / "covers"

HORIZONTAL_SUBFOLDER = "horizontal"
SQUARE_SUBFOLDER	 = "square"


class Asset:
	def __init__(self, size):
		self.size = size

	@property
	def width(self):
		return self.size[0]

	@property
	def height(self):
		return self.size[1]

	@property
	def landscape(self):
		return self.width > self.height

	@property
	def square(self):
		return self.width == self.height
