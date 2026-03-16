import pygame

# --- DISPLAY ---
WIDTH, HEIGHT = 1024, 768
FPS = 60
TITLE = "NEON SURVIVOR"

# --- MODERN COLOR PALETTE ---
# Dark, rich backgrounds with depth
BG_TOP = (8, 10, 28)          # Deep navy
BG_BOT = (18, 8, 32)          # Dark indigo
GRID = (22, 24, 48)

# Primary accent — electric blue/violet
CYAN = (60, 180, 255)
BLUE_LIGHT = (120, 200, 255)
VIOLET = (140, 80, 255)
INDIGO = (90, 60, 220)

# Warm accents
RED = (255, 60, 80)
CRIMSON = (220, 30, 60)
ORANGE = (255, 150, 50)
AMBER = (255, 200, 60)
YELLOW = (255, 220, 80)

# Cool accents
GREEN = (80, 230, 130)
TEAL = (50, 210, 190)
MINT = (100, 255, 200)

# Utility
PINK = (255, 100, 180)
PURPLE = (180, 80, 255)
WHITE = (240, 240, 255)
GRAY = (100, 105, 130)
DARK_GRAY = (40, 42, 60)

# Player palette
CLR_PLAYER = BLUE_LIGHT
CLR_DASH = (180, 220, 255)
CLR_SHIELD = MINT

# Enemy palette — each type distinct and readable
ENEMY_COLORS = {
    "stalker": (255, 70, 90),      # Warm red
    "dasher": (255, 200, 50),      # Gold
    "splitter": (180, 60, 255),    # Violet
    "orbiter": (60, 220, 160),     # Teal-green
    "shielder": (220, 220, 255),   # Pale blue-white
    "sniper": (255, 80, 180),      # Hot pink
    "carrier": (60, 200, 220),     # Cyan-teal
    "glitcher": (140, 140, 170),   # Silver
}

CLR_BOSS = (255, 120, 40)  # Deep orange

# UI colors
UI_BG = (12, 14, 32)
UI_BORDER = (50, 55, 90)
UI_ACCENT = VIOLET
UI_TEXT = (200, 205, 230)
UI_TEXT_DIM = (90, 95, 120)
UI_HP_FULL = (255, 60, 80)
UI_HP_EMPTY = (35, 30, 50)
UI_XP_BAR = VIOLET
UI_CARD_BG = (18, 20, 42)
UI_CARD_HOVER = (28, 30, 55)

# --- PLAYER TUNING ---
PLAYER_HP = 3
PLAYER_SPEED = 0.8
PLAYER_FRICTION = 0.91
PLAYER_RADIUS = 12
PLAYER_INVULN_TIME = 50
DASH_SPEED = 18.0
DASH_DURATION = 9
DASH_COOLDOWN = 90
PICKUP_RADIUS = 40

# --- WEAPONS ---
WEAPONS = {
    "pulse_shot": {
        "name": "Pulse Shot",
        "color": CYAN,
        "damage": 1,
        "speed": 10,
        "fire_rate": 30,
        "radius": 4,
        "pierce": 0,
        "count": 1,
        "desc": "Single target pulse",
        "evolution": "gatling_pulse",
        "evo_requires": "overclock",
        "upgrades": [
            {"fire_rate": -5, "desc": "+Fire Rate"},
            {"damage": 1, "desc": "+1 Damage"},
            {"count": 1, "desc": "+1 Projectile"},
            {"pierce": 2, "fire_rate": -5, "desc": "EVOLVE: Gatling Pulse"},
        ],
    },
    "orbit_blade": {
        "name": "Orbit Blade",
        "color": PURPLE,
        "damage": 2,
        "orbit_radius": 60,
        "orbit_speed": 3,
        "blade_count": 1,
        "hit_cooldown": 30,
        "desc": "Blades orbit you",
        "evolution": "quantum_blades",
        "evo_requires": "phase_shift",
        "upgrades": [
            {"blade_count": 1, "desc": "+1 Blade"},
            {"damage": 1, "orbit_radius": 10, "desc": "+Damage +Range"},
            {"blade_count": 1, "orbit_speed": 1, "desc": "+1 Blade +Speed"},
            {"blade_count": 2, "damage": 2, "desc": "EVOLVE: Quantum Blades"},
        ],
    },
    "shockwave": {
        "name": "Shockwave",
        "color": ORANGE,
        "damage": 3,
        "radius": 80,
        "cooldown": 180,
        "desc": "AOE ring blast",
        "evolution": "singularity",
        "evo_requires": "hardened_core",
        "upgrades": [
            {"radius": 30, "desc": "+Range"},
            {"damage": 2, "desc": "+2 Damage"},
            {"cooldown": -40, "desc": "Faster Cooldown"},
            {"radius": 50, "damage": 3, "desc": "EVOLVE: Singularity"},
        ],
    },
    "lightning_arc": {
        "name": "Lightning Arc",
        "color": (130, 170, 255),
        "damage": 1,
        "chain_count": 2,
        "chain_range": 100,
        "fire_rate": 45,
        "desc": "Chains between enemies",
        "evolution": "storm_protocol",
        "evo_requires": "overclock",
        "upgrades": [
            {"chain_count": 1, "desc": "+1 Chain"},
            {"damage": 1, "desc": "+1 Damage"},
            {"chain_count": 2, "chain_range": 30, "desc": "+2 Chains +Range"},
            {"chain_count": 5, "damage": 2, "desc": "EVOLVE: Storm Protocol"},
        ],
    },
    "drone": {
        "name": "Drone",
        "color": TEAL,
        "damage": 1,
        "speed": 8,
        "fire_rate": 40,
        "radius": 3,
        "drone_count": 1,
        "drone_orbit": 80,
        "desc": "Auto-turret follows you",
        "evolution": "swarm_ai",
        "evo_requires": "coolant",
        "upgrades": [
            {"drone_count": 1, "desc": "+1 Drone"},
            {"damage": 1, "fire_rate": -8, "desc": "+Damage +Speed"},
            {"drone_count": 1, "desc": "+1 Drone"},
            {"drone_count": 2, "damage": 2, "desc": "EVOLVE: Swarm AI"},
        ],
    },
    "laser_beam": {
        "name": "Laser Beam",
        "color": PINK,
        "damage": 4,
        "beam_width": 6,
        "beam_range": 250,
        "fire_rate": 90,
        "beam_duration": 20,
        "desc": "Sustained beam, high DPS",
        "evolution": "prismatic",
        "evo_requires": "overclock",
        "upgrades": [
            {"damage": 2, "desc": "+2 Damage"},
            {"beam_range": 80, "beam_width": 3, "desc": "+Range +Width"},
            {"fire_rate": -20, "desc": "Faster Recharge"},
            {"damage": 4, "beam_width": 4, "desc": "EVOLVE: Prismatic Beam"},
        ],
    },
}

# --- PASSIVE ITEMS ---
PASSIVES = {
    "overclock": {"name": "Overclock", "color": AMBER, "desc": "+15% fire rate", "max_level": 3},
    "hardened_core": {"name": "Hardened Core", "color": RED, "desc": "+1 max HP", "max_level": 3},
    "phase_shift": {"name": "Phase Shift", "color": CYAN, "desc": "+12% move speed", "max_level": 3},
    "magnetic_field": {"name": "Magnetic Field", "color": GREEN, "desc": "+40px pickup range", "max_level": 3},
    "data_leech": {"name": "Data Leech", "color": PINK, "desc": "Heal on kill (3%)", "max_level": 3},
    "coolant": {"name": "Coolant", "color": TEAL, "desc": "-20% dash cooldown", "max_level": 3},
}

# --- WEAPON EVOLUTIONS ---
EVOLUTIONS = {
    "gatling_pulse": {"name": "Gatling Pulse", "desc": "Triple fire, piercing shots",
                      "color": (100, 220, 255)},
    "quantum_blades": {"name": "Quantum Blades", "desc": "6 blades, enemies slowed",
                       "color": (200, 120, 255)},
    "singularity": {"name": "Singularity", "desc": "Black hole pulls enemies in",
                    "color": (255, 180, 80)},
    "storm_protocol": {"name": "Storm Protocol", "desc": "Chains to ALL enemies",
                       "color": (160, 200, 255)},
    "swarm_ai": {"name": "Swarm AI", "desc": "5 drones, dash into enemies",
                 "color": (80, 240, 220)},
    "prismatic": {"name": "Prismatic Beam", "desc": "Splits into 3 beams",
                  "color": (255, 140, 220)},
}

# --- META SHOP ---
META_UPGRADES = {
    "starting_hp": {"name": "Reinforced Core", "desc": "+1 starting HP", "cost": 500, "max": 3},
    "xp_gain": {"name": "Data Absorber", "desc": "+15% XP gain", "cost": 300, "max": 3},
    "pickup_range": {"name": "Wider Net", "desc": "+20px pickup range", "cost": 250, "max": 3},
    "credit_mult": {"name": "Credit Boost", "desc": "+15% credits per run", "cost": 600, "max": 3},
    "starting_dash": {"name": "Quick Start", "desc": "Dash available instantly", "cost": 400, "max": 1},
    "reroll": {"name": "Reroll Token", "desc": "+1 reroll per level-up", "cost": 350, "max": 3},
}

# --- XP CURVE ---
def xp_for_level(level):
    return 50 + level * 15

# --- ENEMIES ---
ENEMY_STATS = {
    "stalker": {"hp": 1, "speed": 2.5, "radius": 10, "xp": 1, "shape": "circle"},
    "dasher": {"hp": 1, "speed": 1.8, "radius": 8, "xp": 2, "shape": "triangle",
               "dash_speed": 8, "dash_interval": 120, "dash_duration": 15},
    "splitter": {"hp": 3, "speed": 1.5, "radius": 18, "xp": 3, "shape": "square"},
    "orbiter": {"hp": 2, "speed": 2.2, "radius": 10, "xp": 2, "shape": "diamond",
                "orbit_dist": 120, "close_rate": 0.3},
    "shielder": {"hp": 3, "speed": 1.2, "radius": 14, "xp": 4, "shape": "hexagon",
                 "shield_radius": 80},
    "carrier": {"hp": 10, "speed": 0.8, "radius": 22, "xp": 8, "shape": "octagon",
                "spawn_interval": 300, "spawn_type": "dasher"},
}

BOSS_STATS = {
    "firewall": {"hp": 80, "speed": 1.0, "radius": 45, "xp": 50,
                 "phase2_hp": 0.5, "phase3_hp": 0.25},
}

# --- WAVES ---
WAVE_INTERMISSION = 180
BOSS_EVERY = 10
