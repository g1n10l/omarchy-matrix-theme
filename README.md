# arch-matrich-theme

An animated Matrix-inspired theme for Arch Linux with Omarchy.

- Solar lighting changes every half hour, with weather adjustments from Open-Meteo.
- The main CRT runs a 30-minute hacking simulation.
- The small CRT independently loops a 12-second recording of real system counters in an htop-style display.
- The desk lamp turns off during daylight and occasionally flickers at night.
- Both powered computer towers have independently blinking orange HDD indicators.

The system monitor records CPU, RAM, swap, load, uptime and processes when a new lighting block is generated. It is a recording, refreshed every half hour, rather than a live monitor. The terminal simulation and HDD activity lights are visual effects.

## Requirements

An existing Omarchy desktop with `owe`, Python 3.9 or newer, FFmpeg with libx264 and libass, and the JetBrainsMono Nerd Font. Python code uses only the standard library. The included font path is `/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf`.

## Install

Clone into the `matrix` directory, which the scripts and services expect. If that directory already exists, keep your current copy and install from a separate checkout instead of overwriting it.

```bash
git clone https://github.com/g1n10l/arch-matrich-theme.git ~/.config/omarchy/themes/matrix
mkdir -p ~/.config/systemd/user
cp ~/.config/omarchy/themes/matrix/systemd/user/matrix-* ~/.config/systemd/user/
omarchy theme set matrix
~/.config/omarchy/themes/matrix/animation-source/apply-animation.sh
```

Edit `daylight.json` to set your city and coordinates. Lighting and scheduling currently use `Europe/Warsaw`. Changing the JSON timezone alone does not change the controller or timer timezone.

Rendering a 30-minute video can take a few minutes. The current background continues playing until the new video is ready. Generated videos stay local and are excluded from Git. Old daily videos are cleaned up by the controller.

The bundled short source video lets the theme run without rebuilding the original animation. To rebuild it after changing the room or base effects:

```bash
python animation-source/build-animation.py
```

## Check the animation

```bash
cd ~/.config/omarchy/themes/matrix
python animation-source/test-hacking.py
python animation-source/test-system-monitor.py
python animation-source/test-solar.py
python animation-source/test-weather.py
python animation-source/test-playback.py
python animation-source/test-cleanup.py
```

Generate a lighting preview without switching the desktop:

```bash
python animation-source/build-daylight.py --at 2026-10-25T11:05
```

System counters in previews are captured at render time, even when the lighting date is historical. Captures from the agent sandbox are marked `SANDBOX`; the desktop service captures its own process namespace.

See [DAYLIGHT.md](animation-source/DAYLIGHT.md) for lighting, weather, playback and recording details. Weather data comes from [Open-Meteo](https://open-meteo.com/), with attribution under CC BY 4.0.
