#!/usr/bin/env python3
"""Engine-free check of the chase camera.

Simulates a run at 25 m/s (physics 60 Hz, display 90 Hz, the engine's physics interpolation), with lane changes, a jump and a few
hits / near misses / landings, and measures how much the runner JITTERS on a 1080x1920 portrait screen:
    jitter = RMS of (screen position - the same signal smoothed over 0.35 s)   in pixels
for the 0.5.0 camera (rigid follow + look_at + shake + FOV swing, re-implemented from the old gd file) and the 0.6.0 camera
(damped follow, fixed yaw / pitch, no shake - the same maths as gameplay/camera/chase_camera.gd).
It also prints the framing (how big the runner is, where the horizon is, how far the three lanes are visible).

    python tools/camera_sim.py
"""
import math
import numpy as np

W, H = 1080, 1920
ASPECT = W / H
PHYS_DT = 1 / 60.0
DISPLAY_HZ = 90.0
SPEED = 25.0
LANES = (-3.2, 0.0, 3.2)
LATERAL = 0.72          # share of the runner's sideways offset the 0.6.0 camera follows (LATERAL_FOLLOW in chase_camera.gd)


# ------------------------------------------------------------------------------------------------ runner
def runner_ticks(duration):
    """Runner root position per physics tick: lane changes (exponential approach), one jump."""
    n = int(duration / PHYS_DT) + 3
    xs = np.zeros(n); ys = np.zeros(n); zs = np.zeros(n)
    x = 0.0; y = 0.0; vy = 0.0; z = 0.0
    targets = [(1.0, 3.2), (2.0, 0.0), (5.2, -3.2)]
    tx = 0.0
    for i in range(n):
        t = i * PHYS_DT
        for t0, v in targets:
            if t >= t0: tx = v
        x += np.clip((tx - x) * 18.0, -14.0, 14.0) * PHYS_DT
        if abs(t - 2.8) < PHYS_DT / 2: vy = 11.0
        if y > 0.0 or vy > 0.0:
            vy -= 32.0 * PHYS_DT; y += vy * PHYS_DT
            if y <= 0.0: y = 0.0; vy = 0.0
        z += SPEED * PHYS_DT
        xs[i], ys[i], zs[i] = x, y, z
    return np.c_[xs, ys, zs]


def interpolated(ticks, t):
    f = t / PHYS_DT; i = int(f); a = f - i
    return ticks[i] * (1 - a) + ticks[i + 1] * a


# ------------------------------------------------------------------------------------------------ projection
def project(point, cam_pos, cam_dir, fov_deg):
    fwd = cam_dir / np.linalg.norm(cam_dir)
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    d = point - cam_pos
    z = d @ fwd
    th = math.tan(math.radians(fov_deg) / 2)
    sx = W / 2 + (d @ right) / (z * th * ASPECT) * (W / 2)
    sy = H / 2 - (d @ up) / (z * th) * (H / 2)
    return np.array([sx, sy]), z


# ------------------------------------------------------------------------------------------------ cameras
class OldCamera:
    """gameplay/camera/chase_camera.gd of 0.5.0."""
    def __init__(self):
        self.dip = 0.0; self.shake = 0.0; self.st = 0.0; self.speed_factor = 0.0
        self.pos = np.zeros(3); self.dir = np.array([0, 0, 1.0]); self.fov = 62.0; self.h = 0.0; self.v = 0.0

    def tick(self, p, speed, dt):
        self.prev = (self.pos.copy(), self.dir.copy()) if hasattr(self, 'cur') else None
        self.dip = max(self.dip - dt * 0.9, 0.0)
        self.speed_factor += (np.clip((speed - 14.0) / 18.0, 0, 1) - self.speed_factor) * min(1.0, dt * 2.0)
        cam = np.array([p[0] * 0.62, 3.45 + p[1] * 0.5 - self.dip, p[2] - 9.4])
        look = np.array([p[0] * 0.8, 1.2, p[2] + 6.5])
        self.pos = cam; self.dir = look - cam
        self.fov = 62.0 + (74.0 - 62.0) * self.speed_factor
        if self.prev is None: self.prev = (cam.copy(), self.dir.copy())
        self.cur = (cam.copy(), self.dir.copy())

    def frame(self, dt, alpha=1.0):
        pos = self.prev[0] * (1 - alpha) + self.cur[0] * alpha                   # the engine interpolates the camera node between ticks
        dirv = self.prev[1] / np.linalg.norm(self.prev[1]) * (1 - alpha) + self.cur[1] / np.linalg.norm(self.cur[1]) * alpha
        if self.shake > 0.001:
            self.st += dt * 45.0
            self.h = math.sin(self.st * 1.3) * self.shake * 0.12; self.v = math.cos(self.st * 1.7) * self.shake * 0.09
            self.shake = max(0.0, self.shake - dt * 2.4)
        else:
            self.h = self.v = 0.0
        fwd = dirv / np.linalg.norm(dirv); right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
        return pos + right * self.h + up * self.v, dirv, self.fov


class NewCamera:
    """gameplay/camera/chase_camera.gd of 0.6.0 (same constants and maths)."""
    DIST, HEIGHT, PITCH = 7.2, 3.35, math.radians(13.0)

    def __init__(self):
        self.x = 0.0; self.up = 0.0; self.stretch = 0.0; self.boost = 0.0; self.impact = 0.0; self.dip = 0.0; self.impact_goal = 0.0; self.dip_goal = 0.0

    @staticmethod
    def damp(a, b, rate, dt):
        return a + (b - a) * (1 - math.exp(-rate * dt))

    def frame(self, p, speed, dt):
        self.x = self.damp(self.x, p[0] * LATERAL, 9.0, dt)
        self.up = self.damp(self.up, max(p[1], 0) * 0.30, 5.0, dt)
        self.stretch = self.damp(self.stretch, np.clip((speed - 20) / 12, 0, 1) * 0.7 * 0.6, 2.5, dt)
        self.boost = self.damp(self.boost, np.clip((speed - 18) / 14, 0, 1) * 0.6, 2.0, dt)
        self.impact_goal = self.damp(self.impact_goal, 0.0, 3.0, dt); self.impact = self.damp(self.impact, self.impact_goal, 26.0, dt)
        self.dip_goal = self.damp(self.dip_goal, 0.0, 7.0, dt); self.dip = self.damp(self.dip, self.dip_goal, 30.0, dt)
        cam = np.array([self.x, self.HEIGHT + self.up - self.dip, p[2] - self.DIST - self.stretch])
        pitch = self.PITCH + self.impact * 0.016
        d = np.array([0, -math.sin(pitch), math.cos(pitch)])
        return cam, d, 58.0 + self.boost * 3.5 + self.impact * 1.6


# ------------------------------------------------------------------------------------------------ run
def simulate(kind, events):
    dur = 6.0
    ticks = runner_ticks(dur + 1.0)
    cam = OldCamera() if kind == 'old' else NewCamera()
    out = []; t = 0.0; dt = 1 / DISPLAY_HZ; next_tick = 0.0; tick_i = 0
    ev = list(events)
    while t < dur:
        while next_tick <= t:                                   # physics ticks the engine has run by now
            if kind == 'old':
                cam.tick(ticks[tick_i], SPEED, PHYS_DT)
            next_tick += PHYS_DT; tick_i += 1
        while ev and ev[0][0] <= t:
            _, what, s = ev.pop(0)
            if kind == 'old':
                if what == 'kick': cam.shake = max(cam.shake, s)
                else: cam.dip = max(cam.dip, s * 0.20)
            else:
                if what == 'kick': cam.impact_goal = max(cam.impact_goal, s) if s >= 0.3 else cam.impact_goal
                else: cam.dip_goal = max(cam.dip_goal, s * 0.03)
        p = interpolated(ticks, t)
        if kind == 'old':
            # the old camera node is itself interpolated between its physics-tick transforms by the engine: emulate with the tick values
            f = (t - (tick_i - 1) * PHYS_DT) / PHYS_DT
            cam_pos, cam_dir, fov = cam.frame(dt, float(np.clip(f, 0, 1)))
        else:
            cam_pos, cam_dir, fov = cam.frame(p, SPEED, dt)
        s, z = project(p + np.array([0, 1.0, 0]), cam_pos, cam_dir, fov)
        out.append((t, s[0], s[1]))
        t += dt
    return np.array(out)


def jitter(sig, hz=DISPLAY_HZ, lo=6.0):
    """RMS (pixels) of everything above `lo` Hz: lane changes and jumps live below ~4 Hz, shake / stepping above."""
    sp = np.fft.rfft(sig - sig.mean())
    f = np.fft.rfftfreq(len(sig), 1.0 / hz)
    sp[f < lo] = 0
    hp = np.fft.irfft(sp, len(sig))
    return float(np.sqrt(np.mean(hp ** 2)))


def accel_window(r, t0, t1):
    """RMS of the second difference (px / frame^2) of the screen position inside a window: a 10 Hz shake is large here, a smooth settle is ~0."""
    m = (r[:, 0] >= t0) & (r[:, 0] <= t1)
    a = np.diff(r[m, 1:3], 2, axis=0)
    return float(np.sqrt(np.mean(a ** 2)))


def steady_window(r, t0, t1):
    """Unsteadiness: RMS distance (px) of the runner from its mean screen position in a window in which he runs straight and nothing
    should move except the events (landing, near misses, a shield hit)."""
    m = (r[:, 0] >= t0) & (r[:, 0] <= t1)
    return float(np.sqrt(np.mean((r[m, 1] - r[m, 1].mean()) ** 2 + (r[m, 2] - r[m, 2].mean()) ** 2)))


def main():
    events = [(0.6, 'kick', 0.12), (3.6, 'land', 0.8), (3.9, 'kick', 0.12), (4.4, 'kick', 0.6), (4.8, 'kick', 0.12)]
    res = {}
    for kind in ('old', 'new'):
        r = simulate(kind, events)
        res[kind] = r
        print(f'{kind.upper()} camera, running straight (landing, 2 near misses, 1 shield hit in the window): '
              f'motion {steady_window(r, 3.7, 5.1):5.2f} px RMS (includes the deliberate jump settle and hit punch), shake energy {accel_window(r, 3.7, 5.1):5.3f} px/frame^2 | '
              f'steady 0.3-0.95 s with one near miss: {steady_window(r, 0.3, 0.95):4.2f} px, {accel_window(r, 0.3, 0.95):5.3f} | '
              f'screen travel of lane changes + jump: x {np.ptp(r[:, 1]):.0f} px, y {np.ptp(r[:, 2]):.0f} px')
    print()
    # framing at rest, runner on the centre lane
    cam = NewCamera(); p = np.array([0.0, 0.0, 0.0])
    for _ in range(300): c, d, fov = cam.frame(p, SPEED, 1 / 60)
    feet, _ = project(np.array([0, 0.0, 0.0]), c, d, fov); head, _ = project(np.array([0, 1.93, 0.0]), c, d, fov)
    hor, _ = project(c + np.array([0, 0, 1000.0]), c, d, fov)
    print(f'0.6.0 framing (portrait {W}x{H}, FOV {fov:.1f}): runner from y={head[1] / H * 100:.0f}% to {feet[1] / H * 100:.0f}% of the screen height '
          f'(= {abs(feet[1] - head[1]) / H * 100:.0f}% tall), horizon at {hor[1] / H * 100:.0f}% from the top')
    for lx in LANES:
        s, z = project(np.array([lx, 0.0, 30.0]), c, d, fov)
        print(f'  lane x={lx:+.1f}: 30 m ahead of the runner at screen x={s[0]:5.0f} ({"inside" if 0 <= s[0] <= W else "OUTSIDE"} the screen), y={s[1] / H * 100:.0f}%')
    # the runner standing in the outer lane
    cam = NewCamera(); p = np.array([3.2, 0.0, 0.0])
    for _ in range(300): c, d, fov = cam.frame(p, SPEED, 1 / 60)
    s, _ = project(np.array([3.2, 1.0, 0.0]), c, d, fov)
    print(f'  runner in the right lane: screen x={s[0]:.0f} of {W} ({s[0] / W * 100:.0f}%)')
    old = OldCamera(); old.tick(np.array([0.0, 0.0, 0.0]), SPEED, 1 / 60); old.speed_factor = 0.6
    old.tick(np.array([0.0, 0.0, 0.0]), SPEED, 1 / 60); c, d, fov = old.frame(1 / 60)
    feet, _ = project(np.array([0, 0.0, 0.0]), c, d, fov); head, _ = project(np.array([0, 1.84, 0.0]), c, d, fov)
    print(f'0.5.0 framing for comparison: runner {abs(feet[1] - head[1]) / H * 100:.0f}% of the screen height (FOV {fov:.0f})')


if __name__ == '__main__':
    main()
