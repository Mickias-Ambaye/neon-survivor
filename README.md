# Neon Survivor

A Vampire Survivors-inspired arena survival game built with HTML5 Canvas and Web Audio API. All visuals are procedurally drawn and all audio is synthesized at runtime — zero external assets, single file, instant load.

## Play Online

**[Play Neon Survivor in your browser](https://mickias-ambaye.github.io/neon-survivor/)**

## Features

- **6 Weapons** — Pulse Shot, Orbit Blade, Shockwave, Lightning Arc, Drone, Laser Beam
- **6 Passive Upgrades** — Speed Boost, Shield Regen, Magnet, Damage Amp, XP Boost, Cooldown Reduction
- **6 Weapon Evolutions** — Max a weapon + the right passive to unlock its evolved form
- **7 Enemy Types** — Stalkers, Dashers, Splitters, Orbiters, Shielders, Carriers, Glitchers
- **Boss Fights** — Every 10 waves, with bullet-hell attack patterns
- **Meta Progression** — Earn credits, buy permanent upgrades between runs (saved to localStorage)
- **Procedural Audio** — All SFX + ambient music synthesized via Web Audio API
- **Screen Effects** — Vignette, screen shake, hit-stop, slow-mo, shockwave rings

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrow Keys | Move |
| Space | Dash (invincible frames) |
| 1 / 2 / 3 | Choose upgrade on level-up |
| R | Reroll upgrade choices |
| P / Escape | Pause |

Mouse/touch also supported for menu navigation and upgrade selection.

## Tech

Single `index.html` file (~50KB). HTML5 Canvas for rendering, Web Audio API for sound. No build step, no dependencies, no frameworks. Deploys directly to GitHub Pages.
