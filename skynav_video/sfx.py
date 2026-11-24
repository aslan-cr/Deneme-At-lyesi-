"""Tanıtım videoları için ses: efektler + hafif müzik + gece ortam sesi (SkyNav'daki CC0 orman gecesi kaydı).
Kullanım: python3 sfx.py <info.json> <video_no> <çıktı.wav>"""
import json, subprocess, sys
import numpy as np

SR = 44100
info = json.load(open(sys.argv[1])); vid = sys.argv[2]; out = sys.argv[3]
dur = info['dur']; N = int(dur * SR)
mixL = np.zeros(N); mixR = np.zeros(N)
rng = np.random.default_rng(7)

def env(n, a=.005, r=.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))

def add(t0, sig, gain=1., pan=0.):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[:N - i]
    mixL[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
    mixR[i:i + len(sig)] += sig * gain * (1 + min(0, pan))

def sweep(f0, f1, d, kind='sin'):
    n = int(d * SR); f = np.geomspace(f0, f1, n); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) if kind == 'sin' else np.sign(np.sin(ph)) * .5

def noise(d): return rng.standard_normal(int(d * SR))

def lowpass(sig, k):  # basit tek kutuplu
    out = np.empty_like(sig); acc = 0.
    for i, v in enumerate(sig): acc += k * (v - acc); out[i] = acc
    return out

def bandnoise(d, k1, k2): s = noise(d); return lowpass(s, k1) - lowpass(s, k2)

def pluck(f, d=.45, bright=.35):
    n = int(d * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + bright * np.sin(4 * np.pi * f * t) + .12 * np.sin(6 * np.pi * f * t)) * env(n, .003, d / 3.2)

def ms(*parts):
    n = max(len(a) for a in parts); out = np.zeros(n)
    for a in parts: out[:len(a)] += a
    return out

SFX = {}
SFX['pop'] = lambda: sweep(950, 480, .09) * env(int(.09 * SR), .002, .03) * .55
SFX['boing'] = lambda: (lambda n: np.sin(2 * np.pi * np.cumsum(330 + 220 * np.sin(np.linspace(0, np.pi, n)) + 25 * np.sin(np.arange(n) / SR * 2 * np.pi * 18)) / SR) * env(n, .005, .18))(int(.42 * SR)) * .45
SFX['whoosh'] = lambda: bandnoise(.45, .25, .02) * np.sin(np.linspace(0, np.pi, int(.45 * SR))) ** 2 * .9
SFX['swipe'] = lambda: bandnoise(.22, .5, .08) * np.sin(np.linspace(0, np.pi, int(.22 * SR))) * .55
SFX['ding'] = lambda: ms(pluck(1318, 1.1, .5), .5 * pluck(1975, .9, .2)) * .32
SFX['thump'] = lambda: ms(sweep(140, 60, .28) * env(int(.28 * SR), .002, .08), bandnoise(.28, .08, .01) * env(int(.28 * SR), .001, .04)) * .8
SFX['thud'] = lambda: ms(sweep(110, 45, .4) * env(int(.4 * SR), .002, .12), bandnoise(.4, .1, .01) * env(int(.4 * SR), .001, .06) * 1.2) * .9
SFX['spin'] = lambda: ms(sweep(500, 1600, .8) * env(int(.8 * SR), .05, .6) * .18, sweep(520, 1650, .8) * env(int(.8 * SR), .05, .6) * .12)
SFX['shiver'] = lambda: (lambda n: bandnoise(2.0, .3, .05) * (.5 + .5 * np.sin(np.arange(n) / SR * 2 * np.pi * 22)) * np.minimum(1, np.linspace(0, 6, n)) * np.exp(-np.linspace(0, 2.2, n)) * .5)(int(2.0 * SR))
SFX['step'] = lambda: np.concatenate([sweep(120, 70, .09) * env(int(.09 * SR), .002, .03) * .5, np.zeros(int(.17 * SR))] * 5)
SFX['sparkle'] = lambda: ms(*[np.pad(pluck(f, .7, .1), (int(i * .09 * SR), 0)) for i, f in enumerate([2093, 2637, 3136, 2349, 2794, 3520])]) * .12
SFX['meteor'] = lambda: ms(bandnoise(.7, .6, .2) * np.sin(np.linspace(0, np.pi, int(.7 * SR))) ** 2 * .35, sweep(2400, 900, .7) * env(int(.7 * SR), .02, .3) * .05)
SFX['confetti'] = lambda: np.concatenate([bandnoise(.05, .9, .2) * 1.4] + [np.concatenate([bandnoise(.015, .9, .4) * rng.uniform(.1, .4), np.zeros(int(rng.uniform(.01, .05) * SR))]) for _ in range(30)])
SFX['taps'] = lambda: np.concatenate([np.concatenate([bandnoise(.012, .95, .5) * .9, np.zeros(int(rng.uniform(.06, .12) * SR))]) for _ in range(16)])
SFX['snore'] = lambda: (lambda n: bandnoise(1.6, .05, .01) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 2.0)(int(1.6 * SR))

# Müzik: pentatonik, hafif (gündüz neşeli, gece yumuşak)
def music(bpm, d, gain, decay, night):
    beat = 60 / bpm; prog = [(261.63, [261.63, 329.63, 392.0, 440.0]), (220.0, [261.63, 329.63, 440.0, 392.0]),
                            (174.61, [349.23, 440.0, 392.0, 329.63]), (196.0, [392.0, 293.66, 329.63, 392.0])]
    mel = [0, 2, 1, 3, 2, 0, 3, 1]
    t = 0; bar = 0
    while t < d:
        root, notes = prog[bar % 4]
        add(t, pluck(root / 2, beat * 3.5, .2) * .55 * gain)
        for i in range(8 if not night else 4):
            step = beat / 2 if not night else beat
            n = notes[mel[(i + bar) % 8] % 4] * (2 if (i % 3 == 0 and not night) else 1)
            add(t + i * step, pluck(n, decay, .3) * gain * (.9 if i % 2 == 0 else .6), pan=(-.3 if i % 2 else .3))
        t += beat * 4; bar += 1

if vid == '1': music(112, dur - .5, .11, .35, False)
else: music(84, dur - .5, .09, 1.1, True)

# Gece ortam sesi (gerçek CC0 kayıt, uygulamanın kendi sesi)
def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'quiet', '-i', path, '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(float).reshape(-1, 2) / 32768
    return a
night = load('forest_night.ogg')
def ambience(t0, t1, gain):
    i0, i1 = int(t0 * SR), min(N, int(t1 * SR)); n = i1 - i0
    seg = np.tile(night, (n // len(night) + 1, 1))[:n]
    fade = np.minimum(1, np.minimum(np.arange(n) / (SR * .8), (n - np.arange(n)) / (SR * .8)))
    mixL[i0:i1] += seg[:, 0] * fade * gain; mixR[i0:i1] += seg[:, 1] * fade * gain
if vid == '1': ambience(20.8, 26.8, .5)
else: ambience(0, dur - 2.5, .45)

for t0, kind in info['sfx']:
    if kind in ('music', 'night'): continue
    add(t0, np.asarray(SFX[kind](), dtype=float), 1.0)

# Son: müzik ve her şey yavaşça kısılır; tepe -1 dBFS
fo = np.ones(N); k = int(1.5 * SR); fo[-k:] = np.linspace(1, 0, k)
L = np.tanh(mixL * fo * 1.4) ; R = np.tanh(mixR * fo * 1.4)
peak = max(np.abs(L).max(), np.abs(R).max()); L *= .89 / peak; R *= .89 / peak
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
import wave
with wave.open(out, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', out, round(dur, 1))
