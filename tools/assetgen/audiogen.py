"""Procedural audio: layered-synthesis SFX and 16-bar music loops (all original, deterministic)."""
from __future__ import annotations
import math, os, subprocess, wave
import numpy as np
from scipy import signal

SR = 44100
BPM = 120.0
BEAT = 60.0 / BPM            # 0.5 s
BAR = BEAT * 4               # 2.0 s


# ------------------------------------------------------------------ primitives
def n_of(sec): return int(round(sec * SR))
def tt(sec): return np.arange(n_of(sec)) / SR
def exp_env(n, tau): return np.exp(-np.arange(n) / SR / tau)
def rng_of(seed): return np.random.default_rng(seed)

def white(n, rng): return rng.standard_normal(n)

def pink(n, rng):
    F = np.fft.rfft(rng.standard_normal(n)); f = np.arange(len(F)); f[0] = 1
    x = np.fft.irfft(F / np.sqrt(f), n); return x / (np.abs(x).max() + 1e-9)

def _sos(kind, fc, order=2):
    return signal.butter(order, fc, kind, fs=SR, output='sos')

def lp(x, fc, order=2): return signal.sosfilt(_sos('lowpass', min(fc, SR * 0.45), order), x, axis=0)
def hp(x, fc, order=2): return signal.sosfilt(_sos('highpass', max(fc, 20), order), x, axis=0)
def bp(x, lo, hi, order=2): return signal.sosfilt(_sos('bandpass', [max(lo, 20), min(hi, SR * 0.45)], order), x, axis=0)

def sweep_bp(x, f0, f1, width=0.5, steps=20):
    """Band-pass whose centre glides f0 -> f1 across the clip (log-spaced), cross-faded."""
    n = len(x); out = np.zeros(n); pos = np.linspace(0, 1, steps)
    centres = f0 * (f1 / f0) ** pos
    tpos = np.linspace(0, 1, n)
    for c, p in zip(centres, pos):
        w = np.clip(1 - np.abs(tpos - p) * (steps - 1), 0, 1)
        out += bp(x, c / (1 + width), c * (1 + width)) * w
    return out

def reverb(x, rt60=0.5, mix=0.2, seed=3, stereo=False):
    rng = rng_of(seed); n = n_of(rt60 * 1.2)
    ir = rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / SR * 6.9 / rt60)[:, None]
    ir = lp(ir, 5500) ; ir[0] += 0.0
    if x.ndim == 1: xs = np.stack([x, x], -1) if stereo else x[:, None]
    else: xs = x
    outc = []
    for c in range(2 if stereo else 1):
        src = xs[:, c if xs.shape[1] > 1 else 0]
        wet = signal.fftconvolve(src, ir[:, c])[:len(src) + n]
        outc.append(wet)
    wet = np.stack(outc, -1); dry = np.zeros_like(wet); dry[:len(xs)] = xs if xs.shape[1] == wet.shape[1] else np.repeat(xs, wet.shape[1], 1)
    wet /= (np.abs(wet).max() + 1e-9) / (np.abs(dry).max() + 1e-9)
    return dry * (1 - mix) + wet * mix if stereo else (dry * (1 - mix) + wet * mix)[:, 0]

def norm(x, peak=0.9): return x / (np.abs(x).max() + 1e-9) * peak
def fade(x, a=0.003, r=0.01):
    x = x.copy(); na, nr = n_of(a), n_of(r)
    if na: x[:na] *= np.linspace(0, 1, na).reshape((-1,) + (1,) * (x.ndim - 1))
    if nr: x[-nr:] *= np.linspace(1, 0, nr).reshape((-1,) + (1,) * (x.ndim - 1))
    return x

def sine(f, sec, ph=0.0):
    t = tt(sec); f = np.broadcast_to(f, t.shape) if np.ndim(f) else f
    return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, t.shape)) / SR + ph) if np.ndim(f) else np.sin(2 * np.pi * f * t + ph)

def saw(f, sec, ph=0.0, maxh=40):
    t = tt(sec); K = max(1, min(maxh, int(0.42 * SR / max(f, 1))))
    out = np.zeros_like(t)
    for k in range(1, K + 1): out += np.sin(2 * np.pi * k * f * t + ph * k) / k
    return out * (2 / np.pi)

def square(f, sec, maxh=30):
    t = tt(sec); K = max(1, min(maxh, int(0.42 * SR / max(f, 1))))
    out = np.zeros_like(t)
    for k in range(1, K + 1, 2): out += np.sin(2 * np.pi * k * f * t) / k
    return out * (4 / np.pi) * 0.5

def fm_bell(f, sec, ratio=3.5, index=3.0, tau=None):
    t = tt(sec); tau = tau or sec / 3.5
    env = np.exp(-t / tau)
    mod = np.sin(2 * np.pi * f * ratio * t) * index * env
    return np.sin(2 * np.pi * f * t + mod) * env

def pluck(f, sec, bright=0.6, tau=0.18, maxh=24):
    t = tt(sec); K = max(1, min(maxh, int(0.42 * SR / f))); out = np.zeros_like(t)
    for k in range(1, K + 1):
        out += np.sin(2 * np.pi * k * f * t + k * 0.3) / k * np.exp(-t * (1.5 + k * (1.0 - bright) * 3.0) / tau)
    return out * 0.8

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def save_wav(path, x):
    x = np.clip(x, -1, 1); st = x.ndim == 2
    pcm = (x * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2 if st else 1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def save_ogg(path, x, q=3):
    pcm = np.ascontiguousarray(np.clip(x, -1, 1).astype('<f4'))
    p = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'libvorbis', '-q:a', str(q), path], input=pcm.tobytes(), capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode())

def soft(x, drive=1.0): return np.tanh(x * drive) / np.tanh(drive)


# ------------------------------------------------------------------ SFX
def sfx_ui_tap():
    r = rng_of(1); n = n_of(0.07)
    x = sine(1900, 0.07) * exp_env(n, 0.012) * 0.7 + hp(white(n, r), 3000) * exp_env(n, 0.004) * 0.25
    return fade(norm(x, 0.55))

def sfx_ui_confirm():
    x = fm_bell(784, 0.34, 3.0, 1.6, 0.10) * 0.7
    y = np.zeros(n_of(0.34)); b = fm_bell(1175, 0.26, 3.0, 1.4, 0.08) * 0.8; y[n_of(0.06):n_of(0.06) + len(b)] += b[:len(y) - n_of(0.06)]
    return fade(norm(reverb(x + y, 0.35, 0.18), 0.7), 0.002, 0.04)

def sfx_ui_cancel():
    x = fm_bell(392, 0.28, 2.0, 1.2, 0.09) + 0.6 * fm_bell(294, 0.28, 2.0, 1.2, 0.09)
    return fade(norm(reverb(x, 0.3, 0.14), 0.6), 0.002, 0.05)

def sfx_lane_change():
    r = rng_of(2); n = n_of(0.17); w = white(n, r)
    sw = sweep_bp(w, 500, 3200, 0.7) * np.sin(np.linspace(0, np.pi, n)) ** 1.5
    scuff = lp(white(n, r), 700) * exp_env(n, 0.035) * 0.35
    return fade(norm(sw + scuff, 0.62), 0.004, 0.03)

def sfx_jump():
    r = rng_of(3); n = n_of(0.34); t = tt(0.34)
    thump = np.sin(2 * np.pi * np.cumsum(90 + 80 * np.exp(-t / 0.05)) / SR) * exp_env(n, 0.07) * 0.9
    air = sweep_bp(white(n, r), 350, 2600, 0.8) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.65
    cloth = hp(white(n, r), 2500) * exp_env(n, 0.05) * 0.12
    return fade(norm(thump + air + cloth, 0.7), 0.002, 0.05)

def sfx_slide():
    r = rng_of(4); n = n_of(0.62)
    e = np.minimum(1, np.arange(n) / (SR * 0.04)) * np.exp(-np.arange(n) / SR / 0.35)
    sc = bp(pink(n, r), 600, 2400) * e * (0.8 + 0.2 * np.sin(2 * np.pi * 14 * tt(0.62)))
    rum = lp(pink(n, r), 160) * e * 0.8
    return fade(norm(sc + rum, 0.62), 0.004, 0.08)

def sfx_land():
    r = rng_of(5); n = n_of(0.24); t = tt(0.24)
    thump = np.sin(2 * np.pi * np.cumsum(55 + 60 * np.exp(-t / 0.03)) / SR) * exp_env(n, 0.06)
    slap = hp(white(n, r), 1800) * exp_env(n, 0.012) * 0.5; body = bp(white(n, r), 150, 380) * exp_env(n, 0.05) * 0.8
    return fade(norm(thump + slap + body, 0.75), 0.001, 0.04)

def sfx_pickup():
    r = rng_of(6); n = n_of(0.42)
    x = fm_bell(2093, 0.42, 2.0, 0.9, 0.12) * 0.7 + fm_bell(3136, 0.42, 2.0, 0.6, 0.09) * 0.45
    sh = hp(white(n, r), 7000) * exp_env(n, 0.03) * 0.12
    return fade(norm(reverb(x + sh, 0.3, 0.12), 0.6), 0.001, 0.05)

def sfx_reward():
    notes = [1047, 1319, 1568, 2093]; out = np.zeros(n_of(1.1))
    for i, f in enumerate(notes):
        b = fm_bell(f, 0.7, 3.0, 1.2, 0.18) * (0.55 + 0.15 * i); o = n_of(0.09 * i); out[o:o + len(b)] += b[:len(out) - o]
    out += hp(white(len(out), rng_of(7)), 6000) * exp_env(len(out), 0.25) * 0.05
    return fade(norm(reverb(out, 0.8, 0.28), 0.7), 0.002, 0.1)

def sfx_collision():
    r = rng_of(8); n = n_of(0.9); t = tt(0.9)
    boom = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t / 0.12)) / SR) * exp_env(n, 0.22)
    body = lp(white(n, r), 900) * exp_env(n, 0.12) * 0.9
    metal = bp(white(n, r), 900, 4200) * exp_env(n, 0.08) * (0.6 + 0.4 * np.sin(2 * np.pi * 190 * t)) * 0.7
    deb = hp(white(n, r), 4000) * exp_env(n, 0.3) * np.abs(white(n, r)) * 0.15
    return fade(norm(reverb(soft(boom * 1.2 + body + metal + deb, 1.6), 0.5, 0.15), 0.9), 0.001, 0.12)

def sfx_shield_on():
    r = rng_of(9); n = n_of(0.7); t = tt(0.7); f = 280 * (1900 / 280) ** (t / 0.7)
    ph = 2 * np.pi * np.cumsum(f) / SR; sweep = sum(np.sin(ph * k) / k for k in (1, 2, 3)) * np.sin(np.linspace(0, np.pi, n)) ** 0.7
    sh = sweep_bp(white(n, r), 1500, 7000, 0.5) * np.linspace(0, 1, n) ** 2 * 0.35
    chime = np.zeros(n); b = fm_bell(1568, 0.3, 2.5, 1.0, 0.1) * 0.5; o = n_of(0.4); chime[o:o + len(b)] += b[:n - o]
    return fade(norm(reverb(sweep * 0.5 + sh + chime, 0.6, 0.22), 0.7), 0.003, 0.08)

def sfx_shield_hit():
    r = rng_of(10); n = n_of(0.55); t = tt(0.55)
    glass = fm_bell(1250, 0.55, 3.7, 3.5, 0.13) * 0.6 + fm_bell(1870, 0.55, 2.9, 2.5, 0.09) * 0.35
    crack = hp(white(n, r), 2500) * exp_env(n, 0.05) * 0.8; thump = np.sin(2 * np.pi * 85 * t) * exp_env(n, 0.09)
    return fade(norm(reverb(glass + crack + thump * 0.8, 0.5, 0.2), 0.8), 0.001, 0.07)

def sfx_overdrive():
    r = rng_of(11); n = n_of(1.3); t = tt(1.3)
    f = 70 * (800 / 70) ** (t / 1.0); f = np.where(t > 1.0, 800, f)
    ph = 2 * np.pi * np.cumsum(f) / SR; s = sum(np.sin(ph * k) / k for k in range(1, 7))
    cutoff = lp(s, 2600) * np.minimum(1, t / 1.0) ** 1.5 * np.exp(-np.maximum(0, t - 1.0) / 0.1)
    rush = sweep_bp(white(n, r), 400, 6000, 0.8) * np.minimum(1, t) ** 2 * np.exp(-np.maximum(0, t - 1.05) / 0.12) * 0.7
    boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-np.maximum(0, t - 1.0) / 0.2) + 30) / SR) * np.exp(-np.maximum(0, t - 1.0) / 0.25) * (t > 1.0) * 1.2
    return fade(norm(reverb(soft(cutoff * 0.35 + rush + boom, 1.4), 0.6, 0.18), 0.85), 0.01, 0.15)

def sfx_overdrive_loop():
    r = rng_of(12); dur = 2.0; n = n_of(dur); t = tt(dur)
    d = sum(saw(55 * (1 + 0.003 * k), dur) for k in (-1, 0, 1)) * 0.3
    d = lp(d, 380) * (0.8 + 0.2 * np.sin(2 * np.pi * 6 * t)); air = bp(pink(n, r), 800, 3200) * 0.12 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t))
    x = norm(d + air, 0.5); xf = n_of(0.08)
    x[:xf] = x[:xf] * np.linspace(0, 1, xf) + x[-xf:] * np.linspace(1, 0, xf)   # equal-length loop crossfade
    return x[:-xf] if False else x

def sfx_purchase_success():
    r = rng_of(13); out = np.zeros(n_of(1.0))
    for i, (o, d) in enumerate(((0.0, 0.06), (0.08, 0.06))):
        c = bp(white(n_of(d), r), 3000, 9000) * exp_env(n_of(d), 0.02) * 0.5; out[n_of(o):n_of(o) + len(c)] += c
    for i, f in enumerate((1047, 1319, 1568)):
        b = fm_bell(f, 0.8, 3.0, 1.2, 0.22) * 0.6; o = n_of(0.16 + 0.05 * i); out[o:o + len(b)] += b[:len(out) - o]
    return fade(norm(reverb(out, 0.7, 0.25), 0.7), 0.001, 0.1)

def sfx_purchase_error():
    n = n_of(0.38); out = np.zeros(n)
    for o, f in ((0.0, 233), (0.13, 175)):
        s = lp(square(f, 0.2), 900) * exp_env(n_of(0.2), 0.12); out[n_of(o):n_of(o) + len(s)] += s
    return fade(norm(out, 0.55), 0.003, 0.05)

def sfx_near_miss():
    r = rng_of(14); n = n_of(0.3); w = white(n, r)
    x = sweep_bp(w, 1800, 7000, 0.6) * np.sin(np.linspace(0, np.pi, n)) ** 1.2
    t = tt(0.3); d = np.sin(2 * np.pi * np.cumsum(900 - 500 * (t / 0.3)) / SR) * np.sin(np.linspace(0, np.pi, n)) * 0.18
    return fade(norm(x + d, 0.6), 0.004, 0.05)

def sfx_power_ready():
    out = np.zeros(n_of(0.34))
    for o, f in ((0.0, 1250), (0.09, 1880)):
        b = fm_bell(f, 0.22, 2.0, 0.8, 0.08); out[n_of(o):n_of(o) + len(b)] += b[:len(out) - n_of(o)]
    return fade(norm(reverb(out, 0.3, 0.12), 0.55), 0.001, 0.04)

def sfx_countdown(go=False):
    if not go: return fade(norm(fm_bell(880, 0.18, 2.0, 0.8, 0.06), 0.55), 0.001, 0.03)
    x = sum(fm_bell(f, 0.5, 2.0, 0.9, 0.16) for f in (880, 1320, 1760))
    return fade(norm(reverb(x, 0.4, 0.15), 0.7), 0.001, 0.08)

def sfx_revive():
    n = n_of(1.0); t = tt(1.0); pad = sum(np.sin(2 * np.pi * f * t) for f in (261.6, 329.6, 392, 523.3)) * np.sin(np.linspace(0, np.pi, n)) ** 1.3 * 0.2
    ch = np.zeros(n); b = fm_bell(1568, 0.6, 3.0, 1.0, 0.2) * 0.6; o = n_of(0.35); ch[o:o + len(b)] += b[:n - o]
    return fade(norm(reverb(pad + ch, 0.7, 0.25), 0.7), 0.02, 0.1)

SFX = {
    'generated/ui_tap': sfx_ui_tap, 'sfx/ui_confirm': sfx_ui_confirm, 'sfx/ui_cancel': sfx_ui_cancel,
    'generated/lane_change': sfx_lane_change, 'sfx/jump': sfx_jump, 'sfx/slide': sfx_slide, 'sfx/land': sfx_land,
    'generated/pickup': sfx_pickup, 'sfx/reward': sfx_reward, 'sfx/purchase_success': sfx_purchase_success,
    'sfx/purchase_error': sfx_purchase_error, 'sfx/collision': sfx_collision, 'sfx/shield_on': sfx_shield_on,
    'sfx/shield_hit': sfx_shield_hit, 'generated/overdrive': sfx_overdrive, 'sfx/overdrive_loop': sfx_overdrive_loop,
    'sfx/near_miss': sfx_near_miss, 'sfx/power_ready': sfx_power_ready, 'sfx/countdown': lambda: sfx_countdown(False),
    'sfx/go': lambda: sfx_countdown(True), 'sfx/revive': sfx_revive,
}


# ------------------------------------------------------------------ drums
def kick(vol=1.0, deep=1.0):
    n = n_of(0.45); t = tt(0.45)
    body = np.sin(2 * np.pi * np.cumsum(46 + 120 * np.exp(-t / 0.035) * deep) / SR) * exp_env(n, 0.16)
    click = hp(white(n, rng_of(21)), 2500) * exp_env(n, 0.003) * 0.3
    return (body + click) * vol

def snare(vol=1.0, tone=190):
    n = n_of(0.32); r = rng_of(22); t = tt(0.32)
    return (bp(white(n, r), 1200, 6500) * exp_env(n, 0.09) * 0.8 + np.sin(2 * np.pi * tone * t) * exp_env(n, 0.05) * 0.5) * vol

def clap(vol=1.0):
    n = n_of(0.3); r = rng_of(23); out = np.zeros(n)
    for o in (0.0, 0.011, 0.024): out[n_of(o):] += bp(white(n - n_of(o), r), 1000, 3200) * exp_env(n - n_of(o), 0.015) * 0.6
    out += bp(white(n, r), 900, 2800) * exp_env(n, 0.09) * 0.5
    return out * vol

def hat(vol=1.0, open_=False):
    n = n_of(0.22 if open_ else 0.06); r = rng_of(24 + int(open_))
    return hp(white(n, r), 7500) * exp_env(n, 0.09 if open_ else 0.018) * vol

def tom(vol=1.0, f=110):
    n = n_of(0.4); t = tt(0.4)
    return np.sin(2 * np.pi * np.cumsum(f * 0.6 + f * 0.8 * np.exp(-t / 0.05)) / SR) * exp_env(n, 0.13) * vol

def metal(vol=1.0):
    n = n_of(0.35); r = rng_of(26); t = tt(0.35)
    return bp(white(n, r), 1500, 7000) * np.sin(2 * np.pi * 311 * t) * exp_env(n, 0.1) * vol

def put(buf, x, at, pan=0.0, gain=1.0):
    o = n_of(at)
    if o >= len(buf): return
    m = min(len(x), len(buf) - o)
    l = gain * math.cos((pan + 1) * math.pi / 4); rr = gain * math.sin((pan + 1) * math.pi / 4)
    buf[o:o + m, 0] += x[:m] * l * 1.414; buf[o:o + m, 1] += x[:m] * rr * 1.414


# ------------------------------------------------------------------ music
CHORDS = {'min': (0, 3, 7), 'maj': (0, 4, 7), 'min7': (0, 3, 7, 10), 'maj7': (0, 4, 7, 11), 'sus2': (0, 2, 7), 'dom': (0, 4, 7, 10)}

STYLES = {
    # root = MIDI note of the tonic (bass register +12 for pads)
    'district_old_quarter':    dict(root=45, prog=[(0, 'min7'), (8, 'maj7'), (3, 'maj'), (10, 'dom')], arp='pluck', arp_pat=[0, 2, 1, 2, 3, 2, 1, 2], drum='folk', bass='root', pad=0.26, bright=0.5, seed=101),
    'district_transit_core':   dict(root=50, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], arp='saw', arp_pat=[0, 1, 2, 1, 3, 2, 1, 2, 0, 1, 2, 3, 2, 1, 2, 1], drum='four', bass='eighth', pad=0.2, bright=0.6, seed=102),
    'district_harbor_arc':     dict(root=40, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], arp='pluck', arp_pat=[0, None, 1, None, 2, None, 1, None], drum='half', bass='long', pad=0.34, bright=0.35, seed=103),
    'district_industrial_belt': dict(root=48, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], arp='stab', arp_pat=[0, None, None, 1, None, None, 2, None], drum='heavy', bass='drive', pad=0.18, bright=0.3, seed=104),
    'district_skyline_works':  dict(root=43, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], arp='saw', arp_pat=[0, 1, 2, 3, 2, 1, 2, 3, 4, 3, 2, 1, 2, 3, 2, 1], drum='four', bass='off', pad=0.24, bright=0.8, seed=105),
    'district_neon_market':    dict(root=47, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], arp='square', arp_pat=[0, 1, 2, 1, 0, 1, 2, 3], drum='synth', bass='sixteenth', pad=0.28, bright=0.7, seed=106),
    'district_stormline':      dict(root=41, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], arp='trem', arp_pat=[0, 1, 2, 1, 2, 3, 2, 1], drum='storm', bass='long', pad=0.3, bright=0.45, seed=107),
    'district_central_spire':  dict(root=45, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (7, 'dom')], arp='brass', arp_pat=[0, 2, 1, 2, 3, 2, 4, 2], drum='epic', bass='long', pad=0.38, bright=0.55, seed=108),
    'menu':                    dict(root=48, prog=[(0, 'maj7'), (9, 'min7'), (5, 'maj7'), (7, 'dom')], arp='bell', arp_pat=[0, None, 2, None, 1, None, 3, None], drum='soft', bass='long', pad=0.34, bright=0.4, seed=109),
    'event':                   dict(root=52, prog=[(0, 'min'), (8, 'maj'), (3, 'maj'), (10, 'maj')], arp='saw', arp_pat=[0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 1, 3, 2, 4, 3, 2], drum='four', bass='sixteenth', pad=0.22, bright=0.85, seed=110),
}

def _tones(root, off, qual, octave_span=3):
    base = root + off; notes = []
    for o in range(octave_span):
        for iv in CHORDS[qual]: notes.append(base + iv + 12 * o)
    return notes

def _drum_pattern(style, bar, buf, rng):
    """Add one bar of drums starting at bar*BAR."""
    s16 = BEAT / 4; t0 = bar * BAR
    K, SN, HH, CL, TM, MT = kick(), snare(), hat(), clap(), tom(), metal()
    hat_o = hat(1.0, True)
    def at(i): return t0 + i * s16
    if style == 'folk':
        for i in (0, 8): put(buf, K, at(i), 0, 0.55)
        for i in (4, 12): put(buf, snare(0.5, 230), at(i), 0.1, 0.35)
        for i in range(0, 16, 2): put(buf, hat(0.6), at(i), 0.3, 0.12 + 0.05 * (i % 4 == 0))
    elif style == 'four':
        for i in (0, 4, 8, 12): put(buf, K, at(i), 0, 0.85)
        for i in (4, 12): put(buf, CL, at(i), 0.05, 0.4)
        for i in (2, 6, 10, 14): put(buf, hat_o, at(i), 0.2, 0.16)
        for i in range(0, 16, 2): put(buf, HH, at(i + 1) if i + 1 < 16 else at(i), -0.2, 0.08)
    elif style == 'half':
        for i in (0, 10): put(buf, K, at(i), 0, 0.9)
        put(buf, SN, at(8), 0, 0.5)
        for i in (12, 14): put(buf, tom(0.7, 90), at(i), -0.3, 0.3)
        for i in range(0, 16, 4): put(buf, HH, at(i), 0.3, 0.1)
    elif style == 'heavy':
        for i in (0, 3, 6, 8, 11, 14): put(buf, kick(1.0, 1.3), at(i), 0, 0.95)
        for i in (4, 12): put(buf, SN, at(i), 0, 0.6)
        for i in (2, 7, 10, 15): put(buf, MT, at(i), 0.25, 0.3)
        for i in range(0, 16, 2): put(buf, HH, at(i), -0.2, 0.1)
    elif style == 'synth':
        for i in (0, 4, 8, 12): put(buf, K, at(i), 0, 0.8)
        for i in (4, 12): put(buf, snare(1.0, 170), at(i), 0, 0.55); put(buf, CL, at(i), 0, 0.35)
        for i in range(0, 16): put(buf, HH, at(i), 0.2 if i % 2 else -0.2, 0.07 + 0.05 * (i % 4 == 2))
    elif style == 'storm':
        for i in (0, 6, 8, 11): put(buf, K, at(i), 0, 0.85)
        for i in (4, 12): put(buf, SN, at(i), 0, 0.55)
        for i in range(16): put(buf, HH, at(i), 0.3 if i % 2 else -0.3, 0.08 + 0.04 * (i % 4 == 0))
        if bar % 4 == 3:
            for i in (12, 13, 14, 15): put(buf, tom(0.8, 100 + 12 * (i - 12)), at(i), 0.0, 0.35)
    elif style == 'epic':
        for i in (0, 6, 8, 14): put(buf, kick(1.0, 1.2), at(i), 0, 0.9)
        for i in (4, 12): put(buf, snare(1.0, 160), at(i), 0, 0.7)
        for i in (0, 8): put(buf, tom(0.9, 70), at(i), -0.2, 0.3)
        for i in range(0, 16, 2): put(buf, HH, at(i), 0.25, 0.1)
        if bar % 4 == 3:
            for i in range(12, 16): put(buf, tom(0.8, 140 - 12 * (i - 12)), at(i), 0.2 * (i - 13), 0.4)
    elif style == 'soft':
        if bar % 2 == 0: put(buf, kick(0.7), at(0), 0, 0.4)
        for i in (4, 12): put(buf, hat(0.8), at(i), 0.3, 0.1)
        put(buf, snare(0.4, 250), at(8), 0.1, 0.18)

def render_music(name, spec, bars=16, tail_bars=1):
    rng = rng_of(spec['seed']); style = spec['drum']
    total = (bars + tail_bars) * BAR
    L = n_of(total)
    drums = np.zeros((L, 2)); pad_b = np.zeros((L, 2)); bass_b = np.zeros((L, 2)); arp_b = np.zeros((L, 2)); lead_b = np.zeros((L, 2))
    s16 = BEAT / 4
    kick_times = []
    for bar in range(bars):
        _drum_pattern(style, bar, drums, rng)
        if style in ('four', 'synth', 'storm', 'heavy', 'epic', 'half', 'folk', 'soft'):
            kick_times += [bar * BAR + i * s16 for i in {'four': (0, 4, 8, 12), 'synth': (0, 4, 8, 12), 'storm': (0, 6, 8, 11), 'heavy': (0, 3, 6, 8, 11, 14), 'epic': (0, 6, 8, 14), 'half': (0, 10), 'folk': (0, 8), 'soft': (0,) if bar % 2 == 0 else ()}[style]]
    root = spec['root']; prog = spec['prog']
    for ci in range(bars // 2):
        off, qual = prog[ci % len(prog)]
        t0 = ci * 2 * BAR; tones = _tones(root + 12, off, qual, 3); chord = [root + 12 + off + iv for iv in CHORDS[qual]]
        # pad: 3 detuned saws per note, slow attack/release, lowpassed
        pd = np.zeros((n_of(2 * BAR + 0.6), 2))
        for k, nt in enumerate(chord):
            for side, det in ((0, -7), (1, +7), (0, 0), (1, 0)):
                f = midi(nt) * 2 ** (det / 1200); v = saw(f, 2 * BAR + 0.6, maxh=14)
                pd[:, side] += v * (0.5 if det == 0 else 1.0)
        env = np.minimum(1, tt(2 * BAR + 0.6) / 0.9) * np.minimum(1, (2 * BAR + 0.6 - tt(2 * BAR + 0.6)) / 0.6)
        pd = lp(pd, 900 + 2600 * spec['bright']) * env[:, None] * spec['pad'] * 0.16
        o = n_of(t0); pad_b[o:o + len(pd)] += pd[:len(pad_b) - o]
        # bass
        bnote = root + off - 12 + 12 * 0
        bp_ = spec['bass']
        steps = {'root': [(0, 8)], 'eighth': [(i, 2) for i in range(0, 16, 2)] * 2, 'long': [(0, 16)], 'drive': [(0, 3), (3, 3), (6, 2), (8, 3), (11, 3), (14, 2)], 'off': [(2, 2), (6, 2), (10, 2), (14, 2)] * 1, 'sixteenth': [(i, 1) for i in range(16)]}[bp_]
        for bar_i in range(2):
            for (st, ln) in steps:
                if bp_ in ('eighth', 'long') and False: continue
                if bp_ == 'eighth' and st >= 16: pass
                tpos = t0 + bar_i * BAR + st * s16
                dur = max(0.12, ln * s16 * (0.95 if bp_ in ('long', 'root') else 0.8))
                f = midi(bnote + (12 if (bp_ == 'sixteenth' and st % 8 in (3, 6)) else 0))
                v = lp(saw(f, dur, maxh=10) * 0.6 + sine(f, dur) * 0.9, 260 + 700 * (bp_ in ('drive',))) * np.minimum(1, tt(dur) / 0.004) * np.exp(-tt(dur) / (dur * 0.8))
                if bp_ == 'drive': v = soft(v * 3.5, 1.2)
                put(bass_b, v, tpos, 0.0, 0.5)
        # arp
        pat = spec['arp_pat']; kind = spec['arp']
        for bar_i in range(2):
            for i in range(16):
                p = pat[i % len(pat)] if kind not in ('brass', 'bell', 'stab') else pat[(i // (2 if kind != 'stab' else 1)) % len(pat)] if (i % 2 == 0 or kind == 'stab') else None
                if len(pat) == 16: p = pat[i]
                elif len(pat) == 8 and kind in ('pluck', 'trem'): p = pat[i % 8] if i % 2 == 0 else None
                elif len(pat) == 8 and kind == 'square': p = pat[i % 8]
                if p is None: continue
                nt = tones[min(p + 3, len(tones) - 1)] + (12 if (ci % 4 >= 2 and kind in ('saw', 'square')) else 0)
                tpos = t0 + bar_i * BAR + i * s16; f = midi(nt)
                if kind == 'pluck': v = pluck(f, 0.55, spec['bright'], 0.22) * 0.9
                elif kind == 'saw': v = lp(saw(f, 0.26, maxh=16), 3200 * spec['bright'] + 1200) * exp_env(n_of(0.26), 0.14)
                elif kind == 'square': v = lp(square(f, 0.3), 2600) * exp_env(n_of(0.3), 0.16) * 1.4
                elif kind == 'trem': v = pluck(f, 0.5, 0.5, 0.2) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt(0.5)))
                elif kind == 'brass': v = lp(saw(f, 0.9, maxh=12), 1500) * np.minimum(1, tt(0.9) / 0.05) * np.exp(-tt(0.9) / 0.55) * 0.9
                elif kind == 'stab': v = soft(lp(saw(midi(nt - 12), 0.22, maxh=10), 1400) * exp_env(n_of(0.22), 0.1) * 2.4, 1.2)
                else: v = fm_bell(f, 1.0, 3.5, 1.0, 0.45) * 0.8
                put(arp_b, v, tpos, 0.35 if (i // 2) % 2 == 0 else -0.35, 0.35)
        # lead melody in second half of the loop
        if ci >= bars // 4 and kind not in ('bell',):
            motif = [0, 2, 4, 2, 0, -1, 0, 2][:]
            for k_, m_ in enumerate(motif):
                if k_ % 2 == 1 and ci % 2 == 0: continue
                nt = tones[min(max(m_ + 6, 0), len(tones) - 1)]; dur = BEAT * 0.9
                v = lp(saw(midi(nt), dur, maxh=12) + 0.5 * saw(midi(nt) * 1.004, dur, maxh=12), 2800) * np.minimum(1, tt(dur) / 0.015) * np.exp(-tt(dur) / 0.4)
                put(lead_b, v, t0 + k_ * BEAT, 0.0, 0.2)
    # delay for arp (dotted 8th ping-pong)
    dly = np.zeros_like(arp_b); d = n_of(BEAT * 0.75)
    for k in range(1, 4):
        sh = d * k
        if sh < L:
            dly[sh:, 0] += arp_b[:L - sh, 1] * 0.38 ** k; dly[sh:, 1] += arp_b[:L - sh, 0] * 0.38 ** k
    arp_b = arp_b + dly
    # sidechain duck from kick times
    duck = np.ones(L)
    for kt in kick_times:
        o = n_of(kt); m = min(n_of(0.35), L - o)
        if m > 0: duck[o:o + m] = np.minimum(duck[o:o + m], 1 - 0.55 * np.exp(-np.arange(m) / SR / 0.11))
    mix = drums * 0.9 + (pad_b * 1.0 + bass_b * 1.0 + arp_b * 0.9 + lead_b * 0.8) * duck[:, None]
    if name == 'district_stormline':
        r = rng_of(77); rum = lp(pink(L, r), 140)[:, None] * (0.5 + 0.5 * np.sin(2 * np.pi * np.arange(L) / SR / (BAR * 4)))[:, None] * 0.28; mix += rum
    mix = reverb(mix, 0.9, 0.16, seed=spec['seed'], stereo=True)[:L]
    mix = soft(mix * 1.1, 1.3)
    # seamless loop: fold the tail back onto the head
    loop = n_of(bars * BAR); out = mix[:loop].copy(); tail = mix[loop:loop + (L - loop)]
    out[:len(tail)] += tail
    out = hp(out, 28)
    return out / (np.abs(out).max() + 1e-9) * 0.56      # background-music level (about -16 dBFS RMS)

def render_chase():
    bars = 16; L = n_of(bars * BAR); buf = np.zeros((L, 2)); rng = rng_of(201); s16 = BEAT / 4
    for bar in range(bars):
        t0 = bar * BAR
        for i in (0, 4, 8, 12): put(buf, kick(1.0, 1.1), t0 + i * s16, 0, 0.7)
        for i in range(16): put(buf, hat(1.0), t0 + i * s16, 0.3 if i % 2 else -0.3, 0.14 + 0.06 * (i % 4 == 2))
        for i in (2, 6, 10, 14): put(buf, tom(0.7, 120 if i % 8 == 2 else 95), t0 + i * s16, -0.2, 0.28)
        for i in (4, 12): put(buf, snare(1.0, 200), t0 + i * s16, 0, 0.45)
        if bar % 4 == 3:
            for i in range(12, 16): put(buf, snare(0.9, 210), t0 + i * s16, 0.0, 0.3 + 0.05 * (i - 12))
    buf = reverb(buf, 0.5, 0.1, seed=201, stereo=True)[:L]
    return norm(soft(buf, 1.2), 0.5)

def render_overdrive():
    bars = 16; L = n_of(bars * BAR); buf = np.zeros((L, 2)); r = rng_of(202); s16 = BEAT / 4
    for bar in range(bars):
        t0 = bar * BAR
        if bar % 4 == 0:  # riser swell over 4 bars
            n = n_of(4 * BAR); w = sweep_bp(white(n, r), 300, 9000, 0.9, 30) * np.linspace(0, 1, n) ** 2.2 * 0.5
            put(buf, w, t0, 0.0, 0.6)
        for i in range(0, 16, 1):
            h = hp(white(n_of(0.05), r), 6500) * exp_env(n_of(0.05), 0.015) * (0.5 + 0.5 * (i % 2 == 0))
            put(buf, h, t0 + i * s16, -0.4 if i % 2 else 0.4, 0.16)
        for i in (0, 8): put(buf, np.sin(2 * np.pi * 52 * tt(0.4)) * exp_env(n_of(0.4), 0.12), t0 + i * s16, 0, 0.35)
    buf = reverb(buf, 0.7, 0.15, seed=202, stereo=True)[:L]
    return norm(soft(buf, 1.1), 0.45)

def render_reward():
    notes = [60, 64, 67, 72, 76, 79, 84]; L = n_of(9.0); buf = np.zeros((L, 2))
    for i, nt in enumerate(notes):
        put(buf, fm_bell(midi(nt + 12), 2.5, 3.0, 1.1, 0.6) * 0.7, 0.18 * i, (i - 3) * 0.12, 0.5)
    for k, nt in enumerate((60, 64, 67, 72)):
        put(buf, lp(saw(midi(nt), 5.0, maxh=10), 1800) * np.minimum(1, tt(5.0) / 0.6) * np.exp(-tt(5.0) / 2.4), 1.6, (k - 1.5) * 0.3, 0.14)
    buf = reverb(buf, 1.6, 0.3, seed=203, stereo=True)[:L]
    return fade(norm(buf, 0.6), 0.01, 0.6)

MUSIC = {f'music_ogg/{n}': (lambda n=n, s=s: render_music(n, s)) for n, s in STYLES.items()}
MUSIC['music_ogg/chase'] = render_chase; MUSIC['music_ogg/overdrive'] = render_overdrive; MUSIC['music_ogg/reward'] = render_reward


def generate_all(audio_dir, only=None, log=print):
    """Write every SFX (.wav) and music loop (.ogg) under audio_dir. Returns {relative_path: bytes}."""
    os.makedirs(os.path.join(audio_dir, 'sfx'), exist_ok=True); os.makedirs(os.path.join(audio_dir, 'generated'), exist_ok=True); os.makedirs(os.path.join(audio_dir, 'music_ogg'), exist_ok=True)
    out = {}
    for key, fn in SFX.items():
        if only and key not in only: continue
        p = os.path.join(audio_dir, key + '.wav'); save_wav(p, fn()); out[key + '.wav'] = os.path.getsize(p)
    for key, fn in MUSIC.items():
        if only and key not in only: continue
        p = os.path.join(audio_dir, key + '.ogg'); save_ogg(p, fn()); out[key + '.ogg'] = os.path.getsize(p); log('  ', key, out[key + '.ogg'] // 1024, 'KB')
    return out
