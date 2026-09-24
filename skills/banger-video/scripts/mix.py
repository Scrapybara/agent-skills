"""Mix a music track and a sound-design layer for a video, driven by its events.json.

events.json: {"T": total_s, "music": "track.mp3", "music_start": s_into_track,
              "impact": payoff_s, "end": final_hit_s,
              "events": [{"t": s, "kind": "whoosh"}, ...]}
kit.json:    {"whoosh": [["sfx/whoosh.mp3", "peak", -13]], "key": [["sfx/key00.wav", "attack", -25], ...], ...}
             kinds "impact" and "final" also get a synthesized sub hit.
usage: python mix.py events.json kit.json out.m4a
"""
import json, random, subprocess, sys, tempfile
import numpy as np, librosa, soundfile as sf, pyloudnorm as pyln

SR = 48000
ev, kit, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
N = int(ev["T"] * SR) + 1
meter = pyln.Meter(SR)
lufs = lambda x: meter.integrated_loudness(x.T)


def gain(target, x):
    if x.shape[-1] < int(0.4 * SR):
        return 1.0
    level = lufs(x)
    return 10 ** ((target - level) / 20) if np.isfinite(level) else 1.0

cache = {}


def load(name, anchor):
    if (name, anchor) not in cache:
        y, _ = librosa.load(name, sr=SR, mono=True)
        y = y / (np.abs(y).max() + 1e-9)
        a = int(np.argmax(np.convolve(y**2, np.ones(1200) / 1200, "same"))) if anchor == "peak" else int(np.argmax(np.abs(y) > 0.5)) if anchor == "attack" else 0
        cache[(name, anchor)] = (y, a)
    return cache[(name, anchor)]


def place(dst, y, a, t, db):
    s = int(round(t * SR)) - a
    lo, hi = max(0, s), min(N, s + len(y))
    if hi > lo:
        dst[lo:hi] += (y * 10 ** (db / 20))[lo - s:hi - s]


def sub(f0, f1, dur, decay):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-t * 9)) / SR) * np.exp(-t / decay) * np.minimum(1, t / 0.004)


rng = random.Random(7)
fx, acc = np.zeros(N), np.zeros(N)
for e in ev["events"]:
    opts = kit.get(e["kind"], [])
    picks = [rng.choice(opts)] if e["kind"] == "key" and opts else opts
    for name, anchor, db in picks:
        y, a = load(name, anchor)
        place(acc if e["kind"] in ("impact", "final") else fx, y, a, e["t"], db + (rng.uniform(-2.5, 2.5) if e["kind"] == "key" else 0))
    if e["kind"] == "impact":
        place(acc, sub(70, 42, 1.6, 0.45), 0, e["t"], -10)
    if e["kind"] == "final":
        place(acc, sub(62, 38, 2.4, 0.7), 0, e["t"], -10)

m, _ = librosa.load(ev["music"], sr=SR, mono=False)
m = m if m.ndim == 2 else np.stack([m, m])
m = m[:, int(ev["music_start"] * SR):][:, :N]
m = np.pad(m, ((0, 0), (0, N - m.shape[1])))
t = np.arange(N) / SR
end, imp = ev.get("end", ev["T"]), ev["impact"]
m *= np.minimum(1, t / 0.9) ** 2 * np.clip(1 - (t - end) / 0.14, 0, 1)
body = slice(0, int(end * SR))
pre, post = slice(int(0.4 * SR), int(imp * SR)), slice(int(imp * SR), int(end * SR))
g_pre, g_post = gain(-16.5, m[:, pre]), gain(-14.5, m[:, post])
m *= g_pre + (g_post - g_pre) * np.clip((t - imp + 0.02) / 0.02, 0, 1)
m *= 1 - (1 - 10 ** (-2.5 / 20)) * np.clip(np.minimum((t - imp + 0.03) / 0.03, (imp + 0.6 - t) / 0.3), 0, 1)
fx *= gain(lufs(m[:, body]) - 5.5, np.stack([fx, fx]))
w = slice(int((imp - 0.3) * SR), int((imp + 0.7) * SR))
base = np.mean(m[:, w] ** 2)
lo, hi = 0.0, 50.0
for _ in range(40):
    k = (lo + hi) / 2
    lo, hi = (k, hi) if 10 * np.log10(np.mean((m[:, w] + fx[None, w] + k * acc[None, w]) ** 2) / base) < 2.5 else (lo, k)
mix = m + (fx + lo * acc)[None, :]

g = -14 - lufs(mix)
wav = tempfile.mktemp(suffix=".wav")
for _ in range(5):
    sf.write(wav, (mix * 10 ** (g / 20)).T, SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", "alimiter=limit=0.8:attack=1:release=80:level=disabled", "-c:a", "aac", "-b:a", "320k", out], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    s = r[r.rfind("Summary"):].splitlines()
    I = float(next(l for l in s if "I:" in l).split()[1])
    TP = float(next(l for l in s if "Peak:" in l).split()[1])
    if abs(I + 14) < 0.2 and TP <= -1.0:
        break
    g += -14 - I - (0.3 if TP > -1.0 else 0)
per_s = [20 * np.log10(np.sqrt(np.mean(mix[:, i * SR:(i + 1) * SR] ** 2)) / (np.sqrt(np.mean(m[:, i * SR:(i + 1) * SR] ** 2)) + 1e-9) + 1e-9) for i in range(int(end))]
print(f"{out}: I {I} LUFS, TP {TP} dBTP, worst mix-over-music second {max(per_s):.1f} dB")
