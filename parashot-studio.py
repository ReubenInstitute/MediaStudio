from flask import Flask, send_file, request, Response, render_template, redirect, url_for, abort
import ffmpeg
from Bible import Bible
import Hebrew
from Video import EpisodeVideo
import Media
import os
from Parashot import Parashot
from AudioBible import AudioBible
from Audio import ParashahAudio

app = Flask(__name__, template_folder="templates")
bible = Bible()
bible.parashot = Parashot(bible)

def format_duration(seconds):
	if seconds <= 0:
		return ""
	m = int(seconds // 60)
	s = int(seconds % 60)
	return f"{m}:{s:02d}"

def audio_totals(verses, audio):
	total_original = 0.0
	total_cloned = 0.0
	for verse in verses:
		if audio.has_original_audio(verse):
			start, end = audio.get_timing(verse)
			total_original += (end - start)
		if audio.has_cloned_audio(verse):
			total_cloned += audio.cloned_duration(verse)
	return total_original, total_cloned

@app.route('/')
def index():
	audio = AudioBible.get_instance()
	parashot_data = []
	for parashah_obj in bible.parashot:
		total_original, total_cloned = audio_totals(parashah_obj.verses, audio)
		parashot_data.append({
			"parashah": parashah_obj,
			"original_duration": format_duration(total_original),
			"cloned_duration": format_duration(total_cloned),
		})
	return render_template('parashot.html', parashot=parashot_data)

@app.route('/<int:number>')
def parashah(number):
	parashah = bible.parashot[number-1]
	audio = AudioBible.get_instance()
	episodes_data = []
	for episode_obj in parashah.episodes:
		total_original, total_cloned = audio_totals(episode_obj.verses, audio)
		episodes_data.append({
			"episode": episode_obj,
			"original_duration": format_duration(total_original),
			"cloned_duration": format_duration(total_cloned),
		})
	return render_template('parashah.html', parashah=parashah, episodes=episodes_data)

@app.route('/<int:number>/edit', methods=['GET'])
def parashah_edit(number):
	parashah = bible.parashot[number-1]
	return render_template('parashah_edit.html', parashah=parashah)

@app.route('/<int:number>/edit', methods=['POST'])
def parashah_save(number):
	parashah = bible.parashot[number-1]
	text = request.form.get('text').replace('\r\n', '\n')
	text = Hebrew.normalize(text=text)
	parashah.markdown = text
	return redirect(f'/{parashah.number}')

@app.route('/<int:number>/<int:episode>')
def episode(number, episode):
	parashah = bible.parashot[number-1]
	episode = parashah.episodes[episode-1]
	audio = AudioBible.get_instance()
	total_original, total_cloned = audio_totals(episode.verses, audio)
	return render_template('episode.html',
		episode=episode,
		audio=audio,
		total_original_mmss=format_duration(total_original),
		total_cloned_mmss=format_duration(total_cloned)
	)

@app.route('/<int:number>/export-audio')
def export_parashah_audio(number):
	parashah = bible.parashot[number-1]
	ParashahAudio(parashah).export_mp3()
	return redirect(f'/{number}')

@app.route('/<int:parashah_num>/<int:episode_num>/<int:v>/audio')
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
	audio = AudioBible.get_instance()
	start, end = audio.get_timing(verse)
	if not start:
		if prev_verse:
			s, e = audio.get_timing(prev_verse)
			start = e
			end = start + 15
	frm = max(0, start - 2)
	to = end + 15 if end > 0 else 15

	return render_template('parashah_verse_audio_edit.html',
		parashah=parashah, episode=episode, v=v, verse=verse,
		start=start, end=end, frm=frm, to=to, next_verse=next_verse)

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
	audio = AudioBible.get_instance()
	audio.set_timing(verse, start, end)

	if 'next' in request.form and 'next_verse' in request.form:
		next_verse = int(request.form['next_verse'])
		return redirect(f'/{parashah.number}/{episode.number}/{next_verse}/audio')
	return redirect(f'/{parashah.number}/{episode.number}/{idx - 1}/audio')

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

@app.route('/generate/video/<int:parashah>/<int:episode>')
def generate_episode_video(parashah, episode):
	parashah_obj = bible.parashot[parashah-1]
	episode_obj = parashah_obj.episodes[episode-1]
	video = EpisodeVideo(episode_obj, size=Media.TESTV)
	video.export()
	return redirect(f'/{parashah}/{episode}')

@app.route('/clone/<int:parashah>/<int:episode>')
def clone_episode_voice(parashah, episode):
	parashah_obj = bible.parashot[parashah-1]
	episode_obj = parashah_obj.episodes[episode-1]
	audio = AudioBible.get_instance()
	for verse in episode_obj.verses:
		if not audio.has_cloned_audio(verse) and audio.has_original_audio(verse):
			audio.clone(verse)
	return redirect(f'/{parashah}/{episode}')

@app.route('/clone/<int:book>/<int:chapter>/<int:verse>')
def clone_verse(book, chapter, verse):
	verse_obj = bible.verse(book - 1, chapter, verse)
	audio = AudioBible.get_instance()
	if audio.has_original_audio(verse_obj):
		audio.clone(verse_obj)
	return redirect(request.referrer or '/')

@app.route('/align/<int:book>/<int:chapter>/<int:verse>')
def align_verse(book, chapter, verse):
	audio = AudioBible.get_instance()
	verse_obj = bible.verse(book - 1, chapter, verse)
	if audio.has_cloned_audio(verse_obj):
		audio.align(verse_obj)
	return redirect(request.referrer or '/')

@app.route('/align/<int:book>/<int:chapter>')
def align_chapter(book, chapter):
	book_obj = bible[book - 1]
	chapter_obj = book_obj[chapter - 1]
	audio = AudioBible.get_instance()
	for verse in chapter_obj.verses:
		if audio.has_cloned_audio(verse):
			audio.align(verse)
	return redirect(request.referrer or '/')

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
	app.run(host='0.0.0.0', debug=True, port=5000)