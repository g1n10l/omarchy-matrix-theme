#!/usr/bin/env python3
"""Seasonal solar lighting. Solar geometry follows NOAA solareqns.PDF.
Location is explicit; local lighting is pinned to Europe/Warsaw.
"""
import argparse
import calendar
import fcntl
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'daylight.json'
TIMEZONE = ZoneInfo('Europe/Warsaw')


def preview_time(value):
    now = datetime.fromisoformat(value)
    if now.tzinfo is not None:
        return now.astimezone(TIMEZONE)
    local = now.replace(tzinfo=TIMEZONE)
    if local.astimezone(timezone.utc).astimezone(TIMEZONE).replace(tzinfo=None) != now:
        raise ValueError('This local time does not exist in Europe/Warsaw due to DST.')
    return local


def solar_position(now, latitude, longitude):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Solar calculations require a timezone-aware datetime.')
    utc = now.astimezone(timezone.utc)
    # UTC makes the declination independent of the timezone used to express an instant.
    fraction_hour = utc.hour + utc.minute/60 + utc.second/3600
    g = 2 * math.pi / (366 if calendar.isleap(utc.year) else 365) * (utc.timetuple().tm_yday - 1 + (fraction_hour - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868*math.cos(g) - 0.032077*math.sin(g) - 0.014615*math.cos(2*g) - 0.040849*math.sin(2*g))
    dec = (0.006918 - 0.399912*math.cos(g) + 0.070257*math.sin(g) - 0.006758*math.cos(2*g) + 0.000907*math.sin(2*g) - 0.002697*math.cos(3*g) + 0.00148*math.sin(3*g))
    minutes = (now.hour*60 + now.minute + now.second/60 + eq + 4*longitude - now.utcoffset().total_seconds()/60) % 1440
    angle = math.radians(minutes/4 - 180)
    lat = math.radians(latitude)
    elevation = math.degrees(math.asin(max(-1, min(1, math.sin(lat)*math.sin(dec) + math.cos(lat)*math.cos(dec)*math.cos(angle)))))
    return elevation, minutes


def lighting_at(now, latitude, longitude):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Lighting requires a timezone-aware datetime.')
    local = now.astimezone(TIMEZONE)
    slot = local.replace(minute=local.minute//30*30, second=0, microsecond=0)
    elevation, minutes = solar_position(slot, latitude, longitude)
    daylight = max(0.0, min(1.0, (math.sin(math.radians(elevation)) + 0.12)/0.90))
    warmth = math.exp(-(elevation/9)**2)
    return dict(slot=slot.isoformat(), elevation=elevation,
                brightness=-0.12+0.22*daylight, gamma=0.45+0.95*math.sqrt(daylight),
                saturation=0.35+0.5*daylight,
                red=0.28*warmth, blue=0.035*(1-daylight)-0.22*warmth,
                lamp_dim=max(0.0, min(1.0, (elevation+6)/12)),
                key=slot.strftime('%Y-%m-%d/%H%M%z'))



def owe(*arguments):
    return subprocess.run(['owe', *arguments], check=True, text=True,
                          stdout=subprocess.PIPE, timeout=15).stdout


def ensure_playback():
    """Clear pause policy and recover a decoder that stopped advancing."""
    owe('resume')
    owe('always-animate', 'on')
    try:
        first = json.loads(owe('render-status'))
        if first.get('outputs', 0) == 0:
            return
        time.sleep(0.35)
        second = json.loads(owe('render-status'))
        first_time, second_time = first.get('time_pos'), second.get('time_pos')
        stalled = (isinstance(first_time, (int, float)) and
                   isinstance(second_time, (int, float)) and first_time == second_time)
        restart = second.get('error') or not second.get('ready', False) or stalled
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        # A missing or unresponsive renderer cannot return a valid status.
        restart = True
    if restart:
        owe('render-restart')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--flicker', action='store_true', help='Briefly flicker the active night lamp')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--at', help='Local ISO datetime for preview calculations')
    args = parser.parse_args()
    if not CONFIG.exists():
        print('Location required in ' + str(CONFIG))
        raise SystemExit(1)
    conf = json.loads(CONFIG.read_text())
    now = preview_time(args.at) if args.at else datetime.now(TIMEZONE)
    look = lighting_at(now, conf['latitude'], conf['longitude'])
    if not args.at:
        from weather_light import current_weather, apply_weather
        look = apply_weather(look, current_weather(conf['latitude'], conf['longitude'], now.timestamp()))
    print(json.dumps(dict(location=conf['location'], **look), ensure_ascii=False), flush=True)
    if args.status or args.at:
        return
    current = Path.home()/'.local/state/omarchy/current'
    if (current/'theme.name').read_text().strip() != 'matrix':
        return
    lock_path = Path.home()/'.cache/matrix-daylight.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path.open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    # Another invocation may have waited for the lamp effect or a theme switch.
    if (current/'theme.name').read_text().strip() != 'matrix':
        return
    from lighting_video import render_slot
    if args.flicker:
        active = (current/'background').resolve()
        normal_dir = (ROOT/'daylight/half-hour').resolve()
        if look['elevation'] >= -6 or not active.is_relative_to(normal_dir) or not active.is_file():
            return
        effect = render_slot(ROOT, look, flicker=True)
        try:
            owe('set', str(effect))
            owe('refresh')
            ensure_playback()
            time.sleep(8)
        finally:
            if (current/'theme.name').read_text().strip() == 'matrix' and (current/'background').resolve() == effect:
                owe('set', str(active))
                owe('refresh')
                ensure_playback()
        return
    target = render_slot(ROOT, look)
    # Rendering can take several seconds; respect a theme changed meanwhile.
    if (current/'theme.name').read_text().strip() != 'matrix':
        return
    if (current/'background').resolve() != target:
        owe('set', str(target))
        owe('refresh')
    # Recover playback even when the lighting phase has not changed.
    ensure_playback()
    from video_cleanup import cleanup_videos
    cleaned = cleanup_videos(ROOT, datetime.now(TIMEZONE).date(), current/'background', protected=(target,))
    if cleaned['removed']:
        print(json.dumps(dict(cleanup=cleaned)), flush=True)


if __name__ == '__main__':
    main()
