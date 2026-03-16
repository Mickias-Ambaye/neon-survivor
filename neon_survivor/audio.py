"""
Modern electronic audio engine — deeper bass, layered synths, punchy impacts.
All procedurally generated at runtime.
"""
import pygame
import numpy as np
import math

SAMPLE_RATE = 44100


def _make_sound(samples):
    samples = np.clip(samples, -1, 1)
    int_samples = (samples * 32767).astype(np.int16)
    stereo = np.column_stack((int_samples, int_samples))
    return pygame.sndarray.make_sound(stereo)


def _sine(freq, duration, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def _square(freq, duration, sr=SAMPLE_RATE):
    return np.sign(_sine(freq, duration, sr))


def _saw(freq, duration, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return 2 * (t * freq - np.floor(t * freq + 0.5))


def _noise(duration, sr=SAMPLE_RATE):
    return np.random.uniform(-1, 1, int(sr * duration))


def _env(samples, attack=0.01, decay=0.05, sustain=0.7, release=0.1):
    n = len(samples)
    sr = SAMPLE_RATE
    env = np.ones(n)
    a = min(int(attack * sr), n)
    d = min(int(decay * sr), n - a)
    r = min(int(release * sr), n)

    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if d > 0 and a + d < n:
        env[a:a + d] = np.linspace(1, sustain, d)
        if r > 0:
            env[a + d:-r] = sustain
    if r > 0:
        start_val = env[-r] if r < n else sustain
        env[-r:] = np.linspace(start_val, 0, r)
    return samples * env


def _distort(samples, gain=2.0):
    return np.tanh(samples * gain)


def _filter_lp(samples, cutoff=0.15):
    out = np.zeros_like(samples)
    out[0] = samples[0]
    for i in range(1, len(samples)):
        out[i] = out[i-1] + cutoff * (samples[i] - out[i-1])
    return out


def _reverb(samples, decay=0.3, delay_ms=40):
    delay = int(SAMPLE_RATE * delay_ms / 1000)
    out = samples.copy()
    if delay < len(out):
        out[delay:] += samples[:-delay] * decay
    return np.clip(out, -1, 1)


# ─── MODERN SFX ───────────────────────────────────────────────

def sfx_player_shoot():
    """Punchy laser thump — short with sub bass."""
    dur = 0.09
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Frequency sweep 1800 -> 200
    freq = 1800 * np.exp(-t * 30)
    wave = np.sin(2 * np.pi * freq * t / SAMPLE_RATE * np.arange(len(t))) * 0.3
    sub = np.sin(2 * np.pi * 80 * t) * 0.2  # sub layer
    click = _noise(0.008) * 0.4 if dur > 0.008 else np.array([])
    result = np.zeros(len(t))
    result[:len(wave)] += wave
    result[:len(sub)] += sub
    if len(click) > 0:
        result[:len(click)] += click
    return _make_sound(_env(result, attack=0.001, decay=0.02, sustain=0.3, release=0.04))


def sfx_enemy_hit():
    """Tight impact — filtered thud."""
    dur = 0.08
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    body = np.sin(2 * np.pi * 200 * np.exp(-t * 20) * t) * 0.5
    crack = _noise(dur) * 0.15 * np.exp(-t * 40)
    wave = _filter_lp(body + crack, 0.3)
    return _make_sound(_env(wave, attack=0.001, release=0.04))


def sfx_enemy_death():
    """Satisfying digital crunch — layered."""
    dur = 0.2
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Pitch drop
    freq = 600 * np.exp(-t * 12)
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * 0.3
    # Digital noise burst
    noise = _noise(dur) * 0.25 * np.exp(-t * 15)
    # Bitcrush on the noise
    bits = 6
    noise = np.round(noise * bits) / bits
    # Sub thump
    sub = np.sin(2 * np.pi * 50 * t) * 0.25 * np.exp(-t * 10)
    wave = tone + noise + sub
    return _make_sound(_env(wave, attack=0.001, release=0.08))


def sfx_player_hit():
    """Deep bass impact + distortion wash."""
    dur = 0.35
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    bass = np.sin(2 * np.pi * 45 * t) * 0.7 * np.exp(-t * 5)
    mid = _saw(150, dur) * 0.15 * np.exp(-t * 8)
    crunch = _distort(_noise(dur) * 0.3, 4.0) * np.exp(-t * 10)
    wave = bass + mid + crunch
    return _make_sound(_env(wave, attack=0.003, release=0.15))


def sfx_player_death():
    """Massive sub explosion with reverb tail."""
    dur = 0.8
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    sub = np.sin(2 * np.pi * 30 * t) * 0.8 * np.exp(-t * 3)
    rumble = _filter_lp(_noise(dur) * 0.4, 0.08) * np.exp(-t * 2)
    sweep = np.sin(2 * np.pi * np.cumsum(300 * np.exp(-t * 5)) / SAMPLE_RATE) * 0.3
    wave = _distort(sub + rumble + sweep, 2.0)
    wave = _reverb(wave, 0.3, 60)
    return _make_sound(_env(wave, attack=0.01, release=0.4))


def sfx_xp_collect():
    """Clean ascending blip — two notes."""
    dur = 0.07
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    freq = 900 + t * 6000
    wave = np.sin(2 * np.pi * freq * t) * 0.2
    return _make_sound(_env(wave, attack=0.002, release=0.02))


def sfx_level_up():
    """Lush synth chord — major with shimmer."""
    dur = 0.5
    # C major 7 voicing
    freqs = [261.6, 329.6, 392.0, 493.9, 523.3]
    wave = np.zeros(int(SAMPLE_RATE * dur))
    for f in freqs:
        wave += _sine(f, dur) * 0.1
        wave += _sine(f * 2.005, dur) * 0.04  # slight detune for chorus
    # Shimmer: fast arp over the chord
    shimmer_t = np.linspace(0, dur, len(wave), endpoint=False)
    shimmer = np.sin(2 * np.pi * 1568 * shimmer_t) * 0.06 * np.sin(np.pi * shimmer_t / dur)
    wave += shimmer
    wave = _reverb(wave, 0.25, 50)
    return _make_sound(_env(wave, attack=0.03, decay=0.1, sustain=0.6, release=0.25))


def sfx_dash():
    """Filtered noise whoosh — tight and modern."""
    dur = 0.12
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    noise = _noise(dur) * 0.35
    # Bandpass sweep using multiplication
    bp = np.sin(2 * np.pi * (3000 - t * 15000) * t) * 0.3
    wave = noise * np.abs(bp) + bp * 0.15
    return _make_sound(_env(wave, attack=0.003, release=0.05))


def sfx_boss_spawn():
    """Cinematic sub hit + tension riser."""
    dur = 1.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Sub hit
    sub = np.sin(2 * np.pi * 35 * t) * 0.6 * np.exp(-t * 2)
    # Rising tone
    riser = _saw(80 + t * 200, dur) * 0.15 * np.minimum(t * 2, 1.0)
    # Noise texture
    atmos = _filter_lp(_noise(dur) * 0.12, 0.05) * np.minimum(t * 3, 1.0)
    wave = sub + riser + atmos
    wave = _reverb(wave, 0.35, 80)
    return _make_sound(_env(wave, attack=0.05, release=0.3))


def sfx_wave_clear():
    """Two-note victory chime — clean and satisfying."""
    dur = 0.45
    n = int(SAMPLE_RATE * dur)
    half = n // 2
    # E5 -> A5 (bright interval)
    note1 = _env(_sine(659, dur / 2) * 0.2 + _sine(1318, dur / 2) * 0.08,
                 attack=0.005, release=0.08)
    note2 = _env(_sine(880, dur / 2) * 0.2 + _sine(1760, dur / 2) * 0.08,
                 attack=0.005, release=0.15)
    wave = np.concatenate([note1, note2])
    wave = _reverb(wave, 0.2, 40)
    return _make_sound(wave)


def sfx_shockwave():
    """Deep expanding boom."""
    dur = 0.3
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    boom = np.sin(2 * np.pi * np.cumsum(200 * np.exp(-t * 8)) / SAMPLE_RATE) * 0.5
    sub = np.sin(2 * np.pi * 40 * t) * 0.4 * np.exp(-t * 6)
    wave = boom + sub + _noise(dur) * 0.1 * np.exp(-t * 12)
    return _make_sound(_env(wave, attack=0.003, release=0.15))


def sfx_lightning():
    """Electric zap — filtered crackle."""
    dur = 0.15
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    crackle = _noise(dur) * 0.35 * np.exp(-t * 15)
    tone = np.sin(2 * np.pi * 2500 * t) * 0.15 * np.exp(-t * 20)
    # Gate it for electric feel
    gate = (np.sin(2 * np.pi * 120 * t) > 0).astype(float)
    wave = (crackle * gate + tone)
    return _make_sound(_env(wave, attack=0.001, release=0.04))


def sfx_combo_milestone():
    """Rising power chord."""
    dur = 0.25
    wave = (_sine(880, dur) * 0.15 + _sine(1320, dur) * 0.12 +
            _sine(1760, dur) * 0.08 + _sine(2640, dur) * 0.05)
    wave = _reverb(wave, 0.2, 30)
    return _make_sound(_env(wave, attack=0.005, release=0.12))


def sfx_menu_select():
    """Clean UI click."""
    dur = 0.05
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    wave = np.sin(2 * np.pi * 800 * t) * 0.2 + np.sin(2 * np.pi * 1200 * t) * 0.1
    return _make_sound(_env(wave, attack=0.001, release=0.02))


def sfx_evolution():
    """Epic transformation sound."""
    dur = 0.7
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    # Rising sweep
    sweep = np.sin(2 * np.pi * np.cumsum(200 + t * 2000) / SAMPLE_RATE) * 0.2
    # Chord burst at the top
    burst_start = int(len(t) * 0.5)
    chord = np.zeros(len(t))
    for f in [523, 659, 784, 1047]:
        chord[burst_start:] += np.sin(
            2 * np.pi * f * np.arange(len(t) - burst_start) / SAMPLE_RATE) * 0.1
    sub = np.sin(2 * np.pi * 60 * t) * 0.3 * np.exp(-t * 2)
    wave = sweep + chord + sub
    wave = _reverb(wave, 0.3, 50)
    return _make_sound(_env(wave, attack=0.02, release=0.3))


def sfx_shop_buy():
    """Coin/purchase confirmation."""
    dur = 0.15
    wave = _sine(1047, dur / 3) * 0.2
    wave2 = _sine(1319, dur / 3) * 0.2
    wave3 = _sine(1568, dur / 3) * 0.2
    result = np.concatenate([
        _env(wave, attack=0.002, release=0.02),
        _env(wave2, attack=0.002, release=0.02),
        _env(wave3, attack=0.002, release=0.05)
    ])
    return _make_sound(result)


def sfx_laser():
    """Sustained beam hum."""
    dur = 0.3
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    beam = _saw(200, dur) * 0.15 + _sine(400, dur) * 0.1
    buzz = _square(100, dur) * 0.05
    wave = beam + buzz + _noise(dur) * 0.05
    wave = _filter_lp(wave, 0.2)
    return _make_sound(_env(wave, attack=0.01, sustain=0.8, release=0.1))


# ─── MUSIC GENERATOR ─────────────────────────────────────────

def generate_music_loop():
    """
    ~17 second modern electronic loop.
    Deeper bass, richer pads, sidechain-style pumping.
    """
    bpm = 128
    beat = 60.0 / bpm
    bars = 8
    total_dur = bars * 4 * beat
    n = int(SAMPLE_RATE * total_dur)
    t = np.linspace(0, total_dur, n, endpoint=False)
    mix = np.zeros(n)

    # ── Sub bass (root notes, sine) ──
    bass_freqs = [55, 55, 65.41, 73.42, 55, 65.41, 73.42, 82.41]
    for bar in range(bars):
        freq = bass_freqs[bar % len(bass_freqs)]
        start = int(bar * 4 * beat * SAMPLE_RATE)
        dur = 4 * beat
        bar_n = int(dur * SAMPLE_RATE)
        bar_t = np.linspace(0, dur, bar_n, endpoint=False)
        bass = np.sin(2 * np.pi * freq * bar_t) * 0.2
        bass = _env(bass, attack=0.01, release=0.15)
        end = min(start + bar_n, n)
        mix[start:end] += bass[:end - start]

    # ── Pad (lush detuned chords) ──
    chords = [
        (220, 277, 330),    # Am
        (220, 277, 330),    # Am
        (262, 330, 392),    # C
        (294, 370, 440),    # Dm
        (220, 277, 330),    # Am
        (262, 330, 392),    # C
        (294, 370, 440),    # Dm
        (330, 415, 494),    # Em
    ]
    for bar in range(bars):
        chord = chords[bar % len(chords)]
        start = int(bar * 4 * beat * SAMPLE_RATE)
        dur = 4 * beat
        bar_n = int(dur * SAMPLE_RATE)
        bar_t = np.linspace(0, dur, bar_n, endpoint=False)
        pad = np.zeros(bar_n)
        for f in chord:
            pad += _sine(f, dur) * 0.025
            pad += _sine(f * 1.003, dur) * 0.02  # chorus detune
        pad = _env(pad, attack=0.4, release=0.4)
        end = min(start + bar_n, n)
        mix[start:end] += pad[:end - start]

    # ── Arpeggio (16th notes, filtered) ──
    arp_notes = [440, 554, 659, 880, 659, 554, 440, 330]
    sixteenth = beat / 4
    arp_n = int(sixteenth * SAMPLE_RATE)
    for i in range(int(total_dur / sixteenth)):
        freq = arp_notes[i % len(arp_notes)]
        start = int(i * sixteenth * SAMPLE_RATE)
        note_dur = sixteenth * 0.7
        note_n = int(note_dur * SAMPLE_RATE)
        note = _sine(freq, note_dur) * 0.04
        note = _env(note, attack=0.003, release=0.015)
        end = min(start + note_n, n)
        if end > start and end <= n:
            mix[start:end] += note[:end - start]

    # ── Kick (808-style with pitch drop) ──
    for beat_i in range(bars * 4):
        start = int(beat_i * beat * SAMPLE_RATE)
        kick_dur = 0.2
        kick_n = int(kick_dur * SAMPLE_RATE)
        kick_t = np.linspace(0, kick_dur, kick_n, endpoint=False)
        # Pitch drops from 150Hz to 40Hz
        kick_freq = 150 * np.exp(-kick_t * 15) + 40
        kick = np.sin(2 * np.pi * np.cumsum(kick_freq) / SAMPLE_RATE) * 0.25
        kick = _env(kick, attack=0.001, release=0.12)
        end = min(start + kick_n, n)
        if end > start:
            mix[start:end] += kick[:end - start]

    # ── Hi-hat (filtered noise, 8th notes, alternating velocity) ──
    eighth = beat / 2
    for i in range(int(total_dur / eighth)):
        start = int(i * eighth * SAMPLE_RATE)
        hat_dur = 0.03 if i % 2 == 0 else 0.06
        hat_n = int(hat_dur * SAMPLE_RATE)
        hat_t = np.linspace(0, hat_dur, hat_n, endpoint=False)
        vel = 0.06 if i % 2 == 0 else 0.035
        hat = _noise(hat_dur) * vel * np.exp(-hat_t * 50)
        end = min(start + hat_n, n)
        if end > start:
            mix[start:end] += hat[:end - start]

    # ── Sidechain pump (duck on every kick) ──
    for beat_i in range(bars * 4):
        start = int(beat_i * beat * SAMPLE_RATE)
        duck_dur = int(0.08 * SAMPLE_RATE)
        release_dur = int(0.15 * SAMPLE_RATE)
        # Quick duck then release
        for j in range(min(duck_dur, n - start)):
            mix[start + j] *= 0.4
        for j in range(min(release_dur, n - start - duck_dur)):
            t_ratio = j / release_dur
            mix[start + duck_dur + j] *= 0.4 + 0.6 * t_ratio

    # Normalize
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.6

    return _make_sound(mix)


# ─── AUDIO MANAGER ────────────────────────────────────────────

class AudioManager:
    def __init__(self):
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=1024)
        pygame.mixer.set_num_channels(16)

        self.sounds = {
            'shoot': sfx_player_shoot(),
            'enemy_hit': sfx_enemy_hit(),
            'enemy_death': sfx_enemy_death(),
            'player_hit': sfx_player_hit(),
            'player_death': sfx_player_death(),
            'xp_collect': sfx_xp_collect(),
            'level_up': sfx_level_up(),
            'dash': sfx_dash(),
            'boss_spawn': sfx_boss_spawn(),
            'wave_clear': sfx_wave_clear(),
            'shockwave': sfx_shockwave(),
            'lightning': sfx_lightning(),
            'combo': sfx_combo_milestone(),
            'menu_select': sfx_menu_select(),
            'evolution': sfx_evolution(),
            'shop_buy': sfx_shop_buy(),
            'laser': sfx_laser(),
        }

        self.sounds['shoot'].set_volume(0.25)
        self.sounds['xp_collect'].set_volume(0.18)
        self.sounds['enemy_hit'].set_volume(0.35)
        self.sounds['enemy_death'].set_volume(0.4)
        self.sounds['laser'].set_volume(0.3)

        self.music = None
        self.music_playing = False

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def start_music(self):
        if not self.music_playing:
            self.music = generate_music_loop()
            self.music.play(loops=-1)
            self.music.set_volume(0.3)
            self.music_playing = True

    def stop_music(self):
        if self.music and self.music_playing:
            self.music.fadeout(500)
            self.music_playing = False

    def set_music_volume(self, vol):
        if self.music:
            self.music.set_volume(vol)
