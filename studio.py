from flask import Flask, send_file, request, Response, render_template, redirect, url_for, abort
import ffmpeg
from Bible import Bible
import Hebrew
#from Audio import BibleAudio
from Video import PsalmVideo, EpisodeVideo
import Media
import re
import os
import csv
from Overlay import PsalmCover
import markdown
from Audio import PsalmAudio

from Parashot import Parashot
from Psalms import Psalms

app = Flask(__name__, template_folder="templates")
bible = Bible()
bible.parashot = Parashot(bible)
bible.psalms = Psalms(bible)
#bible.audio = object()







from AudioBible import AudioBible

@app.route('/')
def index():
	audio = AudioBible.get_instance()

	def format_duration(seconds):
		if seconds <= 0:
			return "0:00"
		h = int(seconds // 3600)
		m = int((seconds % 3600) // 60)
		s = int(seconds % 60)
		if h:
			return f"{h}:{m:02d}:{s:02d}"
		return f"{m}:{s:02d}"

	def compute_stats(verses):
		orig_count = 0
		orig_total = 0.0
		cloned_count = 0
		cloned_total = 0.0
		eng_count = 0
		eng_total = 0.0
		for verse in verses:
			if audio.has_original_audio(verse):
				start, end = audio.get_timing(verse)
				orig_total += (end - start)
				orig_count += 1
			if audio.has_cloned_audio(verse):
				cloned_total += audio.cloned_duration(verse)
				cloned_count += 1
			if audio.has_english_audio(verse):
				eng_total += audio.english_duration(verse)
				eng_count += 1
		return {
			"original": {"count": orig_count, "duration": format_duration(orig_total)},
			"cloned":   {"count": cloned_count, "duration": format_duration(cloned_total)},
			"english":  {"count": eng_count, "duration": format_duration(eng_total)},
		}

	psalm_verses = []
	for p in bible.psalms:
		psalm_verses.extend(p.verses)

	parashot_verses = []
	for parashah in bible.parashot:
		parashot_verses.extend(parashah.verses)

	stats = {
		"psalms": compute_stats(psalm_verses),
		"parashot": compute_stats(parashot_verses),
	}

	return render_template('index.html', stats=stats)


@app.route('/bible/psalms')
def psalms():
	audio = AudioBible.get_instance()

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
	grand_total_duration = 0.0   # <-- new grand total

	for start, end, name in book_ranges:
		book_psalms = []
		book_original = 0.0
		book_cloned = 0.0
		book_total_duration = 0.0   # <-- new book total

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

			# --- new: compute full Score video duration ---
			psalm_audio = PsalmAudio(psalm, music=True)
			total_dur = psalm_audio.duration   # includes title + fades + music
			book_total_duration += total_dur
			# -------------------------------------------

			book_psalms.append({
				"psalm": psalm,
				"cloned_duration": format_duration(total_cloned),
				"original_duration": format_duration(total_original),
				"total_duration": format_duration(total_dur),   # <-- new field
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
			"duration_total": format_duration(book_total_duration)  # updated meaning
		})

	return render_template('psalms.html',
		psalms=bible.psalms,
		books=books_data,
		grand_original_formatted=format_duration(grand_original),
		grand_cloned_formatted=format_duration(grand_cloned),
		grand_total_formatted=format_duration(grand_total_duration),   # new grand total
		len=len
	)




@app.route('/xxxbible/psalms')
def xxxpsalms():
	audio = AudioBible.get_instance()

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
	grand_duration = 0.0

	for start, end, name in book_ranges:
		book_psalms = []
		book_original = 0.0
		book_cloned = 0.0
		book_duration = 0.0

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
			book_duration += total_cloned  # or total_original? assume cloned dominates

			book_psalms.append({
				"psalm": psalm,
				"cloned_duration": format_duration(total_cloned),
				"original_duration": format_duration(total_original),
				"duration": format_duration(total_cloned),  # main displayed duration
				"show_color": total_cloned > 0
			})

		grand_original += book_original
		grand_cloned += book_cloned
		grand_duration += book_duration

		books_data.append({
			"name": name,
			"psalms": book_psalms,
			"cloned_total": format_duration(book_cloned),
			"original_total": format_duration(book_original),
			"duration_total": format_duration(book_duration)
		})

	return render_template('psalms.html',
		psalms=bible.psalms,
		books=books_data,
		grand_original_formatted=format_duration(grand_original),
		grand_cloned_formatted=format_duration(grand_cloned),
		grand_duration_formatted=format_duration(grand_duration),
		len=len
	)

@app.route('/bible/psalms/<int:p>')
def psalm(p):
	psalm = bible.psalms[p-1]
	audio = AudioBible.get_instance()

	# Descriptions (unchanged)
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


@app.route('/bible/psalms/<int:p>/edit', methods=['GET'])
def psalm_edit(p):
	psalm = bible.psalms[p-1]
	return render_template('psalm_edit.html',
				 psalm=psalm,
				 p=p
				)

@app.route('/bible/psalms/<int:p>/edit', methods=['POST'])
def psalm_save(p):
	psalm = bible.psalms[p-1]
	text = request.form.get('text', '').replace('\r\n', '\n')
	#text = Hebrew.normalize(text)   # normalize Hebrew text
	psalm.markdown = text
	psalm.load()
	return redirect(f'/bible/psalms/{p}')



@app.route('/bible/psalms/<int:p>/align')
def psalm_align(p):
	psalm = bible.psalms[p-1]
	alignment_path = 'csv/alignment.csv'
	verse_data = []
	
	# Load alignment rows for this psalm (book=27, chapter=p)
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
	
	# For each verse, get words from bare_text and match alignment
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
	
	return render_template('psalm-align.html',
						   p=p,
						   psalm=psalm,
						   verse_data=verse_data)
















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




@app.route('/bible/articles')
def articles():
	articles = bible.articles.items
	return render_template('articles.html',
						   articles=articles)

@app.route('/bible/articles/<slug>')
def article(slug):
	article = next((a for a in bible.articles.items if a.slug == slug), None)
	if not article:
		return "Article not found", 404
	return render_template('article.html',
						   article=article)

@app.route('/bible/parashot/<int:number>/edit', methods=['POST'])
def parashah_save(number):
	parashah = bible.parashot.items[number-1]
	text = request.form.get('text').replace('\r\n', '\n')
	text = Hebrew.normalize(text=text)
	parashah.markdown = text
	return redirect(f'/bible/parashot/{parashah.number}')

@app.route('/bible/parashot/<int:number>/edit', methods=['GET'])
def parashah_edit(number):
	parashah = bible.parashot.items[number-1]
	return render_template('parashah_edit.html',
						   parashah=parashah)

@app.route('/bible/parashot/<int:number>')
def parashah(number):
	parashah = bible.parashot[number-1]
	episodes = []
	for episode in parashah.episodes:
		#total_cloned = 0.0
		#total_original = 0.0
		for paragraph in episode.paragraphs:
			for verse in paragraph.verses:
				book = verse.chapter.book.number
				chapter = verse.chapter.number
				verse_num = verse.number
				#if bible.audio.has_cloned_audio(book, chapter, verse_num):
				#	total_cloned += bible.audio.cloned_duration(book, chapter, verse_num)
				#if bible.audio.has_original_audio(book, chapter, verse_num):
				#	total_original += bible.audio.original_duration(book, chapter, verse_num)
		#cloned_mmss = f"{int(total_cloned // 60):02d}:{int(total_cloned % 60):02d}" if total_cloned > 0 else ""
		#original_mmss = f"{int(total_original // 60):02d}:{int(total_original % 60):02d}" if total_original > 0 else ""
		r, g, b = episode.color
		episode_color_rgb = f"rgb({r}, {g}, {b})"
		episodes.append({
			'episode': episode,
			#'cloned_duration': cloned_mmss,
			#'original_duration': original_mmss,
			'episode_color_rgb': episode_color_rgb
		})
	return render_template('parashah.html',
						#number=number,
						parashah=parashah)
						#episodes=episodes)

@app.route('/bible/parashot')
def parashot():
	parashot_list = []
	for parashah in bible.parashot:
		#total_cloned = 0.0
		#total_original = 0.0
		#for episode in parashah.episodes:
		#	for paragraph in episode.paragraphs:
		#		for verse in paragraph.verses:
		#			book = verse.chapter.book.number
		#			chapter = verse.chapter.number
		#			verse_num = verse.number
		#			#if bible.audio.has_cloned_audio(book, chapter, verse_num):
		#			#	total_cloned += bible.audio.cloned_duration(book, chapter, verse_num)
		#			#if bible.audio.has_original_audio(book, chapter, verse_num):
		#			#	total_original += bible.audio.original_duration(book, chapter, verse_num)
		##cloned_mmss = f"{int(total_cloned // 60):02d}:{int(total_cloned % 60):02d}" if total_cloned > 0 else ""
		#original_mmss = f"{int(total_original // 60):02d}:{int(total_original % 60):02d}" if total_original > 0 else ""
		parashot_list.append({
			'parashah': parashah,
			#'cloned_duration': cloned_mmss,
			#'original_duration': original_mmss
		})
	return render_template('parashot.html',
						   parashot=parashot_list)


@app.route('/bible/parashot/<int:number>/<int:episode>')
def episode(number, episode):
	parashah = bible.parashot[number-1]
	episode = parashah.episodes[episode-1]

	"""#	verses = []
#	for i, verse in enumerate(episode_obj.verses):
#		book = verse.chapter.book.number
#		chapter = verse.chapter.number
#		verse_num = verse.number
#		#original_duration = 0.0
#		#cloned_duration = 0.0
#		#if bible.audio.has_original_audio(book, chapter, verse_num):
#		#	original_duration = bible.audio.original_duration(book, chapter, verse_num)
#		#if bible.audio.has_cloned_audio(book, chapter, verse_num):
#		#	cloned_duration = bible.audio.cloned_duration(book, chapter, verse_num)
#		#original_mmss = f"{int(original_duration // 60):02d}:{int(original_duration % 60):02d}" if original_duration > 0 else ""
#		#cloned_mmss = f"{int(cloned_duration // 60):02d}:{int(cloned_duration % 60):02d}" if cloned_duration > 0 else ""
#		verses.append({
#			'verse': verse,
#			'index': i,
#			'original_duration': original_mmss,
#			'cloned_duration': cloned_mmss,
#			'has_original': original_duration > 0,
#			'has_cloned': cloned_duration > 0,
#			'original_duration_float': original_duration,
#			'cloned_duration_float': cloned_duration,
#			'book': book,
#			'chapter': chapter,
#			'verse_num': verse_num
#		})
#	#total_original = sum(v['original_duration_float'] for v in verses)
#	#total_cloned = sum(v['cloned_duration_float'] for v in verses)
#	#total_original_mmss = f"{int(total_original // 60):02d}:{int(total_original % 60):02d}" if total_original > 0 else ""
#	#total_cloned_mmss = f"{int(total_cloned // 60):02d}:{int(total_cloned % 60):02d}" if total_cloned > 0 else ""
"""

	return render_template('episode.html',
						   #parashah=parashah,
						   episode=episode)
#						   verses=verses,
#						   total_original_mmss=total_original_mmss,
#						   total_cloned_mmss=total_cloned_mmss)



















@app.route('/generate/video/parashot/<int:parashah>/episodes/<int:episode>')
def generate_episode_video(parashah, episode):
	parashah_obj = bible.parashot[parashah-1]
	episode_obj = parashah_obj.episodes[episode-1]
	video = EpisodeVideo(episode_obj, size=Media.TESTV, raw=False)
	video.export()
	return redirect(f'/bible/parashot/{parashah}/{episode}')

# The full parashah video route is kept as a placeholder; it may be removed or reimplemented later.
@app.route('/generate/video/parashot/<int:parashah>/full')
def generate_parashah_full_video(parashah):
	# Not implemented – redirect back or show message
	return redirect(url_for('parashah', number=parashah))



"""
@app.route('/generate/video/parashot/<int:parashah>/episodes/<int:episode>')
def generate_episode_video(parashah, episode):
	parashah_obj = bible.parashot[parashah-1]
	episode_obj = parashah_obj.episodes[episode-1]
	episode_obj.video.save_overlay()
	episode_obj.video.save_slides()
	print ("OKOK")
	video_path = episode_obj.video.export(imageless=True)
	return redirect(f'/bible/parashot/{parashah_obj.number}/{episode_obj.number}')

@app.route('/generate/video/parashot/<int:parashah>/full')
def generate_parashah_full_video(parashah):
	parashah_obj = bible.parashot[parashah-1]
	#parashah_obj.video.save_overlay()
	#parashah_obj.video.save_slides()
#	parashah_obj.video.generate(imageless=True)
	parashah_obj.video.export(imageless=True)
	return redirect(f'/bible/parashot/{parashah_obj.number}')

@app.route('/generate/video/psalm/<int:psalm>')
def generate_psalm_video(psalm):
	psalm_obj = bible.psalms[psalm - 1]
	psalm_obj.video.export(landscape=False, imageless=False)
	return redirect(f'/bible/psalms/{psalm}')

@app.route('/generate/video/psalm/<int:psalm>/imageless')
def generate_psalm_imageless_video(psalm):
	psalm_obj = bible.psalms[psalm - 1]
	psalm_obj.video.export(landscape=False, imageless=True)
	return redirect(f'/bible/psalms/{psalm}')

@app.route('/generate/video/psalm/<int:psalm>/hd')
def generate_psalm_hd_video(psalm):
	psalm_obj = bible.psalms[psalm - 1]
	psalm_obj.video.export(landscape=True, imageless=True)
	return redirect(f'/bible/psalms/{psalm}')
"""

@app.route('/ai/elevenlabs/clone-voice/<int:book>/<int:chapter>/<int:verse>')
def clone_voice(book, chapter, verse):
	try:
		success = bible.audio.audioai.clone(book, chapter, verse)
		if success:
			if book == 27:
				return redirect(f"/bible/psalms/{chapter}#{verse}")
			return redirect(request.referrer or url_for('index'))
		else:
			return "Failed to clone voice - check ElevenLabs API key and connectivity", 500
	except Exception as e:
		return f"Error cloning voice: {str(e)}", 500

@app.route('/ai/elevenlabs/clone-voice/episode/<int:parashah>/<int:episode>')
def clone_episode_voice(parashah, episode):
	try:
		parashah_obj = bible.parashot.items[parashah-1]
		episode_obj = parashah_obj.episodes[episode-1]
		
		cloned_count = 0
		for verse in episode_obj.verses:
			book_num = verse.chapter.book.number
			chapter_num = verse.chapter.number
			verse_num = verse.number
			if not bible.audio.has_cloned_audio(book_num, chapter_num, verse_num):
				if bible.audio.has_original_audio(book_num, chapter_num, verse_num):
					success = bible.audio.audioai.clone(book_num, chapter_num, verse_num)
					if success:
						cloned_count += 1
		return redirect(f'/bible/parashot/{parashah}/{episode}')
	except Exception as e:
		return f"Error cloning episode voice: {str(e)}", 500

@app.route('/ai/elevenlabs/clone-voice/psalm/<int:psalm>')
def clone_psalm_voice(psalm):
	psalm_obj = bible.psalms[psalm - 1]
	for verse in psalm_obj.verses:
		book_num = 27
		chapter_num = psalm
		verse_num = verse.number
		if not bible.audio.has_cloned_audio(book_num, chapter_num, verse_num):
			if bible.audio.has_original_audio(book_num, chapter_num, verse_num):
				bible.audio.audioai.clone(book_num, chapter_num, verse_num)
	return redirect(f'/bible/psalms/{psalm}')

@app.route('/ai/elevenlabs/generate-english/<int:book>/<int:chapter>/<int:verse>')
def generate_english_audio(book, chapter, verse):
	verse_obj = bible.verse(book, chapter, verse)
	text = getattr(verse_obj, 'english_text', '')
	success = bible.audio.audioai.generate_english_audio(book, chapter, verse, text)
	return redirect(request.referrer or url_for('index'))

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
	audio, _ = process.communicate()


	return Response(audio, mimetype='audio/wav')


@app.route('/bible/psalms/<int:p>/<int:v>/audio')
def psalm_audio_edit(p, v):
	psalm = bible.psalms[p - 1]
	verse = psalm.verses[v - 1]
	audio = AudioBible.get_instance()

	# Get the start/end for this verse
	if audio.has_original_audio(verse):
		start, end = audio.get_timing(verse)
	else:
		start, end = 0.0, 0.0

	# If no start time, guess from the previous verse
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
		p=p,
		v=v,
		start=start,
		end=end,
		frm=frm,
		to=to,
		psalm=psalm,
		verse=verse,
		next_verse=next_verse,
		next_chapter=next_chapter
	)


"""
@app.route('/bible/psalms/<int:p>/<int:v>/audio')
def psalm_audio_edit(p, v):
	psalm = bible.psalms[p - 1]
	verse = psalm.verses[v - 1]
	start, end = bible.audio.get_timing(27, p, v)
	if not start:
		if v > 1:
			prev_verse = psalm.verses[v - 2]
		else:
			prev_verse = bible.psalms[p - 2][-1]
		s, e = bible.audio.get_timing(27, prev_verse.chapter.number, prev_verse.number)
		start = e
		end = start + 15
	frm = max(0, start - 2)
	to = end + 15 if end > 0 else 15
	next_verse = v + 1 if v < len(psalm.verses) else None
	next_chapter = p + 1 if not next_verse and p < 150 else None
	
	return render_template('psalm_audio_edit.html',
						   p=p, v=v, start=start, end=end, frm=frm, to=to,
						   psalm=psalm, verse=verse, next_verse=next_verse, next_chapter=next_chapter)
"""
@app.route('/bible/parashot/<int:parashah_num>/<int:episode_num>/<int:v>/audio')
def parashah_verse_audio_edit(parashah_num, episode_num, v):
	parashah = bible.parashot[parashah_num - 1]
	episode = parashah.episodes[episode_num - 1]
	verse = episode.verses[v - 1]
	prev_verse = episode.verses[v - 2] if v > 1 else None
	if not prev_verse:
		if parashah_num > 1:
			prev_parashah = bible.parashot[parashah_num - 2] 
			prev_verse = prev_parashah.verses[-1]
	next_verse = episode.verses[v] if v < len(episode.verses) else None
	start, end = bible.audio.get_timing(parashah.book.number, verse.chapter.number, verse.number)
	if not start:
		s, e = bible.audio.get_timing(parashah.book.number, prev_verse.chapter.number, prev_verse.number)
		start = e
		end = start + 15
	frm = max(0, start - 2)
	to = end + 15 if end > 0 else 15
	
	return render_template('parashah_verse_audio_edit.html',
						   parashah=parashah, episode=episode, v=v, verse=verse,
						   start=start, end=end, frm=frm, to=to, next_verse=next_verse)

"""
@app.route('/save-psalm-audio-timing', methods=['POST'])
def save_psalm_audio_timing():
	book = int(request.form['book'])
	chapter = int(request.form['chapter']) 
	verse = int(request.form['verse'])
	start = float(request.form['start'])
	end = float(request.form['end'])
	bible.audio.set_timing(book, chapter, verse, start, end)
	if 'next' in request.form:
		if 'next_verse' in request.form:
			next_verse = int(request.form['next_verse'])
			return redirect(f'/bible/psalms/{chapter}/{next_verse}/audio')
		elif 'next_chapter' in request.form:
			next_chapter = int(request.form['next_chapter'])
			return redirect(f'/bible/psalms/{next_chapter}/1/audio')
	return redirect(f'/bible/psalms/{chapter}/{verse}/audio')
"""


@app.route('/save-psalm-audio-timing', methods=['POST'])
def save_psalm_audio_timing():
	book = int(request.form['book'])
	chapter = int(request.form['chapter'])
	verse_num = int(request.form['verse'])
	start = float(request.form['start'])
	end = float(request.form['end'])

	# Get the verse object
	verse = bible.verse(book - 1, chapter, verse_num)

	audio = AudioBible.get_instance()
	audio.set_timing(verse, start, end)

	if 'next' in request.form:
		if 'next_verse' in request.form:
			next_verse = int(request.form['next_verse'])
			return redirect(f'/bible/psalms/{chapter}/{next_verse}/audio')
		elif 'next_chapter' in request.form:
			next_chapter = int(request.form['next_chapter'])
			return redirect(f'/bible/psalms/{next_chapter}/1/audio')
	return redirect(f'/bible/psalms/{chapter}/{verse_num}/audio')

@app.route('/save-parashah-audio-timing', methods=['POST'])
def save_parashah_audio_timing():
	book_num = int(request.form['book'])
	chapter_num = int(request.form['chapter']) 
	idx = int(request.form['verse'])
	start = float(request.form['start'])
	end = float(request.form['end'])
	parashah_num = int(request.form['parashah'])
	episode_num = int(request.form['episode'])
	
	book = bible.books[book_num - 1]
	parashah = bible.parashot[parashah_num - 1]
	episode = parashah.episodes[episode_num - 1]
	verse = episode.verses[idx - 1]
	bible.audio.set_timing(book.number, verse.chapter.number, verse.number, start, end)
	
	if 'next' in request.form and 'next_verse' in request.form:
		next_verse = int(request.form['next_verse'])
		return redirect(f'/bible/parashot/{parashah.number}/{episode.number}/{next_verse}/audio')
	return redirect(f'/bible/parashot/{parashah.number}/{episode.number}/{idx - 1}/audio')

@app.route('/bible/parashot/<int:number>/export-audio')
def export_parashah_audio(number):
	parashah = bible.parashot.items[number-1]
	parashah.audio.export_mp3()
	return redirect(f'/bible/parashot/{number}')
















@app.route('/export/covers/psalm/<int:psalm_number>')
def export_psalm_covers(psalm_number):
	psalm = bible.psalms[psalm_number - 1]
	for size in (Media.SDV, Media.SDH, Media.SD):
		cover = PsalmCover(psalm, size)
		if cover.image is not None:
			cover.export()
	return redirect(f'/bible/psalms/{psalm_number}')


@app.route('/export/covers/psalms')
def export_all_psalm_covers():
	for number in range(1, 151):
		psalm = bible.psalms[number - 1]
		for size in (Media.SDV, Media.SDH, Media.SD):
			cover = PsalmCover(psalm, size)
			if cover.image is not None:
				print (psalm)
				cover.export()
	return redirect('/bible/psalms')


@app.route('/export/audio/psalms')
def export_psalms_audio():
	for i in range(150):
		psalm = bible.psalms[i]
		PsalmAudio(psalm).export()
	return redirect(f'/bible/psalms')



@app.route('/export/audio/psalm/<int:number>')
def export_psalm_audio(number):
	psalm = bible.psalms[number - 1]
	PsalmAudio(psalm).export()
	return redirect(f'/bible/psalms/{number}')

@app.route('/export/audio/psalm+/<int:number>')
def export_psalm_score_audio(number):
	psalm = bible.psalms[number - 1]
	PsalmAudio(psalm, music=True).export()
	return redirect(f'/bible/psalms/{number}')



@app.route('/export/video/psalm/horizontal/<int:psalm>')
def export_psalm_horizonal_video(psalm):
	psalm_obj = bible.psalms[psalm - 1]
	video = PsalmVideo(psalm_obj, size=Media.HDH)
	video.export()
	return redirect(f'/bible/psalms/{psalm}')


@app.route('/export/video/psalm+score/<int:psalm>')
def export_psalm_score_video(psalm):
	psalm = bible.psalms[psalm - 1]
	video = PsalmVideo(psalm, size=Media.SDV, music=True)
	video.export()
	return redirect(f'/bible/psalms/{psalm.number}')

@app.route('/export/video/psalm+score/horizontal/<int:psalm>')
def export_psalm_score_horizontal_video(psalm):
	psalm = bible.psalms[psalm - 1]
	video = PsalmVideo(psalm, size=Media.HDH, music=True)
	video.export()
	return redirect(f'/bible/psalms/{psalm.number}')

@app.route('/export/video/psalm+cinematic/<int:psalm>')
def export_psalm_cinematic_video(psalm):
	psalm = bible.psalms[psalm - 1]
	video = PsalmVideo(psalm, size=Media.SDV, music=True, graphics=True)
	video.export()
	return redirect(f'/bible/psalms/{psalm.number}')










@app.route('/ai/elevenlabs/align/<int:book>/<int:chapter>/<int:verse>')
def align_verse(book, chapter, verse):
	bible.audio.audioai.align(book , chapter, verse)
	if book == 27:
		return redirect(f'/bible/psalms/{chapter}#{verse}')
	return redirect(request.referrer)

@app.route('/ai/elevenlabs/align/<int:book>/<int:chapter>')
def align_chapter(book, chapter):
	book_obj = bible[book - 1]
	chapter_obj = book_obj[chapter - 1]
	for verse in chapter_obj.verses:
		bible.audio.audioai.align(book, chapter, verse.number)
	if book == 27:
		return redirect(url_for('psalm', p=chapter))
	return redirect(request.referrer or url_for('index'))

@app.route('/<path:filename>')
def serve_file(filename):
	if os.path.exists(filename):
		return send_file(f"{filename}")
	else:
		abort(404)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True, port=5000)
	