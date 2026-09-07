from flask import Flask, send_file, request, Response, render_template, redirect, url_for, abort
import ffmpeg
from Bible import Bible
import Hebrew
from Video import PsalmVideo
import Media
import re
import os
import csv
from Overlay import PsalmCover
from Audio import PsalmAudio
from Psalms import Psalms
from AudioBible import AudioBible

app = Flask(__name__, template_folder="templates")
bible = Bible()
bible.psalms = Psalms(bible)

@app.route('/')
def index():
	audio = AudioBible()
	def format_duration(seconds):
		if seconds <= 0:
			return ""
		h = int(seconds // 3600)
		m = int((seconds % 3600) // 60)
		s = int(seconds % 60)
		if h:
			return f"{h}:{m:02d}:{s:02d}"
		return f"{m}:{s:02d}"

	book_ranges = [
		(1, 41, "Book 1 (Psalms 1‑41)"),
		(42, 72, "Book 2 (Psalms 42‑72)"),
		(73, 89, "Book 3 (Psalms 73‑89)"),
		(90, 106, "Book 4 (Psalms 90‑106)"),
		(107, 150, "Book 5 (Psalms 107‑150)")
	]

	books_data = []
	grand_original = 0.0
	grand_cloned = 0.0
	grand_total_duration = 0.0

	for start, end, name in book_ranges:
		book_psalms = []
		book_original = 0.0
		book_cloned = 0.0
		book_total_duration = 0.0

		for i in range(start, end + 1):
			psalm = bible.psalms[i - 1]
			total_original = 0.0
			total_cloned = 0.0

			for verse in psalm.verses:
				if audio.has_original_audio(verse):
					st, en = audio.get_timing(verse)
					total_original += (en - st)
				if audio.has_cloned_audio(verse):
					total_cloned += audio.cloned_duration(verse)

			book_original += total_original
			book_cloned += total_cloned

			psalm_audio = PsalmAudio(psalm, music=True)
			total_dur = psalm_audio.duration
			book_total_duration += total_dur

			book_psalms.append({
				"psalm": psalm,
				"cloned_duration": format_duration(total_cloned),
				"original_duration": format_duration(total_original),
				"total_duration": format_duration(total_dur),
				"show_color": total_cloned > 0
			})

		grand_original += book_original
		grand_cloned += book_cloned
		grand_total_duration += book_total_duration

		books_data.append({
			"name": name,
			"psalms": book_psalms,
			"cloned_total": format_duration(book_cloned),
			"original_total": format_duration(book_original),
			"duration_total": format_duration(book_total_duration)
		})

	return render_template('psalms.html',
		psalms=bible.psalms,
		books=books_data,
		grand_original_formatted=format_duration(grand_original),
		grand_cloned_formatted=format_duration(grand_cloned),
		grand_total_formatted=format_duration(grand_total_duration),
		len=len
	)

@app.route('/<int:p>')
def psalm(p):
	psalm = bible.psalms[p-1]
	audio = AudioBible()

	template = open('descriptions.md', 'r', encoding='utf-8').read()
	templates = {}
	for match in re.finditer(r'##([^\n]+)\n([\s\S]*?)(?=(?:^##|\Z))', template, re.MULTILINE):
		name = match.group(1).strip()
		text = match.group(2).strip()
		templates[name] = text
	descriptions = {}
	for name, template_text in templates.items():
		from jinja2 import Template
		text = Template(template_text).render(psalm=psalm)
		descriptions[name] = text

	return render_template('psalm.html',
		p=p,
		psalm=psalm,
		bible=bible,
		audio=audio,
		descriptions=descriptions
	)

@app.route('/<int:p>/edit', methods=['GET'])
def psalm_edit(p):
	psalm = bible.psalms[p-1]
	return render_template('psalm_edit.html', psalm=psalm, p=p)

@app.route('/<int:p>/edit', methods=['POST'])
def psalm_save(p):
	psalm = bible.psalms[p-1]
	text = request.form.get('text', '').replace('\r\n', '\n')
	psalm.markdown = text
	psalm.load()
	return redirect(f'/{p}')

@app.route('/<int:p>/align')
def psalm_align(p):
	psalm = bible.psalms[p-1]
	alignment_path = 'csv/alignment.csv'
	verse_data = []

	align_rows = []
	if os.path.exists(alignment_path):
		with open(alignment_path, 'r', encoding='utf-8') as f:
			reader = csv.DictReader(f)
			for row in reader:
				if int(row['book']) == 27 and int(row['chapter']) == p:
					align_rows.append({
						'verse': int(row['verse']),
						'word': int(row['word']),
						'start': float(row['start']),
						'end': float(row['end'])
					})

	for verse in psalm.verses:
		words = verse.bare_text.split()
		verse_words = []
		for idx, word_text in enumerate(words, start=1):
			match = next((r for r in align_rows if r['verse'] == verse.number and r['word'] == idx), None)
			if match:
				start = match['start']
				end = match['end']
				duration = end - start
				start_str = f"{start:.3f}"
				end_str = f"{end:.3f}"
				duration_str = f"{duration:.3f}"
			else:
				start_str = end_str = duration_str = ''
			verse_words.append({
				'index': idx,
				'text': word_text,
				'start': start_str,
				'end': end_str,
				'duration': duration_str
			})
		verse_data.append({
			'number': verse.number,
			'words': verse_words
		})

	return render_template('psalm-align.html', p=p, psalm=psalm, verse_data=verse_data)

@app.route('/<int:p>/<int:v>/audio')
def psalm_audio_edit(p, v):
	psalm = bible.psalms[p - 1]
	verse = psalm.verses[v - 1]
	audio = AudioBible()

	if audio.has_original_audio(verse):
		start, end = audio.get_timing(verse)
	else:
		start, end = 0.0, 0.0

	if not start:
		if v > 1:
			prev_verse = psalm.verses[v - 2]
		else:
			prev_psalm = bible.psalms[p - 2] if p > 1 else None
			prev_verse = prev_psalm.verses[-1] if prev_psalm else None
		if prev_verse:
			s, e = audio.get_timing(prev_verse)
			start = e
			end = start + 15

	frm = max(0, start - 2)
	to = end + 15 if end > 0 else 15

	next_verse = v + 1 if v < len(psalm.verses) else None
	next_chapter = p + 1 if not next_verse and p < 150 else None

	return render_template(
		'psalm_audio_edit.html',
		p=p, v=v, start=start, end=end, frm=frm, to=to,
		psalm=psalm, verse=verse,
		next_verse=next_verse, next_chapter=next_chapter
	)

@app.route('/save-psalm-audio-timing', methods=['POST'])
def save_psalm_audio_timing():
	book = int(request.form['book'])
	chapter = int(request.form['chapter'])
	verse_num = int(request.form['verse'])
	start = float(request.form['start'])
	end = float(request.form['end'])

	verse = bible.verse(book - 1, chapter, verse_num)
	audio = AudioBible()
	audio.set_timing(verse, start, end)

	if 'next' in request.form:
		if 'next_verse' in request.form:
			next_verse = int(request.form['next_verse'])
			return redirect(f'/{chapter}/{next_verse}/audio')
		elif 'next_chapter' in request.form:
			next_chapter = int(request.form['next_chapter'])
			return redirect(f'/{next_chapter}/1/audio')
	return redirect(f'/{chapter}/{verse_num}/audio')

@app.route('/audio-<int:book>-<string:frm>-<string:to>.wav')
def serve_audio_segment(book, frm, to):
	frm = float(frm)
	to = float(to)
	audio_path = f"wav/{book:02d}.wav"
	process = (
		ffmpeg
		.input(audio_path, ss=frm, to=to)
		.output('pipe:', acodec='pcm_s16le', ar=44100, ac=1, format='wav')
		.run_async(pipe_stdout=True, pipe_stderr=True)
	)
	audio_data, _ = process.communicate()
	return Response(audio_data, mimetype='audio/wav')

@app.route('/export/covers/<int:psalm_number>')
def export_psalm_covers(psalm_number):
	psalm = bible.psalms[psalm_number - 1]
	for size in (Media.SDV, Media.SDH, Media.SD):
		cover = PsalmCover(psalm, size)
		if cover.image is not None:
			cover.export()
	return redirect(f'/{psalm_number}')

@app.route('/export/covers')
def export_all_psalm_covers():
	for number in range(1, 151):
		psalm = bible.psalms[number - 1]
		for size in (Media.SDV, Media.SDH, Media.SD):
			cover = PsalmCover(psalm, size)
			if cover.image is not None:
				cover.export()
	return redirect('/')

@app.route('/export/audio/<int:number>')
def export_psalm_audio(number):
	psalm = bible.psalms[number - 1]
	PsalmAudio(psalm).export()
	return redirect(f'/{number}')

@app.route('/export/audio/score/<int:number>')
def export_psalm_score_audio(number):
	psalm = bible.psalms[number - 1]
	PsalmAudio(psalm, music=True).export()
	return redirect(f'/{number}')

@app.route('/export/audio')
def export_psalms_audio():
	for i in range(150):
		psalm = bible.psalms[i]
		PsalmAudio(psalm).export()
	return redirect('/')

@app.route('/export/video/horizontal/<int:p>')
def export_psalm_horizontal_video(p):
	psalm = bible.psalms[p - 1]
	video = PsalmVideo(psalm, size=Media.HDH)
	video.export()
	return redirect(f'/{p}')

@app.route('/export/video/score/<int:p>')
def export_psalm_score_video(p):
	psalm = bible.psalms[p - 1]
	video = PsalmVideo(psalm, size=Media.SDV, music=True)
	video.export()
	return redirect(f'/{p}')

@app.route('/export/video/score/horizontal/<int:p>')
def export_psalm_score_horizontal_video(p):
	psalm = bible.psalms[p - 1]
	video = PsalmVideo(psalm, size=Media.HDH, music=True)
	video.export()
	return redirect(f'/{p}')

@app.route('/export/video/cinematic/<int:p>')
def export_psalm_cinematic_video(p):
	psalm = bible.psalms[p - 1]
	video = PsalmVideo(psalm, size=Media.SDV, music=True, graphics=True)
	video.export()
	return redirect(f'/{p}')

@app.route('/clone/<int:p>')
def clone_psalm_voice(p):
	psalm = bible.psalms[p - 1]
	audio = AudioBible()
	for verse in psalm.verses:
		if not audio.has_cloned_audio(verse) and audio.has_original_audio(verse):
			audio.clone(verse)  # note: AudioBible now has a clone(verse) method
	return redirect(f'/{p}')

@app.route('/align/<int:p>')
def align_psalm(p):
	audio = AudioBible()
	psalm = bible.psalms[p - 1]
	for verse in psalm.verses:
		if audio.has_cloned_audio(verse):
			audio.align(verse.chapter.book.number, verse.chapter.number, verse.number)
	return redirect(f'/{p}')

@app.route('/align/<int:p>/<int:v>')
def align_psalm_verse(p, v):
	audio = AudioBible()
	psalm = bible.psalms[p - 1]
	verse = psalm.verses[v - 1]
	if audio.has_cloned_audio(verse):
		audio.align(verse.chapter.book.number, verse.chapter.number, verse.number)
	return redirect(f'/{p}#{v}')

@app.route('/hebrew/normalize', methods=['POST'])
def hebrew_normalize():
	text = request.form.get('text', '')
	normalized = Hebrew.normalize(text)
	return Response(normalized, mimetype='text/plain')

@app.route('/hebrew/dagesh_hazzak', methods=['POST'])
def hebrew_dagesh_hazzak():
	text = request.form.get('text', '')
	processed = Hebrew.add_dagesh_hazzak(text)
	return Response(processed, mimetype='text/plain')

@app.route('/<path:filename>')
def serve_file(filename):
	if os.path.exists(filename):
		return send_file(f"{filename}")
	else:
		abort(404)

if __name__ == '__main__':
	app.run(debug=True, port=5000)
