import WaveSurfer from '/wavesurfer/wavesurfer.esm.js';
import RegionsPlugin from '/wavesurfer/plugins/regions.esm.js';

class AudioPlayer {
	constructor(container, audio) {
		this.container = container;
		this.audio = audio;
		this.wavesurfer = null;
	}

	_init() {
		this.wavesurfer = WaveSurfer.create({
			container: this.container,
			autoplay: false,
			...this.options
		});
		this.wavesurfer.load(this.audio);
		this.container.onclick = (e) => {
			e.preventDefault();
			if (this.wavesurfer.isPlaying()) {
				this.wavesurfer.pause();
			} else {
				stopAllPlayers(this.wavesurfer);
				this.wavesurfer.play();
			}
			return false;
		};
	}

	togglePlay() {
		if (this.wavesurfer.isPlaying()) {
			this.wavesurfer.pause();
		} else {
			stopAllPlayers(this.wavesurfer);
			this.wavesurfer.play();
		}
	}
}

class SimpleAudioPlayer extends AudioPlayer {
	constructor(container, audio) {
		super(container, audio);
		this._init();
	}
	options = {
		height: 40,
		width: 60,
		interact: false
	};
}

class VisualAudioPlayer extends AudioPlayer {
	constructor(container, audio) {
		super(container, audio);
		this._init();
	}

	options = {
		height: 40,
		width: 60,
		barWidth: 2,
		barGap: 1,
		interact: false,
		autoScroll: true,
		autoCenter: true,
		waveColor: '#a1887f',
		progressColor: '#8d6e63',
		cursorColor: '#6d4c41',
		backgroundColor: '#fefcf6'
	};
}

class MarkerAudioPlayer extends AudioPlayer {
	constructor(container, audio, start, end, from, to, playButton) {
		super(container, audio);
		this.start_time = start;
		this.end_time = end;
		this.from = from;
		this.to = to;
		this._init();
		if (playButton) {
			playButton.addEventListener('click', () => {
				this.togglePlay();
			});
		}
		this.regions = RegionsPlugin.create();
		this.wavesurfer.registerPlugin(this.regions);
		this._setupRegions();
	}

	options = {
		height: 100,
		waveColor: 'rgb(100, 100, 200)',
		progressColor: 'rgb(50, 50, 150)',
		cursorColor: '#6d4c41',
		backgroundColor: '#fefcf6',
		barWidth: 2,
		barGap: 1,
		interact: true,
		autoScroll: true,
		autoCenter: true,
		autoplay: false
	};

	_setupRegions() {
		this.wavesurfer.on('decode', () => {
			this.regions.addRegion({
				start: this.start_time - this.from,
				end: this.end_time - this.from,
				drag: false,
				resize: true,
				color: 'rgba(50, 150, 50, 0.4)',
				id: 'verse-region'
			});
			this.regions.on('region-updated', (region) => {
				if (region.id === 'verse-region') {
					this.start_time = region.start + this.from;
					this.end_time = region.end + this.from;
					document.getElementById('start').value = (region.start + this.from).toFixed(3);
					document.getElementById('end').value = (region.end + this.from).toFixed(3);
				}
			});
		});
	}
}

const players = new Map();

function stopAllPlayers(exceptPlayer = null) {
	players.forEach((player) => {
		if (player !== exceptPlayer && player.isPlaying()) {
			player.pause();
		}
	});
}

function initializeAudio() {
	document.querySelectorAll('.simple-player').forEach(container => {
		const audio = container.getAttribute('data-audio');
		const player = new SimpleAudioPlayer(container, audio);
		players.set(container, player.wavesurfer);
	});
	document.querySelectorAll('.visual-player').forEach(container => {
		const audio = container.getAttribute('data-audio');
		const player = new VisualAudioPlayer(container, audio);
		players.set(container, player.wavesurfer);
	});
	document.querySelectorAll('.marker-player').forEach(container => {
		const audio = container.getAttribute('data-audio');
		const start = parseFloat(container.getAttribute('data-start'));
		const end = parseFloat(container.getAttribute('data-end'));
		const from = parseFloat(container.getAttribute('data-from'));
		const to = parseFloat(container.getAttribute('data-to'));
		const playButton = document.getElementById('play-btn');
		const player = new MarkerAudioPlayer(container, audio, start, end, from, to, playButton);
		players.set(container, player.wavesurfer);
	});
}

window.players = players;
document.addEventListener('DOMContentLoaded', initializeAudio);
