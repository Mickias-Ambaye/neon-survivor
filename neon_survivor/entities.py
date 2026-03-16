import pygame
import math
import random
from settings import *

vec = pygame.math.Vector2


# ─── PROJECTILE ───────────────────────────────────────────────

class Projectile:
    __slots__ = ['pos', 'vel', 'damage', 'radius', 'color', 'pierce', 'life', 'active']

    def __init__(self):
        self.active = False

    def spawn(self, pos, vel, damage, radius, color, pierce=0):
        self.pos = vec(pos)
        self.vel = vec(vel)
        self.damage = damage
        self.radius = radius
        self.color = color
        self.pierce = pierce
        self.life = 180  # 3 seconds max
        self.active = True

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= 1
        if self.life <= 0 or self.pos.x < -50 or self.pos.x > WIDTH + 50 or \
           self.pos.y < -50 or self.pos.y > HEIGHT + 50:
            self.active = False

    def draw(self, surface):
        # glow
        glow_surf = pygame.Surface((self.radius * 6, self.radius * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 40), (self.radius * 3, self.radius * 3), self.radius * 3)
        surface.blit(glow_surf, (int(self.pos.x) - self.radius * 3, int(self.pos.y) - self.radius * 3))
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(self.pos.x), int(self.pos.y)), max(1, self.radius - 2))


# ─── ENEMY PROJECTILE ─────────────────────────────────────────

class EnemyProjectile:
    """Projectiles fired BY enemies (boss rings, sniper shots). Damages the PLAYER."""
    __slots__ = ['pos', 'vel', 'damage', 'radius', 'color', 'life', 'active']

    def __init__(self):
        self.active = False

    def spawn(self, pos, vel, damage, radius, color):
        self.pos = vec(pos)
        self.vel = vec(vel)
        self.damage = damage
        self.radius = radius
        self.color = color
        self.life = 300  # 5 seconds
        self.active = True

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= 1
        if self.life <= 0 or self.pos.x < -80 or self.pos.x > WIDTH + 80 or \
           self.pos.y < -80 or self.pos.y > HEIGHT + 80:
            self.active = False

    def draw(self, surface):
        x, y = int(self.pos.x), int(self.pos.y)
        # Outer glow
        glow = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 50), (self.radius * 2, self.radius * 2), self.radius * 2)
        surface.blit(glow, (x - self.radius * 2, y - self.radius * 2))
        # Core
        pygame.draw.circle(surface, self.color, (x, y), self.radius)


# ─── XP GEM ───────────────────────────────────────────────────

class XPGem:
    __slots__ = ['pos', 'vel', 'value', 'color', 'active', 'life', 'attracted']

    def __init__(self):
        self.active = False

    def spawn(self, pos, value=1):
        self.pos = vec(pos) + vec(random.uniform(-15, 15), random.uniform(-15, 15))
        self.vel = vec(random.uniform(-2, 2), random.uniform(-2, 2))
        self.value = value
        self.color = CYAN if value <= 1 else GREEN if value <= 3 else YELLOW
        self.active = True
        self.life = 600  # 10s
        self.attracted = False

    def update(self, player_pos, pickup_radius, dt):
        self.life -= 1
        if self.life <= 0:
            self.active = False
            return

        dist = self.pos.distance_to(player_pos)

        # attraction zone
        if dist < pickup_radius:
            self.attracted = True

        if self.attracted:
            direction = (player_pos - self.pos)
            if direction.length() > 0:
                direction = direction.normalize()
            speed = max(6, 14 - dist * 0.05)  # accelerate as it gets closer
            self.vel = direction * speed
        else:
            self.vel *= 0.92  # friction on idle gems

        self.pos += self.vel * dt

        # collected
        if dist < 12:
            self.active = False
            return self.value
        return 0

    def draw(self, surface):
        # diamond shape
        x, y = int(self.pos.x), int(self.pos.y)
        sz = 4 + (1 if self.value > 1 else 0)
        points = [(x, y - sz), (x + sz, y), (x, y + sz), (x - sz, y)]
        alpha = 255 if self.life > 60 else int(self.life * 4)
        s = pygame.Surface((sz * 2 + 4, sz * 2 + 4), pygame.SRCALPHA)
        local_points = [(sz + 2, 2), (sz * 2 + 2, sz + 2), (sz + 2, sz * 2 + 2), (2, sz + 2)]
        pygame.draw.polygon(s, (*self.color, alpha), local_points)
        pygame.draw.polygon(s, (*WHITE, alpha // 2), local_points, 1)
        surface.blit(s, (x - sz - 2, y - sz - 2))


# ─── ORBIT BLADE ──────────────────────────────────────────────

class OrbitBlade:
    def __init__(self, index, total, radius, speed, damage, color):
        self.angle = (2 * math.pi / total) * index
        self.orbit_radius = radius
        self.speed = speed
        self.damage = damage
        self.color = color
        self.hit_timer = {}  # enemy_id: cooldown

    def update(self, dt):
        self.angle += self.speed * 0.02 * dt
        # decay hit timers
        for eid in list(self.hit_timer):
            self.hit_timer[eid] -= 1
            if self.hit_timer[eid] <= 0:
                del self.hit_timer[eid]

    def get_pos(self, player_pos):
        return vec(
            player_pos.x + math.cos(self.angle) * self.orbit_radius,
            player_pos.y + math.sin(self.angle) * self.orbit_radius
        )

    def can_hit(self, enemy_id):
        return enemy_id not in self.hit_timer

    def register_hit(self, enemy_id):
        self.hit_timer[enemy_id] = 30

    def draw(self, surface, player_pos):
        pos = self.get_pos(player_pos)
        x, y = int(pos.x), int(pos.y)
        # blade shape — elongated diamond
        sz = 8
        trail_angle = self.angle + math.pi / 2
        points = [
            (x + math.cos(self.angle) * sz * 2, y + math.sin(self.angle) * sz * 2),
            (x + math.cos(trail_angle) * sz * 0.5, y + math.sin(trail_angle) * sz * 0.5),
            (x - math.cos(self.angle) * sz * 0.8, y - math.sin(self.angle) * sz * 0.8),
            (x - math.cos(trail_angle) * sz * 0.5, y - math.sin(trail_angle) * sz * 0.5),
        ]
        pygame.draw.polygon(surface, self.color, points)
        pygame.draw.polygon(surface, WHITE, points, 1)


# ─── DRONE ────────────────────────────────────────────────────

class Drone:
    """Autonomous turret that orbits the player and shoots nearest enemy."""
    def __init__(self, index, total, orbit_radius, color):
        self.angle = (2 * math.pi / total) * index
        self.orbit_radius = orbit_radius
        self.color = color
        self.fire_timer = 0

    def update(self, dt):
        self.angle += 0.015 * dt
        if self.fire_timer > 0:
            self.fire_timer -= 1

    def get_pos(self, player_pos):
        return vec(
            player_pos.x + math.cos(self.angle) * self.orbit_radius,
            player_pos.y + math.sin(self.angle) * self.orbit_radius
        )

    def draw(self, surface, player_pos):
        pos = self.get_pos(player_pos)
        x, y = int(pos.x), int(pos.y)
        # Small diamond turret
        sz = 5
        pts = [(x, y - sz), (x + sz, y), (x, y + sz), (x - sz, y)]
        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, WHITE, pts, 1)
        # Connection line to player
        pygame.draw.line(surface, (*self.color[:3], 40) if len(self.color) == 4 else (*self.color, ),
                        (int(player_pos.x), int(player_pos.y)), (x, y), 1)


# ─── LASER BEAM ──────────────────────────────────────────────

class LaserBeam:
    """Sustained beam that locks onto nearest enemy."""
    def __init__(self, color, width, beam_range):
        self.color = color
        self.width = width
        self.beam_range = beam_range
        self.active = False
        self.target_pos = None
        self.duration = 0

    def fire(self, target_pos, duration):
        self.target_pos = vec(target_pos)
        self.active = True
        self.duration = duration

    def update(self):
        if self.active:
            self.duration -= 1
            if self.duration <= 0:
                self.active = False

    def draw(self, surface, player_pos):
        if not self.active or not self.target_pos:
            return
        start = (int(player_pos.x), int(player_pos.y))
        end = (int(self.target_pos.x), int(self.target_pos.y))
        # Outer glow
        pygame.draw.line(surface, (*self.color[:3], 40) if len(self.color) > 3 else self.color,
                        start, end, self.width + 6)
        # Mid
        pygame.draw.line(surface, self.color, start, end, self.width + 2)
        # Core (white)
        pygame.draw.line(surface, WHITE, start, end, max(1, self.width - 2))


# ─── PLAYER ───────────────────────────────────────────────────

class Player:
    def __init__(self):
        self.pos = vec(WIDTH // 2, HEIGHT // 2)
        self.vel = vec(0, 0)
        self.radius = PLAYER_RADIUS
        self.angle = 0
        self.trail = []

        # HP
        self.max_hp = PLAYER_HP
        self.hp = self.max_hp

        # Dash
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_dir = vec(0, 0)
        self.is_dashing = False

        # Invulnerability
        self.invuln_timer = 0

        # Weapon system
        self.weapons = {}  # name: {level, timer, ...}
        self.orbit_blades = []
        self.drones = []
        self.laser = None
        self.shockwave_timer = 0
        self.evolved = set()  # evolved weapon names

        # Stats (modified by passives)
        self.speed_mult = 1.0
        self.fire_rate_mult = 1.0
        self.pickup_radius = PICKUP_RADIUS
        self.dash_cd_mult = 1.0
        self.heal_on_kill = 0.0

        # Passives
        self.passives = {}  # name: level

        # Give starting weapon
        self.add_weapon("pulse_shot")

    def add_weapon(self, name):
        if name not in self.weapons:
            self.weapons[name] = {"level": 1, "timer": 0}
            if name == "orbit_blade":
                self._rebuild_orbit_blades()
            elif name == "drone":
                self._rebuild_drones()
            elif name == "laser_beam":
                stats = self.get_weapon_stats(name)
                self.laser = LaserBeam(WEAPONS[name]["color"],
                                       WEAPONS[name]["beam_width"],
                                       WEAPONS[name]["beam_range"])

    def upgrade_weapon(self, name):
        if name in self.weapons:
            w = self.weapons[name]
            if w["level"] < 5:
                w["level"] += 1
                if name == "orbit_blade":
                    self._rebuild_orbit_blades()
                elif name == "drone":
                    self._rebuild_drones()
                elif name == "laser_beam" and self.laser:
                    stats = self.get_weapon_stats(name)
                    self.laser.width = stats.get("beam_width", 6)
                    self.laser.beam_range = stats.get("beam_range", 250)

    def check_evolution(self, name):
        """Check if a weapon can evolve. Returns evolution name or None."""
        if name not in self.weapons or name in self.evolved:
            return None
        w = self.weapons[name]
        wdata = WEAPONS.get(name)
        if not wdata or w["level"] < 5:
            return None
        required_passive = wdata.get("evo_requires")
        if required_passive and self.passives.get(required_passive, 0) >= 1:
            return wdata.get("evolution")
        return None

    def evolve_weapon(self, name):
        """Evolve a maxed weapon. Returns evolution name."""
        evo = self.check_evolution(name)
        if evo:
            self.evolved.add(name)
            # Rebuild sub-systems with evolved stats
            if name == "orbit_blade":
                self._rebuild_orbit_blades()
            elif name == "drone":
                self._rebuild_drones()
        return evo

    def add_passive(self, name):
        if name not in self.passives:
            self.passives[name] = 1
        else:
            self.passives[name] = min(self.passives[name] + 1, PASSIVES[name]["max_level"])
        self._recalc_passives()

    def _recalc_passives(self):
        self.speed_mult = 1.0 + self.passives.get("phase_shift", 0) * 0.12
        self.fire_rate_mult = 1.0 - self.passives.get("overclock", 0) * 0.15
        self.pickup_radius = PICKUP_RADIUS + self.passives.get("magnetic_field", 0) * 40
        self.dash_cd_mult = 1.0 - self.passives.get("coolant", 0) * 0.2
        self.heal_on_kill = self.passives.get("data_leech", 0) * 0.03
        extra_hp = self.passives.get("hardened_core", 0)
        self.max_hp = PLAYER_HP + extra_hp
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def _rebuild_orbit_blades(self):
        if "orbit_blade" not in self.weapons:
            self.orbit_blades = []
            return
        w = self.weapons["orbit_blade"]
        wdata = WEAPONS["orbit_blade"]
        level = w["level"]
        count = wdata["blade_count"]
        radius = wdata["orbit_radius"]
        speed = wdata["orbit_speed"]
        damage = wdata["damage"]
        # apply upgrades
        for i in range(min(level - 1, len(wdata["upgrades"]))):
            up = wdata["upgrades"][i]
            count += up.get("blade_count", 0)
            radius += up.get("orbit_radius", 0)
            speed += up.get("orbit_speed", 0)
            damage += up.get("damage", 0)
        self.orbit_blades = [
            OrbitBlade(i, count, radius, speed, damage, wdata["color"])
            for i in range(count)
        ]

    def _rebuild_drones(self):
        if "drone" not in self.weapons:
            self.drones = []
            return
        w = self.weapons["drone"]
        wdata = WEAPONS["drone"]
        count = wdata["drone_count"]
        orbit = wdata["drone_orbit"]
        for i in range(min(w["level"] - 1, len(wdata["upgrades"]))):
            up = wdata["upgrades"][i]
            count += up.get("drone_count", 0)
            orbit += up.get("drone_orbit", 0)
        self.drones = [
            Drone(i, count, orbit, wdata["color"])
            for i in range(count)
        ]

    def get_weapon_stats(self, name):
        """Get current stats for a weapon accounting for level upgrades."""
        if name not in self.weapons:
            return None
        w = self.weapons[name]
        wdata = dict(WEAPONS[name])  # copy base stats
        for i in range(min(w["level"] - 1, len(wdata["upgrades"]))):
            up = wdata["upgrades"][i]
            for k, v in up.items():
                if k == "desc":
                    continue
                if k in wdata:
                    wdata[k] += v
        return wdata

    def move(self, keys, dt):
        if self.is_dashing:
            self.dash_timer -= 1
            self.pos += self.dash_dir * DASH_SPEED * dt
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.vel = self.dash_dir * 3  # exit momentum
        else:
            accel = vec(0, 0)
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:   accel.x = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:  accel.x = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:     accel.y = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:    accel.y = 1

            if accel.length() > 0:
                accel = accel.normalize() * PLAYER_SPEED * self.speed_mult

            self.vel += accel
            self.vel *= PLAYER_FRICTION
            self.pos += self.vel * dt

        # Boundaries
        self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(HEIGHT - self.radius, self.pos.y))

        # Trail
        self.trail.append(vec(self.pos))
        if len(self.trail) > 12:
            self.trail.pop(0)
        self.angle += self.vel.length() * 2

        # Timers
        if self.invuln_timer > 0:
            self.invuln_timer -= 1
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        # Update orbit blades
        for blade in self.orbit_blades:
            blade.update(dt)

        # Update drones
        for drone in self.drones:
            drone.update(dt)

        # Update laser
        if self.laser:
            self.laser.update()

        # Weapon timers
        for name, w in self.weapons.items():
            if w["timer"] > 0:
                w["timer"] -= 1
        if self.shockwave_timer > 0:
            self.shockwave_timer -= 1

    def try_dash(self):
        if self.dash_cooldown > 0 or self.is_dashing:
            return False
        direction = vec(self.vel)
        if direction.length() < 0.3:
            direction = vec(1, 0)  # default right
        else:
            direction = direction.normalize()
        self.dash_dir = direction
        self.is_dashing = True
        self.dash_timer = DASH_DURATION
        self.dash_cooldown = int(DASH_COOLDOWN * self.dash_cd_mult)
        self.invuln_timer = max(self.invuln_timer, DASH_DURATION + 3)
        return True

    def take_damage(self, amount=1):
        if self.invuln_timer > 0:
            return False
        self.hp -= amount
        self.invuln_timer = PLAYER_INVULN_TIME
        return True

    def heal(self, amount=1):
        self.hp = min(self.hp + amount, self.max_hp)

    def try_heal_on_kill(self):
        if self.heal_on_kill > 0 and random.random() < self.heal_on_kill:
            self.heal(1)

    def get_fire_targets(self, enemies):
        """Auto-aim: returns list of (weapon_name, target_enemy) pairs ready to fire."""
        shots = []
        for name, w in self.weapons.items():
            if name in ("orbit_blade", "shockwave", "lightning_arc", "drone", "laser_beam"):
                continue  # these don't use projectiles
            if w["timer"] > 0:
                continue
            stats = self.get_weapon_stats(name)
            if not stats:
                continue
            fire_rate = max(5, int(stats.get("fire_rate", 30) * self.fire_rate_mult))
            # find nearest enemy
            nearest = None
            nearest_dist = float('inf')
            for e in enemies:
                d = self.pos.distance_to(e.pos)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest = e
            if nearest and nearest_dist < 500:
                w["timer"] = fire_rate
                count = stats.get("count", 1)
                for i in range(count):
                    shots.append((name, nearest, i, count))
        return shots

    def try_shockwave(self, enemies):
        """Returns list of enemies hit by shockwave if ready."""
        if "shockwave" not in self.weapons:
            return None, 0
        if self.shockwave_timer > 0:
            return None, 0
        stats = self.get_weapon_stats("shockwave")
        self.shockwave_timer = int(stats["cooldown"] * self.fire_rate_mult)
        hit = []
        for e in enemies:
            if self.pos.distance_to(e.pos) < stats["radius"]:
                hit.append(e)
        return hit, stats["damage"]

    def try_lightning(self, enemies):
        """Chain lightning to nearest enemies."""
        if "lightning_arc" not in self.weapons:
            return []
        w = self.weapons["lightning_arc"]
        if w["timer"] > 0:
            return []
        stats = self.get_weapon_stats("lightning_arc")
        fire_rate = max(5, int(stats["fire_rate"] * self.fire_rate_mult))
        w["timer"] = fire_rate

        chains = []
        if not enemies:
            return chains
        # start from nearest enemy
        remaining = list(enemies)
        nearest = min(remaining, key=lambda e: self.pos.distance_to(e.pos))
        if self.pos.distance_to(nearest.pos) > 300:
            return chains

        current_pos = vec(self.pos)
        for _ in range(stats["chain_count"]):
            best = None
            best_dist = stats["chain_range"]
            for e in remaining:
                d = current_pos.distance_to(e.pos)
                if d < best_dist:
                    best_dist = d
                    best = e
            if best is None:
                break
            chains.append((vec(current_pos), vec(best.pos), best, stats["damage"]))
            current_pos = vec(best.pos)
            remaining.remove(best)
        return chains

    def get_drone_shots(self, enemies):
        """Returns list of (drone, target_enemy) pairs for drones ready to fire."""
        shots = []
        if "drone" not in self.weapons:
            return shots
        stats = self.get_weapon_stats("drone")
        if not stats:
            return shots
        fire_rate = max(5, int(stats.get("fire_rate", 40) * self.fire_rate_mult))
        for drone in self.drones:
            if drone.fire_timer > 0:
                continue
            # Find nearest enemy to drone
            drone_pos = drone.get_pos(self.pos)
            nearest = None
            nearest_dist = 350  # drone range
            for e in enemies:
                d = drone_pos.distance_to(e.pos)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest = e
            if nearest:
                drone.fire_timer = fire_rate
                shots.append((drone, nearest, stats["damage"], stats["speed"], stats["radius"]))
        return shots

    def try_laser(self, enemies):
        """Fire laser at nearest enemy. Returns (start, end, damage, enemies_hit) or None."""
        if "laser_beam" not in self.weapons or not self.laser:
            return None
        w = self.weapons["laser_beam"]
        if w["timer"] > 0:
            return None

        stats = self.get_weapon_stats("laser_beam")
        fire_rate = max(10, int(stats.get("fire_rate", 90) * self.fire_rate_mult))

        if not enemies:
            return None
        nearest = min(enemies, key=lambda e: self.pos.distance_to(e.pos))
        if self.pos.distance_to(nearest.pos) > stats["beam_range"]:
            return None

        w["timer"] = fire_rate
        beam_dur = stats.get("beam_duration", 20)
        self.laser.fire(nearest.pos, beam_dur)

        # Hit all enemies in the beam path
        direction = (nearest.pos - self.pos)
        if direction.length() == 0:
            return None
        direction = direction.normalize()
        hit = []
        for e in enemies:
            # Point-to-line distance
            to_enemy = e.pos - self.pos
            proj = to_enemy.dot(direction)
            if proj < 0 or proj > stats["beam_range"]:
                continue
            closest = self.pos + direction * proj
            dist = e.pos.distance_to(closest)
            if dist < e.radius + stats["beam_width"]:
                hit.append(e)

        return (vec(self.pos), vec(nearest.pos), stats["damage"], hit)

    @property
    def is_invuln(self):
        return self.invuln_timer > 0

    def draw(self, surface):
        # Trail
        for i, p in enumerate(self.trail):
            ratio = i / max(1, len(self.trail))
            alpha = int(120 * ratio)
            size = int(self.radius * ratio * 0.8)
            if size < 1:
                continue
            color = CLR_DASH if self.is_dashing else CLR_PLAYER
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha), (size, size), size)
            surface.blit(s, (int(p.x) - size, int(p.y) - size))

        # Invuln flash
        if self.is_invuln and (self.invuln_timer // 3) % 2 == 0:
            return  # blink effect

        # Diamond body
        points = []
        for i in range(4):
            a = math.radians(self.angle + i * 90)
            points.append((
                self.pos.x + math.cos(a) * self.radius * 1.5,
                self.pos.y + math.sin(a) * self.radius * 1.5
            ))
        color = CLR_DASH if self.is_dashing else CLR_PLAYER
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, WHITE, points, 2)

        # Orbit blades
        for blade in self.orbit_blades:
            blade.draw(surface, self.pos)

        # Drones
        for drone in self.drones:
            drone.draw(surface, self.pos)

        # Laser beam
        if self.laser and self.laser.active:
            self.laser.draw(surface, self.pos)

        # Dash cooldown indicator
        if self.dash_cooldown > 0:
            ratio = self.dash_cooldown / DASH_COOLDOWN
            arc_rect = pygame.Rect(
                int(self.pos.x) - 20, int(self.pos.y) - 20, 40, 40
            )
            pygame.draw.arc(surface, (*CYAN, 80), arc_rect,
                          0, math.pi * 2 * (1 - ratio), 2)


# ─── ENEMIES ──────────────────────────────────────────────────

class Enemy:
    _next_id = 0

    def __init__(self, etype, wave_num=1):
        Enemy._next_id += 1
        self.id = Enemy._next_id
        self.type = etype
        self.active = True

        stats = ENEMY_STATS.get(etype, ENEMY_STATS["stalker"])
        scale = 1 + wave_num * 0.04

        self.hp = int(stats["hp"] * scale)
        self.max_hp = self.hp
        self.base_speed = stats["speed"] * min(scale, 2.5)
        self.speed = self.base_speed
        self.radius = stats["radius"]
        self.xp_value = stats["xp"]
        self.color = ENEMY_COLORS.get(etype, RED)
        self.shape = stats.get("shape", "circle")

        self.pos = self._spawn_pos()
        self.vel = vec(0, 0)
        self.flash_timer = 0

        # Type-specific state
        self.dash_timer = 0
        self.dash_cooldown = stats.get("dash_interval", 0)
        self.is_dashing = False
        self.orbit_angle = random.uniform(0, math.pi * 2)
        self.orbit_dist = stats.get("orbit_dist", 120)
        self.spawn_timer = stats.get("spawn_interval", 0)
        self.shield_active = etype == "shielder"
        self.teleport_timer = random.randint(60, 120) if etype == "glitcher" else 0

    def _spawn_pos(self):
        side = random.randint(0, 3)
        margin = 60
        if side == 0: return vec(random.randint(0, WIDTH), -margin)
        if side == 1: return vec(random.randint(0, WIDTH), HEIGHT + margin)
        if side == 2: return vec(-margin, random.randint(0, HEIGHT))
        return vec(WIDTH + margin, random.randint(0, HEIGHT))

    def update(self, player_pos, dt, time_slow=False):
        self.flash_timer = max(0, self.flash_timer - 1)
        speed_mult = 0.3 if time_slow else 1.0

        if self.type == "stalker":
            self._move_toward(player_pos, speed_mult, dt)

        elif self.type == "dasher":
            if self.dash_cooldown > 0:
                self.dash_cooldown -= 1
                self.vel *= 0.9
                self.pos += self.vel * dt
            else:
                if not self.is_dashing:
                    direction = (player_pos - self.pos)
                    if direction.length() > 0:
                        self.vel = direction.normalize() * ENEMY_STATS["dasher"]["dash_speed"] * speed_mult
                    self.is_dashing = True
                    self.dash_timer = ENEMY_STATS["dasher"]["dash_duration"]
                self.pos += self.vel * dt
                self.dash_timer -= 1
                if self.dash_timer <= 0:
                    self.is_dashing = False
                    self.dash_cooldown = ENEMY_STATS["dasher"]["dash_interval"]

        elif self.type == "splitter":
            self._move_toward(player_pos, speed_mult * 0.7, dt)

        elif self.type == "orbiter":
            self.orbit_angle += 0.02 * speed_mult * dt
            self.orbit_dist -= ENEMY_STATS["orbiter"]["close_rate"] * dt
            self.orbit_dist = max(20, self.orbit_dist)
            target = player_pos + vec(
                math.cos(self.orbit_angle) * self.orbit_dist,
                math.sin(self.orbit_angle) * self.orbit_dist
            )
            self._move_toward(target, speed_mult, dt, direct=True)

        elif self.type == "shielder":
            self._move_toward(player_pos, speed_mult * 0.6, dt)

        elif self.type == "carrier":
            self._move_toward(player_pos, speed_mult * 0.5, dt)
            self.spawn_timer -= 1

        elif self.type == "glitcher":
            self._move_toward(player_pos, speed_mult * 1.3, dt)
            self.teleport_timer -= 1
            if self.teleport_timer <= 0:
                offset = vec(random.uniform(-100, 100), random.uniform(-100, 100))
                self.pos = player_pos + offset
                self.pos.x = max(0, min(WIDTH, self.pos.x))
                self.pos.y = max(0, min(HEIGHT, self.pos.y))
                self.teleport_timer = random.randint(60, 120)
        else:
            self._move_toward(player_pos, speed_mult, dt)

    def _move_toward(self, target, speed_mult, dt, direct=False):
        direction = target - self.pos
        if direction.length() > 1:
            direction = direction.normalize()
            spd = self.base_speed * speed_mult
            if direct:
                self.vel = direction * spd
            else:
                self.vel += direction * spd * 0.1
                if self.vel.length() > spd:
                    self.vel = self.vel.normalize() * spd
        self.pos += self.vel * dt

    def take_damage(self, amount):
        self.hp -= amount
        self.flash_timer = 4
        if self.hp <= 0:
            self.active = False
            return True
        return False

    def should_spawn(self):
        """For carrier: returns True when it should spawn a minion."""
        if self.type == "carrier" and self.spawn_timer <= 0:
            self.spawn_timer = ENEMY_STATS["carrier"]["spawn_interval"]
            return True
        return False

    def draw(self, surface):
        x, y = int(self.pos.x), int(self.pos.y)
        r = self.radius
        color = WHITE if self.flash_timer > 0 else self.color

        if self.shape == "circle":
            pygame.draw.circle(surface, color, (x, y), r)
            pygame.draw.circle(surface, WHITE, (x, y), r, 1)

        elif self.shape == "triangle":
            pts = []
            base_angle = math.atan2(self.vel.y, self.vel.x) if self.vel.length() > 0.1 else 0
            for i in range(3):
                a = base_angle + i * (2 * math.pi / 3)
                pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, WHITE, pts, 1)

        elif self.shape == "square":
            pygame.draw.rect(surface, color, (x - r, y - r, r * 2, r * 2))
            pygame.draw.rect(surface, WHITE, (x - r, y - r, r * 2, r * 2), 1)

        elif self.shape == "diamond":
            pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, WHITE, pts, 1)

        elif self.shape == "hexagon":
            pts = [(x + math.cos(math.pi / 3 * i) * r,
                    y + math.sin(math.pi / 3 * i) * r) for i in range(6)]
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, WHITE, pts, 1)
            # shield aura
            if self.shield_active:
                shield_r = ENEMY_STATS["shielder"]["shield_radius"]
                s = pygame.Surface((shield_r * 2, shield_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*WHITE, 25), (shield_r, shield_r), shield_r, 2)
                surface.blit(s, (x - shield_r, y - shield_r))

        elif self.shape == "octagon":
            pts = [(x + math.cos(math.pi / 4 * i) * r,
                    y + math.sin(math.pi / 4 * i) * r) for i in range(8)]
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, WHITE, pts, 1)

        # HP bar for enemies with > 3 HP
        if self.max_hp > 3:
            bar_w = r * 2
            bar_h = 3
            hp_ratio = self.hp / self.max_hp
            pygame.draw.rect(surface, (50, 50, 50), (x - r, y - r - 8, bar_w, bar_h))
            pygame.draw.rect(surface, color, (x - r, y - r - 8, int(bar_w * hp_ratio), bar_h))


# ─── BOSS ─────────────────────────────────────────────────────

class Boss(Enemy):
    def __init__(self, boss_type, wave_num):
        self.boss_type = boss_type
        stats = BOSS_STATS[boss_type]

        # Skip Enemy.__init__, set up manually
        Enemy._next_id += 1
        self.id = Enemy._next_id
        self.type = "boss"
        self.active = True
        self.shape = "hexagon"

        scale = 1 + wave_num * 0.03
        self.hp = int(stats["hp"] * scale)
        self.max_hp = self.hp
        self.base_speed = stats["speed"]
        self.speed = self.base_speed
        self.radius = stats["radius"]
        self.xp_value = stats["xp"]
        self.color = CLR_BOSS

        self.pos = vec(WIDTH // 2, -80)
        self.vel = vec(0, 0)
        self.flash_timer = 0
        self.phase = 1
        self.attack_timer = 0
        self.shield_active = False
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.is_dashing = False
        self.orbit_angle = 0
        self.orbit_dist = 0
        self.spawn_timer = 0
        self.teleport_timer = 0
        self.bullet_ring_timer = 180

    def update(self, player_pos, dt, time_slow=False):
        self.flash_timer = max(0, self.flash_timer - 1)
        speed_mult = 0.3 if time_slow else 1.0

        # Phase transitions
        hp_ratio = self.hp / self.max_hp
        if hp_ratio < 0.25:
            self.phase = 3
        elif hp_ratio < 0.5:
            self.phase = 2

        if self.phase == 1:
            # Slow approach + bullet rings
            self._move_toward(player_pos, speed_mult * 0.4, dt)
            self.bullet_ring_timer -= 1
        elif self.phase == 2:
            # Faster, more aggressive
            self._move_toward(player_pos, speed_mult * 0.8, dt)
            self.bullet_ring_timer -= 1
        elif self.phase == 3:
            # Charge attacks
            if not self.is_dashing and self.dash_cooldown <= 0:
                direction = (player_pos - self.pos)
                if direction.length() > 0:
                    self.vel = direction.normalize() * 6 * speed_mult
                self.is_dashing = True
                self.dash_timer = 30
            elif self.is_dashing:
                self.pos += self.vel * dt
                self.dash_timer -= 1
                if self.dash_timer <= 0:
                    self.is_dashing = False
                    self.dash_cooldown = 90
            else:
                self.dash_cooldown -= 1
                self.vel *= 0.95
                self.pos += self.vel * dt

        # Boundaries (loose)
        self.pos.x = max(-20, min(WIDTH + 20, self.pos.x))
        self.pos.y = max(-20, min(HEIGHT + 20, self.pos.y))

    def should_fire_ring(self):
        if self.bullet_ring_timer <= 0:
            self.bullet_ring_timer = 120 if self.phase == 1 else 60
            return True
        return False

    def draw(self, surface):
        x, y = int(self.pos.x), int(self.pos.y)
        r = self.radius
        color = WHITE if self.flash_timer > 0 else self.color

        # Outer glow
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 30), (r * 2, r * 2), r * 2)
        surface.blit(glow, (x - r * 2, y - r * 2))

        # Body — hexagon
        pts = [(x + math.cos(math.pi / 3 * i + self.flash_timer * 0.1) * r,
                y + math.sin(math.pi / 3 * i + self.flash_timer * 0.1) * r) for i in range(6)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, WHITE, pts, 3)

        # Inner detail
        inner_r = r * 0.5
        inner_pts = [(x + math.cos(math.pi / 3 * i + 0.5) * inner_r,
                      y + math.sin(math.pi / 3 * i + 0.5) * inner_r) for i in range(6)]
        pygame.draw.polygon(surface, (*self.color, 150) if len(color) == 3 else color, inner_pts, 2)

        # HP bar
        bar_w = r * 3
        bar_h = 6
        hp_ratio = self.hp / self.max_hp
        bx = x - bar_w // 2
        by = y - r - 15
        pygame.draw.rect(surface, (30, 30, 30), (bx, by, bar_w, bar_h))
        bar_color = GREEN if hp_ratio > 0.5 else YELLOW if hp_ratio > 0.25 else RED
        pygame.draw.rect(surface, bar_color, (bx, by, int(bar_w * hp_ratio), bar_h))
        pygame.draw.rect(surface, WHITE, (bx, by, bar_w, bar_h), 1)

        # Phase indicator
        phase_txt = f"PHASE {self.phase}"
        font = pygame.font.SysFont("Arial", 14, bold=True)
        txt = font.render(phase_txt, True, self.color)
        surface.blit(txt, (bx, by - 16))
