from flask import Flask, send_file, request, Response, render_template, redirect, url_for, abort
import ffmpeg
from Bible import Bible
import Hebrew
from Video import EpisodeVideo
import Media
import os
from StyledScriptures.Parashot import Parashot
from AudioBible import AudioBible

app = Flask(__name__, template_folder="templates-studio")
bible = Bible()
bible.parashot = Parashot(bible)

@app.route('/')
def index():
	return render_template('parashot.html', parashot=bible.parashot)

@app.route('/<int:number>')
def parashah(number):
	parashah = bible.parashot[number-1]
	return render_template('parashah.html', parashah=parashah)

@app.route('/<int:number>/edit', methods=['GET'])
def parashah_edit(number):
	parashah = bible.parashot.items[number-1]
	return render_template('parashah_edit.html', parashah=parashah)

@app.route('/<int:number>/edit', methods=['POST'])
def parashah_save(number):
	parashah = bible.parashot.items[number-1]
	text = request.form.get('text').replace('\r\n', '\n')
	text = Hebrew.normalize(text=text)
	parashah.markdown = text
	return redirect(f'/{parashah.number}')

@app.route('/<int:number>/<int:episode>')
def episode(number, episode):
	parashah = bible.parashot[number-1]
	episode = parashah.episodes[episode-1]
	return render_template('episode.html', episode=episode)

@app.route('/<int:number>/export-audio')
def export_parashah_audio(number):
	parashah = bible.parashot.items[number-1]
	parashah.audio.export_mp3()
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
	audio = AudioBible()
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
	audio = AudioBible()
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
	audio = AudioBible()
	for verse in episode_obj.verses:
		if not audio.has_cloned_audio(verse) and audio.has_original_audio(verse):
			audio.clone(verse)
	return redirect(f'/{parashah}/{episode}')

@app.route('/clone/<int:book>/<int:chapter>/<int:verse>')
def clone_verse(book, chapter, verse):
	verse_obj = bible.verse(book - 1, chapter, verse)
	audio = AudioBible()
	if audio.has_original_audio(verse_obj):
		audio.clone(verse_obj)
	return redirect(request.referrer or '/')

@app.route('/align/<int:book>/<int:chapter>/<int:verse>')
def align_verse(book, chapter, verse):
	audio = AudioBible()
	verse_obj = bible.verse(book - 1, chapter, verse)
	if audio.has_cloned_audio(verse_obj):
		audio.align(book, chapter, verse)
	return redirect(request.referrer or '/')

@app.route('/align/<int:book>/<int:chapter>')
def align_chapter(book, chapter):
	book_obj = bible[book - 1]
	chapter_obj = book_obj[chapter - 1]
	audio = AudioBible()
	for verse in chapter_obj.verses:
		if audio.has_cloned_audio(verse):
			audio.align(book, chapter, verse.number)
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
	app.run(debug=True, port=5000)