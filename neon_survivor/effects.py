import pygame
import random
import math
from settings import *

vec = pygame.math.Vector2


# ─── PARTICLE POOL ────────────────────────────────────────────

class ParticlePool:
    def __init__(self, max_particles=500):
        self.max = max_particles
        self.positions = [vec(0, 0) for _ in range(max_particles)]
        self.velocities = [vec(0, 0) for _ in range(max_particles)]
        self.colors = [(0, 0, 0) for _ in range(max_particles)]
        self.lives = [0] * max_particles
        self.decays = [0] * max_particles
        self.sizes = [3] * max_particles
        self.count = 0

    def emit(self, pos, color, count=10, speed=3.0, size=3):
        for _ in range(count):
            if self.count >= self.max:
                return
            i = self.count
            self.positions[i] = vec(pos)
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(0.5, speed)
            self.velocities[i] = vec(math.cos(angle) * spd, math.sin(angle) * spd)
            self.colors[i] = color
            self.lives[i] = 255
            self.decays[i] = random.randint(5, 12)
            self.sizes[i] = random.randint(max(1, size - 1), size + 1)
            self.count += 1

    def emit_directional(self, pos, color, direction, count=5, spread=0.5, speed=5.0):
        base_angle = math.atan2(direction.y, direction.x)
        for _ in range(count):
            if self.count >= self.max:
                return
            i = self.count
            self.positions[i] = vec(pos)
            angle = base_angle + random.uniform(-spread, spread)
            spd = random.uniform(speed * 0.5, speed)
            self.velocities[i] = vec(math.cos(angle) * spd, math.sin(angle) * spd)
            self.colors[i] = color
            self.lives[i] = 200
            self.decays[i] = random.randint(6, 14)
            self.sizes[i] = random.randint(2, 4)
            self.count += 1

    def update(self):
        i = 0
        while i < self.count:
            self.positions[i] += self.velocities[i]
            self.velocities[i] *= 0.96
            self.lives[i] -= self.decays[i]
            if self.lives[i] <= 0:
                self.count -= 1
                self.positions[i] = self.positions[self.count]
                self.velocities[i] = self.velocities[self.count]
                self.colors[i] = self.colors[self.count]
                self.lives[i] = self.lives[self.count]
                self.decays[i] = self.decays[self.count]
                self.sizes[i] = self.sizes[self.count]
            else:
                i += 1

    def draw(self, surface):
        for i in range(self.count):
            alpha = max(0, min(255, self.lives[i]))
            color = self.colors[i]
            sz = self.sizes[i]
            x, y = int(self.positions[i].x), int(self.positions[i].y)
            if sz <= 2:
                # Small particles: just a colored rect
                s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                pygame.draw.rect(s, (*color, alpha), (0, 0, sz * 2, sz * 2))
                surface.blit(s, (x - sz, y - sz))
            else:
                # Larger particles: soft circle with glow
                total = sz * 3
                s = pygame.Surface((total * 2, total * 2), pygame.SRCALPHA)
                # outer glow
                pygame.draw.circle(s, (*color, alpha // 4), (total, total), total)
                # core
                pygame.draw.circle(s, (*color, alpha), (total, total), sz)
                surface.blit(s, (x - total, y - total))


# ─── FLOATING TEXT ────────────────────────────────────────────

class FloatingTextPool:
    def __init__(self, max_texts=50):
        self.texts = []
        self.max = max_texts
        self._font_cache = {}

    def _get_font(self, size):
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont("Arial", size, bold=True)
        return self._font_cache[size]

    def spawn(self, pos, text, color, size=22):
        if len(self.texts) >= self.max:
            self.texts.pop(0)
        self.texts.append({
            'pos': vec(pos),
            'text': text,
            'color': color,
            'life': 50,
            'size': size,
            'scale': 1.3,  # starts big, shrinks to 1.0
        })

    def update(self):
        for t in self.texts:
            t['pos'].y -= 1.0
            t['life'] -= 1
            t['scale'] = max(1.0, t['scale'] - 0.02)
        self.texts = [t for t in self.texts if t['life'] > 0]

    def draw(self, surface):
        for t in self.texts:
            alpha = min(255, t['life'] * 6)
            size = max(8, int(t['size'] * t['scale']))
            font = self._get_font(size)
            txt = font.render(t['text'], True, t['color'])
            txt.set_alpha(alpha)
            surface.blit(txt, (int(t['pos'].x), int(t['pos'].y)))


# ─── BACKGROUND RENDERER ─────────────────────────────────────

class Background:
    """Modern gradient background with subtle animated elements."""

    def __init__(self):
        # Pre-render gradient
        self.gradient = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * ratio)
            g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * ratio)
            b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * ratio)
            pygame.draw.line(self.gradient, (r, g, b), (0, y), (WIDTH, y))

        # Floating ambient particles
        self.ambient = []
        for _ in range(40):
            self.ambient.append({
                'x': random.uniform(0, WIDTH),
                'y': random.uniform(0, HEIGHT),
                'speed': random.uniform(0.1, 0.4),
                'size': random.uniform(0.5, 2.0),
                'alpha': random.randint(15, 40),
                'phase': random.uniform(0, math.pi * 2),
            })

    def draw(self, surface, player_pos, frame):
        surface.blit(self.gradient, (0, 0))

        # Subtle grid (parallax)
        grid_size = 60
        ox = (player_pos.x * 0.1) % grid_size
        oy = (player_pos.y * 0.1) % grid_size
        for x in range(0, WIDTH + grid_size, grid_size):
            pygame.draw.line(surface, GRID, (x - ox, 0), (x - ox, HEIGHT))
        for y in range(0, HEIGHT + grid_size, grid_size):
            pygame.draw.line(surface, GRID, (0, y - oy), (WIDTH, y - oy))

        # Ambient floating particles
        t = frame * 0.02
        for p in self.ambient:
            p['y'] -= p['speed']
            if p['y'] < -5:
                p['y'] = HEIGHT + 5
                p['x'] = random.uniform(0, WIDTH)
            # gentle sway
            px = p['x'] + math.sin(t + p['phase']) * 8
            sz = int(p['size'])
            if sz >= 1:
                s = pygame.Surface((sz * 2 + 2, sz * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (100, 120, 200, p['alpha']),
                                 (sz + 1, sz + 1), sz + 1)
                surface.blit(s, (int(px) - sz - 1, int(p['y']) - sz - 1))


# ─── SCREEN EFFECTS ──────────────────────────────────────────

class ScreenFX:
    def __init__(self):
        self.shake_intensity = 0
        self.flash_alpha = 0
        self.flash_color = WHITE
        self.hitstop_frames = 0
        self.slowmo_timer = 0
        self.slowmo_scale = 1.0
        self.vignette = self._make_vignette()
        self.shockwave_rings = []

    def _make_vignette(self):
        import numpy as np
        # Build at quarter res for speed, scale up for smoothness
        sw, sh = WIDTH // 4, HEIGHT // 4
        surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx, cy = sw / 2, sh / 2
        max_r = math.sqrt(cx * cx + cy * cy)
        xs, ys = np.meshgrid(np.arange(sw), np.arange(sh))
        dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / max_r
        alpha = np.where(dist > 0.4,
                         np.clip(((dist - 0.4) / 0.6) ** 2.0 * 140, 0, 140), 0
                         ).astype(np.uint8)
        # pixels_alpha gives (w, h) shaped array — need to transpose
        pa = pygame.surfarray.pixels_alpha(surf)
        pa[:] = alpha.T
        del pa
        return pygame.transform.smoothscale(surf, (WIDTH, HEIGHT))

    def shake(self, intensity):
        self.shake_intensity = max(self.shake_intensity, intensity)

    def flash(self, color=WHITE, alpha=60):
        self.flash_color = color
        self.flash_alpha = alpha

    def hitstop(self, frames=3):
        self.hitstop_frames = max(self.hitstop_frames, frames)

    def slowmo(self, duration=30, scale=0.3):
        self.slowmo_timer = duration
        self.slowmo_scale = scale

    def add_shockwave(self, pos, max_radius, color):
        self.shockwave_rings.append([vec(pos), 0, max_radius, color])

    def update(self):
        if self.shake_intensity > 0:
            self.shake_intensity *= 0.85
            if self.shake_intensity < 0.5:
                self.shake_intensity = 0
        if self.flash_alpha > 0:
            self.flash_alpha -= 6
        if self.hitstop_frames > 0:
            self.hitstop_frames -= 1
        if self.slowmo_timer > 0:
            self.slowmo_timer -= 1

        new_rings = []
        for ring in self.shockwave_rings:
            ring[1] += 5
            if ring[1] < ring[2]:
                new_rings.append(ring)
        self.shockwave_rings = new_rings

    def get_time_scale(self):
        if self.hitstop_frames > 0:
            return 0.0
        if self.slowmo_timer > 0:
            return self.slowmo_scale
        return 1.0

    def get_shake_offset(self):
        if self.shake_intensity < 0.5:
            return (0, 0)
        t = pygame.time.get_ticks() * 0.001
        x = math.sin(t * 37) * self.shake_intensity
        y = math.cos(t * 29) * self.shake_intensity * 0.8
        return (x, y)

    def draw(self, surface):
        # Shockwave rings
        for ring in self.shockwave_rings:
            pos, radius, max_r, color = ring
            alpha = int(180 * (1 - radius / max_r))
            if alpha > 0 and radius > 0:
                thickness = max(2, int(4 * (1 - radius / max_r)))
                sz = int(radius + 4)
                s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, max(0, alpha)),
                                 (sz, sz), int(radius), thickness)
                surface.blit(s, (int(pos.x) - sz, int(pos.y) - sz))

        # Screen flash
        if self.flash_alpha > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((*self.flash_color[:3], max(0, int(self.flash_alpha))))
            surface.blit(flash, (0, 0))

        # Vignette
        surface.blit(self.vignette, (0, 0))
