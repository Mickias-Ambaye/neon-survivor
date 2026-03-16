import pygame
import math
import random
import json
import os
from settings import *
from entities import Player, Enemy, Boss, Projectile, EnemyProjectile, XPGem
from effects import ParticlePool, FloatingTextPool, ScreenFX, Background
from audio import AudioManager

vec = pygame.math.Vector2

MAX_PROJECTILES = 200
MAX_ENEMY_PROJECTILES = 150
MAX_XP_GEMS = 300

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "save.json")


# ─── SPATIAL HASH ─────────────────────────────────────────────

class SpatialHash:
    def __init__(self, cell_size=64):
        self.cell_size = cell_size
        self.grid = {}

    def clear(self):
        self.grid.clear()

    def _key(self, pos):
        return (int(pos.x // self.cell_size), int(pos.y // self.cell_size))

    def insert(self, entity):
        key = self._key(entity.pos)
        self.grid.setdefault(key, []).append(entity)

    def query(self, pos, radius):
        results = []
        cx, cy = self._key(pos)
        r = int(radius // self.cell_size) + 1
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                results.extend(self.grid.get((cx + dx, cy + dy), []))
        return results


# ─── WAVE MANAGER ─────────────────────────────────────────────

class WaveManager:
    def __init__(self):
        self.wave = 0
        self.enemies_to_spawn = []
        self.spawn_timer = 0
        self.intermission = 0
        self.wave_active = False
        self.boss_active = False

    def start_next_wave(self):
        self.wave += 1
        self.wave_active = True
        self.enemies_to_spawn = self._generate_wave(self.wave)
        self.spawn_timer = 0

    def _generate_wave(self, wave):
        spawns = []
        base = 6 + wave * 2
        if wave % BOSS_EVERY == 0:
            self.boss_active = True
            spawns.append(("boss", 30))
            base = base // 2

        types = ["stalker"]
        if wave >= 3: types.append("dasher")
        if wave >= 5: types.append("splitter")
        if wave >= 7: types.append("orbiter")
        if wave >= 10: types.append("shielder")
        if wave >= 13: types.append("carrier")
        if wave >= 16: types.append("glitcher")

        for i in range(base):
            etype = random.choice(types)
            delay = max(5, int(15 + random.uniform(0, 25) - wave * 0.3))
            spawns.append((etype, delay * (i + 1)))
        return sorted(spawns, key=lambda s: s[1])

    def update(self, frame_count, alive_count):
        if self.intermission > 0:
            self.intermission -= 1
            if self.intermission <= 0:
                self.start_next_wave()
            return []

        if not self.wave_active:
            self.intermission = WAVE_INTERMISSION if self.wave > 0 else 10
            return []

        new_enemies = []
        self.spawn_timer += 1
        remaining = []
        for etype, delay in self.enemies_to_spawn:
            if self.spawn_timer >= delay:
                new_enemies.append(etype)
            else:
                remaining.append((etype, delay))
        self.enemies_to_spawn = remaining

        if not self.enemies_to_spawn and alive_count == 0 and self.spawn_timer > 60:
            self.wave_active = False
            self.boss_active = False
        return new_enemies


# ─── UPGRADE SYSTEM ───────────────────────────────────────────

class UpgradeSystem:
    def __init__(self):
        self.xp = 0
        self.level = 1
        self.choosing = False
        self.choices = []
        self.rerolls = 0

    def add_xp(self, amount, mult=1.0):
        self.xp += int(amount * mult)
        needed = xp_for_level(self.level)
        if self.xp >= needed:
            self.xp -= needed
            self.level += 1
            return True
        return False

    def xp_ratio(self):
        return self.xp / xp_for_level(self.level)

    def generate_choices(self, player):
        options = []

        # Check for evolutions first (priority)
        for name in list(player.weapons.keys()):
            evo = player.check_evolution(name)
            if evo and evo in EVOLUTIONS:
                edata = EVOLUTIONS[evo]
                options.insert(0, {
                    "type": "evolution",
                    "key": name,
                    "name": f"★ {edata['name']}",
                    "desc": edata["desc"],
                    "color": edata["color"],
                })

        # Weapon upgrades
        for name, w in player.weapons.items():
            if name in player.evolved:
                continue
            wdata = WEAPONS[name]
            if w["level"] < 5:
                upgrade = wdata["upgrades"][min(w["level"] - 1, len(wdata["upgrades"]) - 1)]
                options.append({
                    "type": "weapon_upgrade",
                    "key": name,
                    "name": f"{wdata['name']} Lv{w['level'] + 1}",
                    "desc": upgrade["desc"],
                    "color": wdata["color"],
                })

        # New weapons
        for name, wdata in WEAPONS.items():
            if name not in player.weapons and len(player.weapons) < 6:
                options.append({
                    "type": "weapon_new",
                    "key": name,
                    "name": f"{wdata['name']} NEW",
                    "desc": wdata["desc"],
                    "color": wdata["color"],
                })

        # Passives
        for name, pdata in PASSIVES.items():
            current = player.passives.get(name, 0)
            if current < pdata["max_level"]:
                options.append({
                    "type": "passive",
                    "key": name,
                    "name": f"{pdata['name']} Lv{current + 1}",
                    "desc": pdata["desc"],
                    "color": pdata["color"],
                })

        random.shuffle(options)
        # Keep evolutions at the front
        evos = [o for o in options if o["type"] == "evolution"]
        others = [o for o in options if o["type"] != "evolution"]
        options = evos + others

        self.choices = options[:3]
        while len(self.choices) < 3:
            self.choices.append({
                "type": "heal", "key": "heal",
                "name": "REPAIR +1 HP", "desc": "Restore 1 health", "color": GREEN,
            })
        self.choosing = True

    def apply_choice(self, index, player):
        if index >= len(self.choices):
            return None
        choice = self.choices[index]
        if choice["type"] == "weapon_upgrade":
            player.upgrade_weapon(choice["key"])
        elif choice["type"] == "weapon_new":
            player.add_weapon(choice["key"])
        elif choice["type"] == "passive":
            player.add_passive(choice["key"])
        elif choice["type"] == "heal":
            player.heal(1)
        elif choice["type"] == "evolution":
            player.evolve_weapon(choice["key"])
        self.choosing = False
        return choice

    def reroll(self, player):
        if self.rerolls > 0:
            self.rerolls -= 1
            self.generate_choices(player)
            return True
        return False


# ─── MAIN GAME ────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "MENU"
        self.frame = 0

        self.font_big = pygame.font.SysFont("Arial", 44, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_sm = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_xs = pygame.font.SysFont("Arial", 13)
        self.font_title = pygame.font.SysFont("Arial", 56, bold=True)

        self.audio = AudioManager()
        self.bg = Background()
        self.meta = self._load_meta()
        self._reset()

    def _reset(self):
        self.player = Player()
        self.enemies = []
        self.projectile_pool = [Projectile() for _ in range(MAX_PROJECTILES)]
        self.enemy_proj_pool = [EnemyProjectile() for _ in range(MAX_ENEMY_PROJECTILES)]
        self.gem_pool = [XPGem() for _ in range(MAX_XP_GEMS)]
        self.particles = ParticlePool(500)
        self.texts = FloatingTextPool(40)
        self.fx = ScreenFX()
        self.waves = WaveManager()
        self.upgrades = UpgradeSystem()
        self.spatial = SpatialHash(64)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_timer = 0
        self.credits_earned = 0
        self.kills = 0
        self.frame = 0
        self.boss_warning_timer = 0
        self.death_ghosts = []
        self.xp_mult = 1.0 + self.meta.get("xp_gain_level", 0) * 0.15
        self.credit_mult = 1.0 + self.meta.get("credit_mult_level", 0) * 0.15
        self.upgrades.rerolls = self.meta.get("reroll_level", 0)
        # Apply meta upgrades
        extra_hp = self.meta.get("starting_hp_level", 0)
        if extra_hp:
            self.player.max_hp += extra_hp
            self.player.hp = self.player.max_hp
        extra_pickup = self.meta.get("pickup_range_level", 0) * 20
        self.player.pickup_radius += extra_pickup

    def _get_projectile(self):
        for p in self.projectile_pool:
            if not p.active:
                return p
        return None

    def _get_gem(self):
        for g in self.gem_pool:
            if not g.active:
                return g
        return None

    def _get_enemy_proj(self):
        for p in self.enemy_proj_pool:
            if not p.active:
                return p
        return None

    def _active_projectiles(self):
        return [p for p in self.projectile_pool if p.active]

    def _active_gems(self):
        return [g for g in self.gem_pool if g.active]

    def _active_enemy_projs(self):
        return [p for p in self.enemy_proj_pool if p.active]

    # ─── META PERSISTENCE ────────────────────────────────────

    def _load_meta(self):
        default = {
            "credits": 0, "total_runs": 0, "best_score": 0,
            "total_kills": 0, "best_wave": 0,
            "starting_hp_level": 0, "xp_gain_level": 0,
            "pickup_range_level": 0, "credit_mult_level": 0,
            "starting_dash_level": 0, "reroll_level": 0,
        }
        try:
            if os.path.exists(SAVE_PATH):
                with open(SAVE_PATH, 'r') as f:
                    data = json.load(f)
                    for k, v in default.items():
                        data.setdefault(k, v)
                    return data
        except Exception:
            pass
        return default

    def _save_meta(self):
        self.meta["total_runs"] += 1
        self.meta["total_kills"] += self.kills
        self.meta["best_score"] = max(self.meta["best_score"], self.score)
        self.meta["best_wave"] = max(self.meta["best_wave"], self.waves.wave)
        self.meta["credits"] += int(self.credits_earned * self.credit_mult)
        try:
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            with open(SAVE_PATH, 'w') as f:
                json.dump(self.meta, f, indent=2)
        except Exception:
            pass

    # ─── UPDATE ───────────────────────────────────────────────

    def update(self):
        if self.state != "PLAYING":
            return

        if self.upgrades.choosing:
            self.particles.update()
            self.texts.update()
            self.fx.update()
            for e in self.enemies:
                e.pos += e.vel * 0.02
            return

        time_scale = self.fx.get_time_scale()
        if time_scale == 0:
            self.fx.update()
            return

        dt = time_scale
        self.frame += 1
        keys = pygame.key.get_pressed()
        self.player.move(keys, dt)

        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

        # ── Waves ──
        was_active = self.waves.wave_active
        new_types = self.waves.update(self.frame, len(self.enemies))

        if was_active and not self.waves.wave_active and self.waves.wave > 0:
            self.audio.play('wave_clear')
            self.fx.slowmo(30, 0.3)
            self.texts.spawn((WIDTH // 2 - 60, 80), "WAVE CLEAR", GREEN, 32)

        for etype in new_types:
            if etype == "boss":
                boss = Boss("firewall", self.waves.wave)
                self.enemies.append(boss)
                self.boss_warning_timer = 120
                self.fx.shake(12)
                self.fx.flash(CLR_BOSS, 40)
                self.texts.spawn((WIDTH // 2 - 80, 80), "BOSS INCOMING", CLR_BOSS, 36)
                self.audio.play('boss_spawn')
            else:
                self.enemies.append(Enemy(etype, self.waves.wave))

        if self.boss_warning_timer > 0:
            self.boss_warning_timer -= 1

        # ── Auto-fire (pulse_shot etc) ──
        shots = self.player.get_fire_targets(self.enemies)
        did_shoot = False
        for name, target, proj_i, proj_count in shots:
            stats = self.player.get_weapon_stats(name)
            p = self._get_projectile()
            if p:
                direction = (target.pos - self.player.pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                if proj_count > 1:
                    spread = 0.15 * (proj_i - (proj_count - 1) / 2)
                    angle = math.atan2(direction.y, direction.x) + spread
                    direction = vec(math.cos(angle), math.sin(angle))
                vel = direction * stats["speed"]
                p.spawn(self.player.pos, vel, stats["damage"],
                       stats.get("radius", 4), stats["color"],
                       stats.get("pierce", 0))
                did_shoot = True
        if did_shoot:
            self.audio.play('shoot')

        # ── Drone shots ──
        drone_shots = self.player.get_drone_shots(self.enemies)
        for drone, target, damage, speed, radius in drone_shots:
            p = self._get_projectile()
            if p:
                drone_pos = drone.get_pos(self.player.pos)
                direction = (target.pos - drone_pos)
                if direction.length() > 0:
                    direction = direction.normalize()
                p.spawn(drone_pos, direction * speed, damage, radius,
                       WEAPONS["drone"]["color"], 0)

        # ── Laser beam ──
        laser_result = self.player.try_laser(self.enemies)
        if laser_result:
            start, end, damage, hit_enemies = laser_result
            self.audio.play('laser')
            for e in hit_enemies:
                if e.take_damage(damage):
                    self._on_enemy_killed(e)
                else:
                    self.particles.emit(e.pos, PINK, 3, 2)

        # ── Shockwave ──
        hit_enemies, sw_damage = self.player.try_shockwave(self.enemies)
        if hit_enemies:
            stats = self.player.get_weapon_stats("shockwave")
            self.fx.add_shockwave(self.player.pos, stats["radius"], ORANGE)
            self.fx.shake(8)
            self.audio.play('shockwave')
            for e in hit_enemies:
                if e.take_damage(sw_damage):
                    self._on_enemy_killed(e)

        # ── Lightning ──
        chains = self.player.try_lightning(self.enemies)
        if chains:
            self.audio.play('lightning')
        for start, end, enemy, damage in chains:
            if enemy.active and enemy.take_damage(damage):
                self._on_enemy_killed(enemy)
            direction = end - start
            length = direction.length()
            if length > 0:
                for t in range(0, int(length), 8):
                    point = start + direction.normalize() * t
                    point += vec(random.uniform(-3, 3), random.uniform(-3, 3))
                    self.particles.emit(point, WEAPONS["lightning_arc"]["color"], 1, 1, 2)

        # ── Rebuild spatial hash ──
        self.spatial.clear()
        for e in self.enemies:
            self.spatial.insert(e)

        # ── Update enemies ──
        for e in self.enemies[:]:
            e.update(self.player.pos, dt)
            if hasattr(e, 'should_spawn') and e.should_spawn():
                minion = Enemy("dasher", self.waves.wave)
                minion.pos = vec(e.pos)
                self.enemies.append(minion)

        # ── Player-enemy collision ──
        nearby = self.spatial.query(self.player.pos, 60)
        for e in nearby:
            if not e.active:
                continue
            dist = e.pos.distance_to(self.player.pos)
            if dist < e.radius + self.player.radius:
                if self.player.take_damage():
                    self.fx.shake(15)
                    self.fx.flash(RED, 80)
                    self.fx.hitstop(5)
                    self.particles.emit(self.player.pos, RED, 20, 4)
                    self.texts.spawn(self.player.pos, "HIT!", RED, 26)
                    self.audio.play('player_hit')
                    if self.player.hp <= 0:
                        self._die()
            elif self.player.radius + 5 < dist < self.player.radius + 25:
                self.score += 1
                if self.frame % 20 == 0:
                    self.texts.spawn(self.player.pos + vec(0, -20), "NEAR MISS", WHITE, 13)

        # ── Projectile vs enemy ──
        for p in self._active_projectiles():
            p.update(dt)
            if not p.active:
                continue
            for e in self.spatial.query(p.pos, 50):
                if not e.active:
                    continue
                if p.pos.distance_to(e.pos) < e.radius + p.radius:
                    shielded = False
                    if e.type != "shielder":
                        for s in self.spatial.query(e.pos, ENEMY_STATS["shielder"]["shield_radius"] + 10):
                            if s.type == "shielder" and s.active and s.id != e.id:
                                if e.pos.distance_to(s.pos) < ENEMY_STATS["shielder"]["shield_radius"]:
                                    shielded = True
                                    break
                    if shielded:
                        self.particles.emit(p.pos, WHITE, 3, 2)
                        if p.pierce <= 0:
                            p.active = False
                        continue

                    if e.take_damage(p.damage):
                        self._on_enemy_killed(e)
                    else:
                        self.particles.emit(e.pos, e.color, 4, 2)
                        self.fx.hitstop(2)
                        self.audio.play('enemy_hit')

                    if p.pierce > 0:
                        p.pierce -= 1
                    else:
                        p.active = False
                    break

        # ── Orbit blade vs enemy ──
        for blade in self.player.orbit_blades:
            blade_pos = blade.get_pos(self.player.pos)
            for e in self.enemies:
                if not e.active:
                    continue
                if blade_pos.distance_to(e.pos) < e.radius + 10 and blade.can_hit(e.id):
                    blade.register_hit(e.id)
                    if e.take_damage(blade.damage):
                        self._on_enemy_killed(e)
                    else:
                        self.particles.emit(e.pos, PURPLE, 4, 2)

        # ── Boss bullet rings ──
        for e in self.enemies:
            if isinstance(e, Boss) and e.should_fire_ring():
                ring_count = 12 if e.phase == 1 else 20
                for i in range(ring_count):
                    angle = (2 * math.pi / ring_count) * i
                    ep = self._get_enemy_proj()
                    if ep:
                        vel = vec(math.cos(angle) * 3, math.sin(angle) * 3)
                        ep.spawn(e.pos, vel, 1, 5, CLR_BOSS)

        # ── Enemy projectile vs player ──
        for ep in self._active_enemy_projs():
            ep.update(dt)
            if not ep.active:
                continue
            if ep.pos.distance_to(self.player.pos) < ep.radius + self.player.radius:
                ep.active = False
                self.particles.emit(ep.pos, ep.color, 8, 3)
                if self.player.take_damage(ep.damage):
                    self.fx.shake(10)
                    self.fx.flash(RED, 60)
                    self.fx.hitstop(4)
                    self.audio.play('player_hit')
                    self.texts.spawn(self.player.pos, "HIT!", RED, 26)
                    if self.player.hp <= 0:
                        self._die()

        # ── XP gems ──
        for g in self._active_gems():
            collected = g.update(self.player.pos, self.player.pickup_radius, dt)
            if collected:
                if self.frame % 3 == 0:
                    self.audio.play('xp_collect')
                if self.upgrades.add_xp(collected, self.xp_mult):
                    self.upgrades.generate_choices(self.player)
                    self.fx.flash(VIOLET, 40)
                    self.texts.spawn(self.player.pos + vec(-30, -30),
                                   f"LEVEL {self.upgrades.level}!", VIOLET, 30)
                    self.audio.play('level_up')

        # ── Cleanup ──
        self.enemies = [e for e in self.enemies if e.active]

        new_ghosts = []
        for ghost in self.death_ghosts:
            ghost[3] -= 6
            if ghost[3] > 0:
                new_ghosts.append(ghost)
        self.death_ghosts = new_ghosts

        self.particles.update()
        self.texts.update()
        self.fx.update()

    def _die(self):
        self.state = "GAMEOVER"
        self.particles.emit(self.player.pos, CLR_PLAYER, 60, 6)
        self.fx.shake(25)
        self.fx.slowmo(60, 0.2)
        self.credits_earned = self.score // 10
        self.audio.play('player_death')
        self._save_meta()

    def _on_enemy_killed(self, enemy):
        self.particles.emit(enemy.pos, enemy.color, 18, 4)
        self.fx.hitstop(3)
        self.fx.shake(4)
        self.combo += 1
        self.combo_timer = 120
        self.max_combo = max(self.max_combo, self.combo)
        points = 10 * self.combo
        self.score += points
        self.kills += 1
        self.texts.spawn(enemy.pos, f"+{points}", enemy.color, 18)
        self.audio.play('enemy_death')

        self.death_ghosts.append([vec(enemy.pos), enemy.color, enemy.radius, 180])

        if self.combo in (10, 25, 50, 100, 200):
            self.audio.play('combo')
            self.texts.spawn(self.player.pos + vec(-40, -50),
                           f"COMBO x{self.combo}!", AMBER, 28)
            self.fx.flash(AMBER, 25)

        if enemy.type == "splitter":
            for _ in range(2):
                mini = Enemy("stalker", self.waves.wave)
                mini.pos = vec(enemy.pos) + vec(random.uniform(-15, 15), random.uniform(-15, 15))
                mini.radius = 7
                self.enemies.append(mini)

        if isinstance(enemy, Boss):
            self.fx.slowmo(60, 0.15)
            self.fx.flash(CLR_BOSS, 80)
            self.fx.shake(20)
            self.particles.emit(enemy.pos, CLR_BOSS, 50, 6)
            self.texts.spawn(enemy.pos + vec(-40, -40), "BOSS DEFEATED!", CLR_BOSS, 34)

        self.player.try_heal_on_kill()

        for _ in range(enemy.xp_value):
            g = self._get_gem()
            if g:
                g.spawn(enemy.pos, 1)

    # ─── DRAW ─────────────────────────────────────────────────

    def draw(self):
        self.bg.draw(self.screen, self.player.pos, self.frame)

        if self.state in ("PLAYING", "GAMEOVER"):
            # Death ghosts
            for ghost in self.death_ghosts:
                pos, color, radius, alpha = ghost
                if alpha > 0 and radius > 0:
                    s = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*color, max(0, int(alpha))),
                                      (radius + 2, radius + 2), radius, 2)
                    self.screen.blit(s, (int(pos.x) - radius - 2, int(pos.y) - radius - 2))

            for g in self._active_gems():
                g.draw(self.screen)
            for e in self.enemies:
                e.draw(self.screen)
            for p in self._active_projectiles():
                p.draw(self.screen)
            for ep in self._active_enemy_projs():
                ep.draw(self.screen)

            if self.state == "PLAYING":
                self.player.draw(self.screen)

            self.particles.draw(self.screen)
            self.texts.draw(self.screen)

            # Bloom
            self._draw_bloom()
            self.fx.draw(self.screen)
            self._draw_hud()

            if self.upgrades.choosing:
                self._draw_upgrade_screen()

        if self.state == "MENU":
            self._draw_menu()
        elif self.state == "GAMEOVER":
            self._draw_game_over()
        elif self.state == "PAUSED":
            self._draw_pause()
        elif self.state == "SHOP":
            self._draw_shop()

        pygame.display.flip()

    def _draw_bloom(self):
        w4, h4 = WIDTH // 4, HEIGHT // 4
        small = pygame.transform.smoothscale(self.screen, (w4, h4))
        tiny = pygame.transform.smoothscale(small, (w4 // 2, h4 // 2))
        blurred = pygame.transform.smoothscale(tiny, (WIDTH, HEIGHT))
        blurred.set_alpha(35)
        self.screen.blit(blurred, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_hud(self):
        # HP
        for i in range(self.player.max_hp):
            x = 20 + i * 26
            color = UI_HP_FULL if i < self.player.hp else UI_HP_EMPTY
            pygame.draw.rect(self.screen, color, (x, 16, 18, 18), border_radius=3)
            if i < self.player.hp:
                pygame.draw.rect(self.screen, (255, 120, 130), (x, 16, 18, 18), 1, border_radius=3)

        # Score
        stxt = self.font_med.render(f"{self.score:,}", True, UI_TEXT)
        self.screen.blit(stxt, (WIDTH - stxt.get_width() - 20, 16))
        slbl = self.font_xs.render("SCORE", True, UI_TEXT_DIM)
        self.screen.blit(slbl, (WIDTH - stxt.get_width() - 20, 4))

        # Combo
        if self.combo > 1:
            sz = min(32, 20 + self.combo // 5)
            cf = pygame.font.SysFont("Arial", sz, bold=True)
            ctxt = cf.render(f"x{self.combo}", True, AMBER)
            self.screen.blit(ctxt, (WIDTH - ctxt.get_width() - 20, 44))

        # Wave
        wtxt = self.font_sm.render(f"WAVE {self.waves.wave}", True, UI_TEXT)
        self.screen.blit(wtxt, (WIDTH // 2 - wtxt.get_width() // 2, 12))

        # Boss warning
        if self.boss_warning_timer > 0 and (self.boss_warning_timer // 8) % 2:
            warn = self.font_big.render("! BOSS !", True, CLR_BOSS)
            self.screen.blit(warn, (WIDTH // 2 - warn.get_width() // 2, 40))

        # Wave clear
        if self.waves.intermission > 0 and self.waves.wave > 0:
            ct = self.font_med.render("WAVE CLEAR", True, GREEN)
            self.screen.blit(ct, (WIDTH // 2 - ct.get_width() // 2, 38))

        # XP bar
        by = HEIGHT - 22
        bw = WIDTH - 40
        bh = 10
        ratio = self.upgrades.xp_ratio()
        pygame.draw.rect(self.screen, UI_BG, (20, by, bw, bh), border_radius=5)
        if ratio > 0:
            pygame.draw.rect(self.screen, UI_XP_BAR, (20, by, max(1, int(bw * ratio)), bh), border_radius=5)
        pygame.draw.rect(self.screen, UI_BORDER, (20, by, bw, bh), 1, border_radius=5)
        lt = self.font_xs.render(f"LV {self.upgrades.level}", True, UI_TEXT_DIM)
        self.screen.blit(lt, (22, by - 14))

        # Weapon bar
        wx = 20
        wy = HEIGHT - 56
        for name, w in self.player.weapons.items():
            wdata = WEAPONS[name]
            evolved = name in self.player.evolved
            label = f"★{wdata['name'][:7]}" if evolved else f"{wdata['name'][:8]} {w['level']}"
            pygame.draw.rect(self.screen, UI_BG, (wx, wy, 74, 20), border_radius=3)
            clr = EVOLUTIONS.get(wdata.get("evolution"), {}).get("color", wdata["color"]) if evolved else wdata["color"]
            pygame.draw.rect(self.screen, clr, (wx, wy, 74, 20), 1, border_radius=3)
            t = self.font_xs.render(label, True, clr)
            self.screen.blit(t, (wx + 4, wy + 3))
            wx += 80

        # Dash / timer / rerolls
        if self.player.dash_cooldown <= 0:
            dt = self.font_xs.render("[SPACE] DASH", True, CYAN)
        else:
            cd = self.player.dash_cooldown / DASH_COOLDOWN
            dt = self.font_xs.render(f"DASH {cd:.0%}", True, GRAY)
        self.screen.blit(dt, (WIDTH - 110, HEIGHT - 52))

        secs = self.frame // 60
        tt = self.font_xs.render(f"{secs // 60:02d}:{secs % 60:02d}", True, UI_TEXT_DIM)
        self.screen.blit(tt, (WIDTH // 2 - 16, HEIGHT - 50))

    def _draw_upgrade_screen(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        title = self.font_big.render("LEVEL UP", True, VIOLET)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        sub_parts = ["Choose an upgrade (1 / 2 / 3)"]
        if self.upgrades.rerolls > 0:
            sub_parts.append(f"  |  [R] Reroll ({self.upgrades.rerolls} left)")
        sub = self.font_xs.render("".join(sub_parts), True, UI_TEXT_DIM)
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 148))

        card_w, card_h = 230, 170
        total_w = card_w * 3 + 24 * 2
        start_x = WIDTH // 2 - total_w // 2

        for i, choice in enumerate(self.upgrades.choices):
            x = start_x + i * (card_w + 24)
            y = 180
            color = choice["color"]
            is_evo = choice["type"] == "evolution"

            bg_color = (25, 20, 45) if is_evo else UI_CARD_BG
            pygame.draw.rect(self.screen, bg_color, (x, y, card_w, card_h), border_radius=10)
            pygame.draw.rect(self.screen, color, (x, y, card_w, card_h), 2, border_radius=10)
            # Top accent
            pygame.draw.rect(self.screen, color, (x + 2, y + 2, card_w - 4, 3), border_radius=2)

            # Name
            nt = self.font_med.render(choice["name"], True, color)
            if nt.get_width() > card_w - 16:
                nt = self.font_sm.render(choice["name"], True, color)
            self.screen.blit(nt, (x + 12, y + 22))

            # Desc
            dt = self.font_sm.render(choice["desc"], True, UI_TEXT)
            self.screen.blit(dt, (x + 12, y + 60))

            # Type badge
            badge = "EVOLVE" if is_evo else choice["type"].upper().replace("_", " ")
            bt = self.font_xs.render(badge, True, UI_TEXT_DIM)
            self.screen.blit(bt, (x + 12, y + 90))

            # Key
            kt = self.font_med.render(f"[{i + 1}]", True, WHITE)
            self.screen.blit(kt, (x + card_w // 2 - kt.get_width() // 2, y + card_h - 42))

    def _draw_menu(self):
        t = pygame.time.get_ticks() * 0.001

        # Floating particles in bg
        for i in range(30):
            px = (i * 37 + t * 12) % WIDTH
            py = (i * 29 + math.sin(t * 0.5 + i) * 40) % HEIGHT
            alpha = int(20 + 10 * math.sin(t + i))
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*VIOLET, max(0, alpha)), (2, 2), 2)
            self.screen.blit(s, (int(px), int(py)))

        # Title
        title = self.font_title.render("NEON SURVIVOR", True, VIOLET)
        # Subtle glow behind title
        glow = self.font_title.render("NEON SURVIVOR", True, (*VIOLET[:3],))
        glow.set_alpha(30)
        self.screen.blit(glow, (WIDTH // 2 - title.get_width() // 2 + 2, HEIGHT // 2 - 130 + 2))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 130))

        sub = self.font_med.render("Survive. Evolve. Dominate.", True, UI_TEXT_DIM)
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 - 65))

        # Buttons
        pulse = int(abs(math.sin(t * 2)) * 40 + 200)
        buttons = [
            ("PLAY", (pulse, pulse, pulse)),
            ("UPGRADES", UI_TEXT_DIM),
        ]
        for i, (label, color) in enumerate(buttons):
            by = HEIGHT // 2 - 10 + i * 50
            bw, bh = 200, 38
            bx = WIDTH // 2 - bw // 2
            pygame.draw.rect(self.screen, UI_BG, (bx, by, bw, bh), border_radius=6)
            pygame.draw.rect(self.screen, VIOLET if i == 0 else UI_BORDER, (bx, by, bw, bh), 1, border_radius=6)
            bt = self.font_med.render(label, True, color)
            self.screen.blit(bt, (bx + bw // 2 - bt.get_width() // 2, by + 6))

        # Credits display
        ct = self.font_xs.render(f"Credits: {self.meta.get('credits', 0):,}", True, AMBER)
        self.screen.blit(ct, (WIDTH // 2 - ct.get_width() // 2, HEIGHT // 2 + 100))

        # Controls
        controls = ["WASD/Arrows \u2014 Move  |  SPACE \u2014 Dash  |  1/2/3 \u2014 Upgrades  |  ESC \u2014 Pause"]
        for i, line in enumerate(controls):
            ct = self.font_xs.render(line, True, (50, 55, 80))
            self.screen.blit(ct, (WIDTH // 2 - ct.get_width() // 2, HEIGHT // 2 + 140 + i * 18))

    def _draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        go = self.font_big.render("SYSTEM FAILURE", True, RED)
        self.screen.blit(go, (WIDTH // 2 - go.get_width() // 2, HEIGHT // 2 - 130))

        stats = [
            ("Score", f"{self.score:,}"),
            ("Wave", f"{self.waves.wave}"),
            ("Kills", f"{self.kills}"),
            ("Max Combo", f"{self.max_combo}"),
            ("Level", f"{self.upgrades.level}"),
            ("Credits", f"+{self.credits_earned}"),
        ]
        for i, (label, val) in enumerate(stats):
            y = HEIGHT // 2 - 60 + i * 30
            lt = self.font_sm.render(f"{label}:", True, UI_TEXT_DIM)
            vt = self.font_med.render(val, True, UI_TEXT)
            self.screen.blit(lt, (WIDTH // 2 - 100, y))
            self.screen.blit(vt, (WIDTH // 2 + 30, y - 2))

        # Persistent
        mt = self.font_xs.render(
            f"Best: {self.meta['best_score']:,}  |  Runs: {self.meta['total_runs']}  |  "
            f"Bank: {self.meta['credits']:,}",
            True, UI_TEXT_DIM)
        self.screen.blit(mt, (WIDTH // 2 - mt.get_width() // 2, HEIGHT // 2 + 130))

        t = pygame.time.get_ticks() * 0.001
        pulse = int(abs(math.sin(t * 2)) * 40 + 200)
        rt = self.font_sm.render("R \u2014 Retry  |  Q \u2014 Menu", True, (pulse, pulse, pulse))
        self.screen.blit(rt, (WIDTH // 2 - rt.get_width() // 2, HEIGHT // 2 + 160))

    def _draw_pause(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        pt = self.font_big.render("PAUSED", True, UI_TEXT)
        self.screen.blit(pt, (WIDTH // 2 - pt.get_width() // 2, HEIGHT // 2 - 30))
        ht = self.font_sm.render("ESC \u2014 Resume  |  Q \u2014 Menu", True, UI_TEXT_DIM)
        self.screen.blit(ht, (WIDTH // 2 - ht.get_width() // 2, HEIGHT // 2 + 25))

    def _draw_shop(self):
        self.screen.fill(UI_BG)
        title = self.font_big.render("UPGRADES", True, VIOLET)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))

        ct = self.font_med.render(f"Credits: {self.meta['credits']:,}", True, AMBER)
        self.screen.blit(ct, (WIDTH // 2 - ct.get_width() // 2, 80))

        items = list(META_UPGRADES.items())
        card_w, card_h = 280, 80
        cols = 2
        gap = 16
        start_x = WIDTH // 2 - (card_w * cols + gap * (cols - 1)) // 2
        start_y = 120

        for idx, (key, data) in enumerate(items):
            col = idx % cols
            row = idx // cols
            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)

            level_key = f"{key}_level"
            current_level = self.meta.get(level_key, 0)
            maxed = current_level >= data["max"]
            can_afford = self.meta["credits"] >= data["cost"] and not maxed

            bg = (20, 25, 50) if can_afford else (15, 15, 30)
            border = VIOLET if can_afford else (40, 40, 60)

            pygame.draw.rect(self.screen, bg, (x, y, card_w, card_h), border_radius=8)
            pygame.draw.rect(self.screen, border, (x, y, card_w, card_h), 1, border_radius=8)

            # Name + level
            nt = self.font_sm.render(f"{data['name']}", True, UI_TEXT if can_afford else GRAY)
            self.screen.blit(nt, (x + 12, y + 10))

            max_lvl = data["max"]
            lv_str = "MAX" if maxed else f"Lv {current_level}/{max_lvl}"
            lvt = self.font_xs.render(lv_str, True, GREEN if maxed else UI_TEXT_DIM)
            self.screen.blit(lvt, (x + card_w - 60, y + 12))

            # Desc
            dt = self.font_xs.render(data["desc"], True, UI_TEXT_DIM)
            self.screen.blit(dt, (x + 12, y + 34))

            # Cost
            if not maxed:
                cost_color = AMBER if can_afford else (80, 60, 60)
                cot = self.font_sm.render(f"{data['cost']} credits", True, cost_color)
                self.screen.blit(cot, (x + 12, y + 54))

            # Key hint
            kt = self.font_xs.render(f"[{idx + 1}]", True, UI_TEXT_DIM)
            self.screen.blit(kt, (x + card_w - 24, y + 56))

        # Back hint
        bt = self.font_sm.render("ESC \u2014 Back to Menu", True, UI_TEXT_DIM)
        self.screen.blit(bt, (WIDTH // 2 - bt.get_width() // 2, HEIGHT - 50))

    # ─── INPUT ────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

        if event.type == pygame.KEYDOWN:
            if self.state == "MENU":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._reset()
                    self.state = "PLAYING"
                    self.audio.start_music()
                    self.audio.play('menu_select')
                elif event.key == pygame.K_u:
                    self.state = "SHOP"
                    self.audio.play('menu_select')

            elif self.state == "SHOP":
                if event.key == pygame.K_ESCAPE:
                    self.state = "MENU"
                    self.audio.play('menu_select')
                # Buy upgrades 1-6
                items = list(META_UPGRADES.keys())
                for i, key in enumerate(items):
                    if event.key == pygame.K_1 + i:
                        self._try_buy_meta(key)

            elif self.state == "PLAYING":
                if event.key == pygame.K_ESCAPE:
                    self.state = "PAUSED"
                elif event.key == pygame.K_SPACE:
                    if self.player.try_dash():
                        self.particles.emit_directional(
                            self.player.pos, CLR_DASH,
                            -self.player.dash_dir, 10, 0.8, 4)
                        self.audio.play('dash')

                if self.upgrades.choosing:
                    if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        idx = event.key - pygame.K_1
                        choice = self.upgrades.apply_choice(idx, self.player)
                        if choice and choice["type"] == "evolution":
                            self.audio.play('evolution')
                            self.fx.flash(choice["color"], 80)
                            self.fx.slowmo(20, 0.2)
                        else:
                            self.audio.play('menu_select')
                    elif event.key == pygame.K_r:
                        if self.upgrades.reroll(self.player):
                            self.audio.play('menu_select')

            elif self.state == "PAUSED":
                if event.key == pygame.K_ESCAPE:
                    self.state = "PLAYING"
                elif event.key == pygame.K_q:
                    self.audio.stop_music()
                    self.state = "MENU"

            elif self.state == "GAMEOVER":
                if event.key == pygame.K_r:
                    self._reset()
                    self.state = "PLAYING"
                    self.audio.start_music()
                elif event.key == pygame.K_q:
                    self.audio.stop_music()
                    self.state = "MENU"

            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self.state == "MENU":
                # Check button clicks
                bw, bh = 200, 38
                bx = WIDTH // 2 - bw // 2
                if bx <= mx <= bx + bw:
                    if HEIGHT // 2 - 10 <= my <= HEIGHT // 2 - 10 + bh:
                        self._reset()
                        self.state = "PLAYING"
                        self.audio.start_music()
                    elif HEIGHT // 2 + 40 <= my <= HEIGHT // 2 + 40 + bh:
                        self.state = "SHOP"
                        self.audio.play('menu_select')

            elif self.state == "GAMEOVER":
                self._reset()
                self.state = "PLAYING"
                self.audio.start_music()

            elif self.state == "PLAYING" and self.upgrades.choosing:
                card_w, card_h = 230, 170
                total_w = card_w * 3 + 24 * 2
                start_x = WIDTH // 2 - total_w // 2
                y = 180
                for i in range(3):
                    x = start_x + i * (card_w + 24)
                    if x <= mx <= x + card_w and y <= my <= y + card_h:
                        choice = self.upgrades.apply_choice(i, self.player)
                        if choice and choice["type"] == "evolution":
                            self.audio.play('evolution')
                            self.fx.flash(choice["color"], 80)
                        else:
                            self.audio.play('menu_select')
                        break

    def _try_buy_meta(self, key):
        data = META_UPGRADES[key]
        level_key = f"{key}_level"
        current = self.meta.get(level_key, 0)
        if current >= data["max"] or self.meta["credits"] < data["cost"]:
            return
        self.meta["credits"] -= data["cost"]
        self.meta[level_key] = current + 1
        try:
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            with open(SAVE_PATH, 'w') as f:
                json.dump(self.meta, f, indent=2)
        except Exception:
            pass
        self.audio.play('shop_buy')

    # ─── MAIN LOOP ────────────────────────────────────────────

    async def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.update()
            self.draw()
            self.clock.tick(FPS)
            await asyncio.sleep(0)
        pygame.quit()


import asyncio

async def main():
    game = Game()
    await game.run()

if __name__ == "__main__":
    asyncio.run(main())
