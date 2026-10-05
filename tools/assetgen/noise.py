"""Periodic (tileable) noise + colour helpers shared by the texture generators."""
from __future__ import annotations
import numpy as np


def fbm(shape, beta=2.0, seed=0):
    """Tileable 1/f^beta noise normalised to ~[0,1] (periodic in both axes)."""
    h, w = shape
    rng = np.random.default_rng(seed)
    F = np.fft.rfft2(rng.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx ** 2 + fy ** 2); f[0, 0] = 1.0
    F *= 1.0 / f ** (beta / 2.0); F[0, 0] = 0
    out = np.fft.irfft2(F, s=(h, w))
    out = (out - out.mean()) / (out.std() + 1e-9)
    return np.clip(out / 6.0 + 0.5, 0.0, 1.0)


def blur(a, sigma_y, sigma_x=None):
    """Periodic gaussian blur (sigma in pixels)."""
    sigma_x = sigma_y if sigma_x is None else sigma_x
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    k = np.exp(-2 * (np.pi ** 2) * ((sigma_y * fy) ** 2 + (sigma_x * fx) ** 2))
    if a.ndim == 2:
        return np.fft.irfft2(np.fft.rfft2(a) * k, s=(h, w))
    return np.stack([np.fft.irfft2(np.fft.rfft2(a[..., c]) * k, s=(h, w)) for c in range(a.shape[2])], -1)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-12), 0, 1)
    return t * t * (3 - 2 * t)


def to_srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def to_u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def normal_map(height, strength=1.0):
    """OpenGL-style (+Y up) tangent-space normal map from a periodic height field."""
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    n = np.stack([-dx * strength, dy * strength, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return to_u8(n * 0.5 + 0.5)
