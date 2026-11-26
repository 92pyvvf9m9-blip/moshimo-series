#!/usr/bin/env python3
"""Sound design for the Fuji eruption episode: distant explosion -> the dry hiss of falling ash
("sara-sara") -> the silence of a blacked-out city. Everything is synthesized here (no recordings,
no copyrighted sounds). Event times come from the cut list, so the 60 s and 45 s edits both work.

  python sound.py EDIT.json OUTDIR      -> OUTDIR/sfx.wav, OUTDIR/bgm.wav
"""
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nankai-trough"))
import sound as S  # primitives from the Episode 1 sound design
from sound import SR, N, Bus, t_axis, white, brown, pink, filt, smooth_rand, fade, wet, pan, drone, glass_pad, write_wav

rng = np.random.default_rng(20261125)
IR_VALLEY = S.reverb_ir(6.0, 0.9, 1200)     # very long, dark: a blast heard from 100 km away


def distant_blast(d=9.0):
    t = t_axis(d)
    thump = np.sin(2 * np.pi * (30 - 8 * np.clip(t, 0, 1)) * t) * (1 - np.exp(-t / 0.08)) * np.exp(-t / 1.6)
    body = filt(brown(d), "lp", 70) * (1 - np.exp(-t / 0.15)) * np.exp(-t / 2.8)
    crackle = filt(white(d), "bp", [120, 700]) * np.exp(-((t - 0.9) ** 2) / 0.3) * 0.25
    rumble = filt(brown(d), "lp", 45) * np.clip(t / 2.0, 0, 1) * np.exp(-t / 5.5) * 0.8
    return thump * 1.0 + body * 0.9 + crackle + rumble


def eruption_roar(d):
    return filt(brown(d), "lp", 90) * (0.6 + 0.4 * smooth_rand(d, 0.7)) + filt(pink(d), "bp", [60, 240]) * 0.25 * smooth_rand(d, 1.5)


def ash_hiss(d, density):
    """Fine ash grains: many tiny ticks + a soft high band of hiss. density: array 0..1 or scalar."""
    n = N(d)
    dens = np.broadcast_to(np.asarray(density, float), (n,)) if np.ndim(density) else np.full(n, float(density))
    bed = filt(pink(d), "bp", [2500, 9000], 2) * (0.55 + 0.45 * smooth_rand(d, 2.0)) * 0.35
    ticks = np.zeros(n)
    rate = 1800  # grains per second at density 1
    k = int(rate * d)
    pos = rng.integers(0, n - 64, k)
    amp = rng.uniform(0.05, 0.4, k)
    keep = rng.random(k) < np.interp(pos, np.arange(n), dens)
    for p, a in zip(pos[keep], amp[keep]):
        L = int(rng.integers(8, 40))
        ticks[p:p + L] += rng.standard_normal(L) * a * np.exp(-np.arange(L) / (L / 3))
    ticks = filt(ticks, "hp", 3500, 2)
    return (bed + ticks) * dens


def city_hum(d):
    return filt(pink(d), "bp", [70, 380], 2) * (0.7 + 0.3 * smooth_rand(d, 0.5)) * 0.5


def shutter(d=2.0):
    t = t_axis(d)
    out = np.zeros(N(d))
    rate = 34
    for i in range(int(d * 0.8 * rate)):
        t0 = i / rate * (1 + 0.15 * np.sin(i))
        L = 900
        tt = np.arange(L) / SR
        click = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * a) for f, a in ((1830, 90), (3270, 120), (5110, 160)))
        click += filt(white(L / SR), "hp", 2000) * np.exp(-tt * 200) * 0.6
        j = N(t0)
        out[j:j + L] += click[: max(0, len(out) - j)] * 0.25
    clunk_t = d * 0.82
    j = N(clunk_t)
    tt = t_axis(d - clunk_t)
    out[j:] += (np.sin(2 * np.pi * 90 * tt) * np.exp(-tt * 14) + filt(white(d - clunk_t), "lp", 3000) * np.exp(-tt * 25) * 0.6)[: len(out) - j]
    return out


def murmur(d):
    """Distant crowd: many short formant-filtered noise 'syllables' (kept low and reverberant)."""
    out = np.zeros(N(d))
    for _ in range(int(d * 22)):
        L = int(rng.uniform(0.08, 0.22) * SR)
        f1 = rng.uniform(300, 800); f2 = rng.uniform(1000, 2400)
        syl = filt(white(L / SR), "bp", [f1 * 0.8, f1 * 1.2], 2) + 0.6 * filt(white(L / SR), "bp", [f2 * 0.85, f2 * 1.15], 2)
        syl *= np.sin(np.pi * np.linspace(0, 1, L)) ** 2
        j = int(rng.integers(0, N(d) - L))
        out[j:j + L] += syl * rng.uniform(0.2, 0.6)
    return out


def ash_steps(d, rate=1.9):
    out = np.zeros(N(d))
    t0 = 0.1
    while t0 < d - 0.3:
        L = 0.22
        tt = t_axis(L)
        st = filt(white(L), "lp", 260) * np.exp(-tt * 22) * 0.9
        grit = filt(white(L), "hp", 3000) * np.exp(-tt * 18) * (rng.random(N(L)) < 0.25) * 0.5
        j = N(t0)
        out[j:j + N(L)] += (st + grit)[: len(out) - j]
        t0 += 1 / rate * rng.uniform(0.94, 1.06)
    return out


def machinery(d):
    t = t_axis(d)
    f0 = 38 * (1 + 0.04 * smooth_rand(d, 0.4, -1, 1))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    eng = sum(np.sin(k * ph) / k for k in range(1, 7)) * (0.7 + 0.3 * np.sin(2 * np.pi * 7 * t))
    beep = np.where((t % 1.0) < 0.42, np.sin(2 * np.pi * 1050 * t), 0) * 0.12 * (t > d * 0.35)
    return filt(eng, "lp", 600, 2) * 0.5 + beep


def build(edit, outdir):
    E = json.load(open(edit, encoding="utf-8"))
    total = E["total"]
    cut = {c[0]: (c[1], c[2]) for c in E["cuts"]}
    has = lambda k: k in cut
    st = lambda k: cut[k][0]
    en = lambda k: cut[k][1]
    fx, mu = Bus(total), Bus(total)

    # 0 s: the eruption, heard from far away (Tokyo is ~100 km from Fuji)
    fx.add(wet(distant_blast(9.0), IR_VALLEY, 0.55), 0.0, 1.0)
    erupt_end = en("f04") if has("f04") else en("f02")
    fx.add(wet(fade(eruption_roar(erupt_end + 1.5), 0.6, 1.5), IR_VALLEY, 0.5), 0.3, 0.45)

    # hours later in Shinjuku: city hum that thins out; ash begins and thickens
    a0 = st("f05")
    day_end = st("f16")
    fx.add(fade(city_hum(day_end - a0), 0.8, 2.5), a0, 0.35)
    dd = day_end - a0
    dens = np.interp(t_axis(dd), [0, 1.5, dd * 0.5, dd], [0.0, 0.35, 0.8, 1.0])
    fx.add(wet(fade(ash_hiss(dd, dens), 0.5, 0.6), S.IR_STREET, 0.25), a0, 0.55)
    if has("f09"):
        fx.add(wet(shutter(1.6), S.IR_STREET, 0.3), st("f09") + 0.05, 0.55, 0.3)
    if has("f10"):
        fx.add(wet(fade(murmur(en("f10") - st("f09")), 0.4, 0.6), S.IR_FAR, 0.6), st("f09"), 0.12)
    walk_a = st("f12") if has("f12") else st("f15")
    walk_b = en("f15") if has("f15") else en("f12")
    fx.add(fade(ash_steps(walk_b - walk_a), 0.05, 0.3), walk_a, 0.45)

    # night: near silence, a whisper of ash, faint wind
    na, nb = st("f16"), en("f19")
    fx.add(fade(ash_hiss(nb - na, 0.45), 1.2, 1.0), na, 0.22)
    fx.add(fade(S.wind(nb - na, 0.8), 1.5, 1.0), na, 0.10)

    # dawn: the clean-up begins far away
    da = st("f20")
    db = en("f22") if has("f22") else en("f21")
    fx.add(wet(fade(machinery(db - da), 1.5, 1.5), S.IR_FAR, 0.7), da, 0.16)
    fx.add(fade(ash_hiss(db - da, 0.2), 1.0, 1.0), da, 0.12)

    # footbridge at dusk, looking west: wind and a little ash; then the next-episode rumble
    ba = st("f23"); bb = en("f25")
    fx.add(fade(S.wind(bb - ba, 1.0), 1.0, 1.2), ba, 0.16)
    fx.add(fade(ash_hiss(bb - ba, 0.3), 1.0, 1.0), ba, 0.12)
    ea, eb = st("f26"), en("f26")
    tt = t_axis(eb - ea)
    rum = filt(brown(eb - ea), "lp", 70) * np.interp(tt, [0, (eb - ea) * 0.7, eb - ea], [0, 1, 0])
    fx.add(wet(rum, IR_VALLEY, 0.4), ea, 0.75)

    # ---- music: small and uneasy (C with a flat 9th), drops away at night, cuts at the end ----
    m_a = st("f03") if has("f03") else st("f02")
    m_b = st("f16")
    d1 = m_b - m_a
    dr = drone(d1, [65.41, 98.0, 138.59], cutoff=360)
    env = np.interp(t_axis(d1), [0, 2.0, d1 - 0.6, d1], [0, 0.7, 0.85, 0.12])
    mu.add(wet(dr * env, S.IR_HALL, 0.5), m_a, 0.9)
    mu.add(wet(fade(glass_pad(d1, [1046.5, 1108.7]), 2.0, 1.0), S.IR_HALL, 0.7), m_a, 0.06)
    d2 = st("f20") - m_b
    mu.add(wet(drone(d2, [65.41, 69.30], cutoff=260) * 0.18, S.IR_HALL, 0.6), m_b, 0.9)
    d3 = ea - st("f20")
    env3 = np.interp(t_axis(d3), [0, 2.0, d3 - 1.0, d3], [0.1, 0.35, 0.45, 0.3])
    mu.add(wet(drone(d3, [65.41, 98.0, 130.81], cutoff=420) * env3, S.IR_HALL, 0.55), st("f20"), 0.9)
    mu.add(wet(fade(drone(eb - ea, [65.41, 69.30], cutoff=300), 0.2, 0.3), S.IR_HALL, 0.4), ea, 0.5)

    os.makedirs(outdir, exist_ok=True)
    for name, bus, peak in (("sfx", fx, 0.89), ("bgm", mu, 0.5)):
        x = bus.buf[:, : N(total)]
        x = x / (np.max(np.abs(x)) + 1e-9) * peak
        write_wav(os.path.join(outdir, f"{name}.wav"), x)
    print("ok", outdir)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
