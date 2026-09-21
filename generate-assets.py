import ffmpeg
import os
import re
import sys
from PIL import Image as PILImage
import io

SOURCE = 'assets/back.orig.mp4'
SQUARE_SCALE = 0.9

def extract_frame(video_path, output_path, time=2):
	frame_data, _ = (
		ffmpeg
		.input(video_path, ss=time)
		.output('pipe:', vframes=1, format='image2', vcodec='png')
		.run(capture_stdout=True, quiet=True)
	)
	img = PILImage.open(io.BytesIO(frame_data)).convert('RGB')
	img.save(output_path, quality=95)

def make_square():
	(
		ffmpeg
		.input(SOURCE)
		.filter('crop',
			w='min(iw,ih)-mod(min(iw,ih),2)',
			h='min(iw,ih)-mod(min(iw,ih),2)',
			x='(iw-min(iw,ih)+mod(min(iw,ih),2))/2',
			y='(ih-min(iw,ih)+mod(min(iw,ih),2))/2'
		)
		.filter('format', pix_fmts='yuv420p')
		.output('assets/back_full.mp4',
			vcodec='libx264',
			preset='fast',
			crf=18,
			pix_fmt='yuv420p',
			movflags='+faststart')
		.overwrite_output()
		.run()
	)

	probe = ffmpeg.probe('assets/back_full.mp4')
	width = int(probe['streams'][0]['width'])
	new_side = int(width * SQUARE_SCALE)
	if new_side % 2 != 0:
		new_side -= 1

	print('assets/back.mp4')
	(
		ffmpeg
		.input('assets/back_full.mp4')
		.filter('scale', new_side, new_side)
		.output('assets/back.mp4',
			vcodec='libx264',
			preset='fast',
			crf=18,
			pix_fmt='yuv420p',
			movflags='+faststart')
		.overwrite_output()
		.run()
	)
	os.remove('assets/back_full.mp4')

def make_orientation(input_file, target_w, target_h, output_file, square=False):
	if target_w > target_h:
		crop_w = 'iw'
		crop_h = f'iw*{target_h}/{target_w}'
	else:
		crop_h = 'ih'
		crop_w = f'ih*{target_w}/{target_h}'

	print(output_file)
	stream = ffmpeg.input(input_file)
	if square:
		stream = stream.filter('crop', w='ih', h='ih', x='(iw-ow)/2', y=0)
	(
		stream
		.filter('crop',
			w=crop_w,
			h=crop_h,
			x='(iw-ow)/2',
			y='(ih-oh)/2'
		)
		.filter('scale', target_w, target_h)
		.output(output_file,
			vcodec='libx264',
			preset='fast',
			crf=18,
			pix_fmt='yuv420p',
			movflags='+faststart')
		.overwrite_output()
		.run()
	)

def generate_videos():
	make_square()
	make_orientation('assets/back.mp4', 720, 1280, 'assets/back-720x1280.mp4')
	make_orientation('assets/back.mp4', 1280, 720, 'assets/back-1280x720.mp4')
	make_orientation(SOURCE, 1920, 1080, 'assets/back-1920x1080.mp4', square=True)

def generate_covers():
	for name in ('back', 'back-720x1280', 'back-1280x720'):
		print(f'assets/{name}.jpg')
		extract_frame(f'assets/{name}.mp4', f'assets/{name}.jpg')

	pattern = re.compile(r'^(\d{3})\.mp4$')
	for filename in os.listdir('assets'):
		match = pattern.match(filename)
		if not match:
			continue
		jpg_path = os.path.join('assets', f'{match.group(1)}.jpg')
		print(jpg_path)
		extract_frame(os.path.join('assets', filename), jpg_path)

if __name__ == '__main__':
	if sys.argv[1:] == ['videos']:
		generate_videos()
	elif sys.argv[1:] == ['covers']:
		generate_covers()
	else:
		sys.exit('usage: generate-assets.py videos|covers')
