#!/usr/bin/env python3
"""Build the current half-hour's wallpaper, or preview a given local date."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from daylight import lighting_at, preview_time, TIMEZONE
from lighting_video import render_slot

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--at', help='Local ISO date and time')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    config = json.loads((root/'daylight.json').read_text())
    now = preview_time(args.at) if args.at else datetime.now(TIMEZONE)
    look = lighting_at(now, config['latitude'], config['longitude'])
    if not args.at:
        from weather_light import current_weather, apply_weather
        look = apply_weather(look, current_weather(config['latitude'], config['longitude'], now.timestamp()))
    print(render_slot(root, look))
