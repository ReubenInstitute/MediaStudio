from pathlib import Path

FADE_DURATION = 0.5

ROOT = Path(__file__).resolve().parent
INSTALLED = ROOT == Path("/usr/share/scripturesstudio")

if INSTALLED:
	ASSETS_FOLDER = Path("/var/lib/scripturesstudio/assets")
	FONTS_FOLDER  = Path("/usr/share/fonts/reubeninstitute")
	OUTPUT_FOLDER = Path("/var/lib/scripturesstudio/output")
	STATIC_FOLDER = ROOT / "@@"
	TEMPLATES_FOLDER = ROOT / "templates"
else:
	ASSETS_FOLDER = ROOT / "assets"
	FONTS_FOLDER  = ROOT / "fonts"
	OUTPUT_FOLDER = ROOT / "output"
	STATIC_FOLDER = ROOT
	TEMPLATES_FOLDER = ROOT / "templates"

BUILD_FOLDER = Path.home() / ".scripturesstudio" / "build"

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
