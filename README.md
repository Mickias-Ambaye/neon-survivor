# Neon Survivor

A Vampire Survivors-inspired arena survival game built with Python and Pygame. All visuals are procedurally drawn and all audio is synthesized at runtime — zero external assets needed.

## Play Online

**[Play Neon Survivor in your browser](https://mickias136.github.io/neon-survivor/)**

## Features

- **6 Weapons** — Pulse Shot, Orbit Blade, Shockwave, Lightning Arc, Drone, Laser Beam
- **6 Passive Upgrades** — Speed Boost, Shield Regen, Magnet, Damage Amp, XP Boost, Cooldown Reduction
- **6 Weapon Evolutions** — Max a weapon + the right passive to unlock its evolved form
- **7 Enemy Types** — Stalkers, Dashers, Splitters, Orbiters, Shielders, Carriers, Glitchers
- **Boss Fights** — Every 10 waves, with bullet-hell attack patterns
- **Meta Progression** — Earn credits, buy permanent upgrades between runs
- **Procedural Audio** — 17 SFX + synthwave music loop, all generated with numpy
- **Screen Effects** — Bloom, screen shake, hit-stop, slow-mo, shockwave rings

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrow Keys | Move |
| Space | Dash (invincible frames) |
| R | Reroll upgrade choices |
| P / Escape | Pause |

## Run Locally

```bash
pip install pygame numpy
cd neon_survivor
python main.py
```

## Tech

Built entirely in Python with Pygame. No sprites, no audio files — everything is rendered and synthesized at runtime using math.
