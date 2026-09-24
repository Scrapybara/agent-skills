import sys
import numpy as np
import librosa

SR = 22050


def load(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    return y


def grid(path, bpm, a, b):
    y = load(path)
    env = librosa.onset.onset_strength(y=y, sr=SR)
    tempo, beats = librosa.beat.beat_track(onset_envelope=env, sr=SR, start_bpm=bpm, tightness=400)
    bt = librosa.frames_to_time(beats, sr=SR)
    spec = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    low = spec[librosa.fft_frequencies(sr=SR) < 150].sum(0)
    lt = librosa.frames_to_time(np.arange(len(low)), sr=SR, hop_length=512)
    print(f"tempo {float(np.atleast_1d(tempo)[0]):.2f}")
    print(" ".join(f"{t:.2f}:{low[np.searchsorted(lt, t):np.searchsorted(lt, t) + 4].mean() / low.max() * 100:.0f}" for t in bt if a <= t <= b))


def onsets(path, a, b):
    y = load(path)
    env = librosa.onset.onset_strength(y=y, sr=SR)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=SR)
    m = env.max()
    print(" ".join(f"{t:.2f}({env[o] / m * 100:.0f})" for t, o in zip(librosa.frames_to_time(on, sr=SR), on) if a <= t <= b and env[o] / m > 0.25))


def score(paths):
    rows = []
    for path in paths:
        y = load(path)
        rms = librosa.feature.rms(y=y, hop_length=SR // 2)[0]
        db = 20 * np.log10(rms + 1e-6)
        k = np.convolve(db, np.ones(4) / 4, mode="same")
        jump = k[8:] - k[:-8]
        jump[:12] = -99
        order = [int(j) for j in np.argsort(-jump)]
        tops = []
        for j in order:
            if all(abs(j - q) > 16 for q in tops):
                tops.append(j)
            if len(tops) == 3:
                break
        i = tops[0] + 8
        lift_t = i / 2
        lifts = ",".join(f"{(q + 8) / 2:.1f}" for q in tops)
        contrast = float(jump.max())
        chroma = librosa.feature.chroma_cqt(y=y, sr=SR)
        seg = chroma[:, int(lift_t * SR / 512):int((lift_t + 8) * SR / 512)]
        changes = int((np.diff(seg.argmax(0)) != 0).sum()) if seg.size else 0
        spec = np.abs(librosa.stft(y))
        fr = librosa.fft_frequencies(sr=SR)
        melodic = float(spec[(fr > 300) & (fr < 4000)].sum() / spec.sum())
        flat = float(librosa.feature.spectral_flatness(y=y).mean())
        rows.append((path, lifts, contrast, changes, melodic, flat))
    print("path | lifts_s (strongest first) | lift_dB | chord_moves_8s | melodic_share | flatness")
    for r in sorted(rows, key=lambda r: -(r[2] + r[4] * 40 + min(r[3], 60) / 10)):
        print(f"{r[0]} | {r[1]} | {r[2]:.1f} | {r[3]} | {r[4]:.2f} | {r[5]:.3f}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or [""]
    if cmd == "grid":
        grid(args[0], float(args[1]), float(args[2]), float(args[3]))
    elif cmd == "onsets":
        onsets(args[0], float(args[1]), float(args[2]))
    elif cmd == "score":
        score(args)
    else:
        raise SystemExit("usage: music.py grid FILE BPM FROM TO | onsets FILE FROM TO | score FILES…")
