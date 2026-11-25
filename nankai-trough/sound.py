#!/usr/bin/env python3
"""Synthesize the sound design (SFX bed + uneasy BGM) for the Nankai Trough short.

Everything is generated from noise and oscillators here, so there are no third-party
recordings and no copyrighted alert chimes or sirens.

  python3 sound.py SCENES.json OUTDIR
SCENES.json: {"total": seconds, "scenes": {"1": [start, end], ...}}  (scene ids as in script.md)
Writes OUTDIR/sfx.wav and OUTDIR/bgm.wav (48 kHz stereo, float -> 24-bit).
"""
import json, sys, wave
import numpy as np
from scipy import signal

SR = 48000
rng = np.random.default_rng(20251125)


def N(d):
    return int(round(d * SR))


# ---------- primitives ----------
def t_axis(d):
    return np.arange(N(d)) / SR


def white(d):
    return rng.standard_normal(N(d))


def brown(d):
    x = np.cumsum(white(d))
    x = signal.sosfilt(signal.butter(1, 15, "hp", fs=SR, output="sos"), x)
    return x / (np.max(np.abs(x)) + 1e-9)


def pink(d):
    n = N(d)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec = (rng.standard_normal(len(f)) + 1j * rng.standard_normal(len(f))) / np.sqrt(np.maximum(f, 20))
    x = np.fft.irfft(spec, n)
    return x / (np.max(np.abs(x)) + 1e-9)


def filt(x, kind, f, order=4):
    return signal.sosfilt(signal.butter(order, f, kind, fs=SR, output="sos"), x)


def smooth_rand(d, rate, lo=0.0, hi=1.0):
    """Slowly varying random envelope (rate = changes per second)."""
    n = N(d)
    k = max(2, int(d * rate) + 2)
    pts = rng.uniform(lo, hi, k)
    xs = np.linspace(0, n, k)
    return np.interp(np.arange(n), xs, pts)


def adsr(d, a=0.01, r=0.3):
    n = N(d)
    e = np.ones(n)
    na, nr = N(a), N(r)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def fade(x, fi=0.05, fo=0.3):
    n = len(x)
    ni, no = min(n, N(fi)), min(n, N(fo))
    x = x.copy()
    if ni: x[:ni] *= np.linspace(0, 1, ni)
    if no: x[-no:] *= np.linspace(1, 0, no)
    return x


def reverb_ir(d=2.5, decay=3.0, bright=6000):
    n = N(d)
    t = np.arange(n) / SR
    ir = np.stack([white(d), white(d)]) * np.exp(-decay * t)
    ir = np.stack([filt(c, "lp", bright, 2) for c in ir])
    ir[:, : int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    return ir / np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))


IR_STREET = reverb_ir(2.2, 3.2, 5000)
IR_HALL = reverb_ir(3.5, 2.0, 3500)
IR_FAR = reverb_ir(4.5, 1.4, 1800)


def wet(x, ir, mix=0.35):
    """mono -> stereo with convolution reverb."""
    w = np.stack([signal.fftconvolve(x, ir[0])[: len(x)], signal.fftconvolve(x, ir[1])[: len(x)]])
    return np.stack([x, x]) * (1 - mix) + w * mix


def pan(x, p=0.0):
    if x.ndim == 2:
        return x
    l, r = np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)
    return np.stack([x * l, x * r]) * np.sqrt(2)


class Bus:
    def __init__(self, total):
        self.buf = np.zeros((2, N(total) + SR))

    def add(self, x, at, gain=1.0, p=0.0):
        x = pan(x, p) * gain
        i = N(at)
        if i >= self.buf.shape[1]:
            return
        n = min(x.shape[1], self.buf.shape[1] - i)
        self.buf[:, i : i + n] += x[:, :n]


# ---------- sound objects ----------
def quake_impact(d=3.0):
    t = t_axis(d)
    boom = np.sin(2 * np.pi * (38 - 10 * t) * t) * np.exp(-1.6 * t)
    crack = filt(white(d), "bp", [60, 900]) * np.exp(-9 * t)
    sub = filt(brown(d), "lp", 90) * np.exp(-1.2 * t)
    return boom * 0.9 + crack * 0.8 + sub * 0.8


def quake_rumble(d, intensity):
    """Long-period shaking: sub rumble + rattling + building creaks. intensity: array or scalar."""
    n = N(d)
    env = np.broadcast_to(np.asarray(intensity, float), (n,)) if np.ndim(intensity) else np.full(n, intensity)
    sub = filt(brown(d), "lp", 110) * (0.6 + 0.4 * smooth_rand(d, 5))
    roll = filt(white(d), "bp", [40, 180]) * smooth_rand(d, 3, 0.3, 1.0)
    rattle = filt(white(d), "bp", [900, 3500]) * smooth_rand(d, 18, 0, 1) ** 3 * 0.35
    clatter = np.zeros(n)
    for _ in range(int(d * 6)):
        i = rng.integers(0, max(1, n - 4000))
        L = rng.integers(400, 3000)
        clatter[i : i + L] += filt(white(L / SR), "bp", [rng.uniform(1500, 2500), rng.uniform(3500, 7000)]) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.1, 0.5)
    creak = np.zeros(n)
    tt = t_axis(d)
    for _ in range(max(1, int(d / 2.5))):
        c0 = rng.uniform(0, max(0.1, d - 1.5)); cl = rng.uniform(0.8, 1.6)
        m = (tt > c0) & (tt < c0 + cl)
        f0 = rng.uniform(70, 140)
        ph = 2 * np.pi * np.cumsum(f0 * (1 + 0.25 * np.sin(2 * np.pi * 0.7 * tt))) / SR
        saw = (ph / np.pi % 2) - 1
        creak += np.where(m, np.tanh(3 * saw) * np.sin(np.pi * np.clip((tt - c0) / cl, 0, 1)), 0) * 0.25
    creak = filt(creak, "bp", [80, 1200], 2)
    x = sub * 1.0 + roll * 0.5 + rattle + clatter + creak
    return x * env


def glass_stress(d=2.0):
    t = t_axis(d)
    x = np.zeros_like(t)
    for f in rng.uniform(2500, 7000, 7):
        t0 = rng.uniform(0, d * 0.7)
        x += np.sin(2 * np.pi * f * t) * np.exp(-25 * np.clip(t - t0, 0, None)) * (t > t0) * rng.uniform(0.05, 0.2)
    return x + filt(white(d), "hp", 5000) * 0.02 * smooth_rand(d, 10)


def sign_crash(d=1.6):
    t = t_axis(d)
    whoosh = filt(white(0.35), "bp", [300, 2000]) * np.linspace(0, 1, int(0.35 * SR)) ** 2 * 0.4
    hit = filt(white(d), "lp", 6000) * np.exp(-8 * t)
    metal = sum(np.sin(2 * np.pi * f * t) * np.exp(-a * t) for f, a in ((523, 5), (1387, 7), (2711, 9), (3990, 12))) * 0.3
    thud = np.sin(2 * np.pi * 55 * t) * np.exp(-10 * t)
    body = hit * 0.8 + metal + thud
    return np.concatenate([whoosh, body])


def car_alarm(d):
    t = t_axis(d)
    f = np.where((t * 2.2) % 1 < 0.5, 620, 930)
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3
    return filt(x, "bp", [400, 2500], 2) * adsr(d, 0.05, 0.4)


def alert_tone(d=3.2):
    """Original phone emergency alert: urgent rising triad, repeated, phone-speaker band."""
    out = np.zeros(N(d))
    pattern = [1046.5, 1318.5, 1568.0]
    step = 0.16
    k = 0
    t0 = 0.0
    while t0 < d - 0.2:
        f = pattern[k % 3]
        tt = t_axis(step * 0.92)
        tone = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.15 * np.sin(6 * np.pi * f * tt)) * adsr(step * 0.92, 0.005, 0.04)
        i = N(t0)
        out[i : i + len(tone)] += tone[: len(out) - i]
        k += 1
        t0 += step + (0.22 if k % 3 == 0 else 0)
    return filt(out, "bp", [350, 4500], 2) * 0.45


def siren(d, f_lo=430, f_hi=690, period=7.0):
    """Municipal outdoor warning siren (generic slow wail, heard from afar)."""
    t = t_axis(d)
    f = f_lo + (f_hi - f_lo) * (0.5 - 0.5 * np.cos(2 * np.pi * t / period))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)
    x *= 0.85 + 0.15 * np.sin(2 * np.pi * 5.5 * t)
    return filt(x, "lp", 2200, 2) * 0.3


def footsteps(d, rate=3.0):
    out = np.zeros(N(d))
    t0 = 0.05
    while t0 < d - 0.15:
        L = 0.11
        tt = t_axis(L)
        step = filt(white(L), "lp", 380) * np.exp(-35 * tt) * 1.2 + filt(white(L), "bp", [1500, 5000]) * np.exp(-90 * tt) * 0.35
        step += np.sin(2 * np.pi * 75 * tt) * np.exp(-40 * tt) * 0.6
        i = N(t0)
        out[i : i + len(step)] += step * rng.uniform(0.7, 1.0)
        t0 += 1 / rate * rng.uniform(0.93, 1.07)
    return out


def breathing(d, rate=1.45):
    out = np.zeros(N(d))
    t0 = 0.1
    k = 0
    while t0 < d - 0.4:
        L = 0.32 if k % 2 == 0 else 0.26
        b = filt(white(L), "bp", [450, 2400], 2) * np.sin(np.pi * np.linspace(0, 1, N(L))) ** 1.5
        i = N(t0)
        out[i : i + len(b)] += b * (0.5 if k % 2 == 0 else 0.38)
        t0 += 1 / (2 * rate) * rng.uniform(0.9, 1.1)
        k += 1
    return out


def tsunami_roar(d, swell):
    low = filt(brown(d), "lp", 160) * 1.2
    wash = filt(pink(d), "bp", [250, 1400]) * smooth_rand(d, 0.8, 0.4, 1.0)
    hiss = filt(white(d), "bp", [2000, 6000]) * smooth_rand(d, 1.2, 0, 1) ** 2 * 0.15
    crunch = np.zeros(N(d))
    for _ in range(int(d * 2.5)):
        i = rng.integers(0, len(crunch) - 12000)
        L = rng.integers(2000, 11000)
        crunch[i : i + L] += filt(white(L / SR), "bp", [80, rng.uniform(500, 1500)]) * np.exp(-np.arange(L) / (L / 5)) * rng.uniform(0.3, 0.8)
    return (low + wash + hiss + crunch) * swell


def wind(d, level=1.0):
    return filt(pink(d), "bp", [150, 900], 2) * smooth_rand(d, 0.6, 0.25, 1.0) * level


def fire_crackle(d):
    n = N(d)
    out = filt(brown(d), "lp", 300) * 0.35 * smooth_rand(d, 1.5, 0.5, 1)
    for _ in range(int(d * 22)):
        i = rng.integers(0, n - 800)
        L = rng.integers(60, 700)
        out[i : i + L] += filt(white(L / SR), "hp", 1200, 2) * np.exp(-np.arange(L) / (L / 3)) * rng.uniform(0.1, 0.7)
    return out


def room_tone(d):
    murmur = filt(pink(d), "bp", [180, 700], 2) * smooth_rand(d, 4, 0.5, 1.0) * 0.5
    return murmur + filt(white(d), "lp", 400) * 0.08


def surf(d):
    t = t_axis(d)
    sw = 0.55 + 0.45 * np.sin(2 * np.pi * t / 6.5 - 1.2) ** 2
    return (filt(pink(d), "bp", [200, 2500], 2) * sw + filt(brown(d), "lp", 150) * 0.4 * sw)


# ---------- music bed ----------
def osc_saw(f, d, detune=0.0):
    t = t_axis(d)
    ph = (f * (1 + detune)) * t
    return 2 * (ph % 1) - 1


def drone(d, notes, cutoff=420, lfo=0.07):
    t = t_axis(d)
    x = sum(osc_saw(f, d, dt) for f in notes for dt in (-0.004, 0.0, 0.0045)) / (3 * len(notes))
    # slowly sweeping low-pass
    blocks = 64
    out = np.zeros_like(x)
    seg = len(x) // blocks + 1
    zi = None
    sos_cache = None
    for b in range(blocks):
        s = slice(b * seg, min(len(x), (b + 1) * seg))
        if s.start >= len(x):
            break
        fc = cutoff * (0.75 + 0.35 * np.sin(2 * np.pi * lfo * t[s.start]))
        sos = signal.butter(2, fc, "lp", fs=SR, output="sos")
        if zi is None:
            zi = signal.sosfilt_zi(sos) * 0
        out[s], zi = signal.sosfilt(sos, x[s], zi=zi)
    return out


def glass_pad(d, freqs):
    t = t_axis(d)
    return sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in freqs) / len(freqs) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t))


def pulse(d, bpm=56, f=55):
    out = np.zeros(N(d))
    beat = 60 / bpm
    k = 0
    while k * beat < d - 0.6:
        tt = t_axis(0.6)
        hit = np.sin(2 * np.pi * f * tt * (1 + 0.6 * np.exp(-30 * tt))) * np.exp(-6 * tt)
        i = int(k * beat * SR)
        out[i : i + len(hit)] += hit * (1.0 if k % 2 == 0 else 0.6)
        k += 1
    return out


# ---------- arrangement ----------
def build(scenes, total, outdir, sign_impact=None):
    S = {int(k): v for k, v in scenes.items()}
    st = lambda i: S[i][0]
    en = lambda i: S[i][1]
    dur = lambda i: S[i][1] - S[i][0]
    fx = Bus(total)
    mu = Bus(total)
    SIGN_IMPACT = sign_impact if sign_impact is not None else st(2) + dur(2) * 0.55 + 0.35

    # 1-3: the quake. Impact at 0, long rumble that peaks in scene 3 and fades through scene 4.
    fx.add(wet(quake_impact(3.5), IR_STREET, 0.3), 0.0, 1.0)
    q_end = st(4) + dur(4) * 0.7
    qd = q_end
    tq = t_axis(qd)
    inten = np.interp(tq, [0, 0.6, st(3), st(3) + dur(3) * 0.6, st(4), q_end], [0.7, 1.0, 1.0, 1.15, 0.55, 0.0])
    fx.add(wet(fade(quake_rumble(qd, inten), 0.02, 1.2), IR_STREET, 0.25), 0.0, 0.85)
    fx.add(wet(glass_stress(2.2), IR_STREET, 0.4), st(2) + 0.1, 0.8, 0.3)
    fx.add(wet(sign_crash(1.8), IR_STREET, 0.35), SIGN_IMPACT - 0.35, 0.9, -0.25)
    fx.add(wet(car_alarm(en(4) - st(3)), IR_FAR, 0.6), st(3) + 0.4, 0.12, 0.6)

    # 4: phone alert, then outdoor siren that carries through scene 6
    fx.add(pan(alert_tone(3.0), 0.1), st(4) + 0.25, 0.55)
    sir_d = en(6) - (st(4) + 2.2) + 1.5
    fx.add(wet(fade(siren(sir_d), 1.5, 2.0), IR_FAR, 0.7), st(4) + 2.2, 0.32, -0.3)

    # 5: running uphill
    fx.add(wet(footsteps(dur(5), 3.1), IR_STREET, 0.2), st(5), 0.55)
    fx.add(breathing(dur(5) + dur(6) * 0.6), st(5) + 0.2, 0.35, 0.05)

    # 6: tsunami reaching the port
    sw_t = t_axis(dur(6) + 1.0)
    swell = np.interp(sw_t, [0, 1.0, dur(6) * 0.8, dur(6) + 1.0], [0.15, 0.6, 1.0, 0.0])
    fx.add(wet(tsunami_roar(dur(6) + 1.0, swell), IR_FAR, 0.45), st(6), 0.55)

    # 7: night, blackout: near silence, wind, very distant siren
    fx.add(fade(wind(dur(7) + dur(8), 1.0), 1.0, 1.5), st(7), 0.18)
    fx.add(wet(fade(siren(dur(7), 450, 640, 9.0), 2.0, 2.0), IR_FAR, 0.85), st(7) + 0.5, 0.06, 0.6)

    # 8: distant fires
    fx.add(wet(fade(fire_crackle(dur(8)), 1.0, 1.0), IR_FAR, 0.5), st(8), 0.22, -0.4)

    # 9: evacuation shelter (gym)
    fx.add(wet(fade(room_tone(dur(9)), 0.8, 0.8), IR_HALL, 0.5), st(9), 0.22)

    # 10-11: dawn on the hill, the sea comes back quietly
    fx.add(fade(surf(en(11) - st(10)), 2.0, 2.0), st(10), 0.16)
    fx.add(fade(wind(en(11) - st(10), 0.6), 1.5, 2.0), st(10), 0.08)

    # 12: low rumble rising into the cut (next episode)
    t12 = t_axis(dur(12))
    r12 = filt(brown(dur(12)), "lp", 90) * np.interp(t12, [0, dur(12) * 0.8, dur(12)], [0.0, 1.0, 0.0])
    fx.add(wet(r12, IR_FAR, 0.4), st(12), 0.7)

    # ---- music: uneasy drone, small ----
    a = st(2); b = st(10)
    dd = b - a
    dr = drone(dd, [73.42, 110.0, 155.56], cutoff=380)
    env = np.interp(t_axis(dd), [0, 2.0, st(6) - a, en(6) - a - 0.05, st(7) - a + 0.05, st(8) - a, st(9) - a, dd],
                    [0, 0.6, 0.75, 1.0, 0.16, 0.22, 0.28, 0.28])
    mu.add(wet(dr * env, IR_HALL, 0.5), a, 0.9)
    pad_a = st(6)
    mu.add(wet(fade(glass_pad(b - pad_a, [1174.7, 1244.5]), 2.0, 2.5), IR_HALL, 0.7), pad_a, 0.08)
    mu.add(fade(pulse(en(6) - st(5), 58, 55), 0.5, 1.0), st(5), 0.35)
    # 10-11: same root, a little light gets in (add major third and fifth), then out
    d2 = en(11) - b
    dr2 = drone(d2, [73.42, 110.0, 146.83, 185.0], cutoff=520)
    env2 = np.interp(t_axis(d2), [0, 1.5, d2 - 1.5, d2], [0.28, 0.42, 0.36, 0.0])
    mu.add(wet(dr2 * env2, IR_HALL, 0.55), b, 0.9)
    mu.add(wet(fade(glass_pad(d2, [880.0, 1108.7, 1318.5]), 2.5, 2.0), IR_HALL, 0.7), b, 0.035)
    # 12: drone drops back to the minor second and cuts with the picture
    d3 = dur(12)
    mu.add(wet(fade(drone(d3, [73.42, 77.78], cutoff=300), 0.3, 0.25), IR_HALL, 0.4), st(12), 0.5)

    for name, bus, peak in (("sfx", fx, 0.89), ("bgm", mu, 0.5)):
        x = bus.buf[:, : N(total)]
        x = x / (np.max(np.abs(x)) + 1e-9) * peak
        write_wav(f"{outdir}/{name}.wav", x)


def write_wav(path, x):
    y = np.clip(x.T, -1, 1)
    pcm = (y * 8388607).astype("<i4")
    b24 = pcm.reshape(-1).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR)
        w.writeframes(b24)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    build(cfg["scenes"], cfg["total"], sys.argv[2], cfg.get("sign_impact"))
    print("ok")
