#!/usr/bin/env python3
"""Decode every lighting variant and check movement on both CRT screens."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('daylight', ROOT/'animation-source/daylight.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def check_video(path):
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)]))['streams'][0]
    assert (probe['width'], probe['height']) == (1672, 940), path
    from hacking_terminal import DURATION, FPS
    assert float(probe['duration']) == DURATION, path
    assert probe['avg_frame_rate'] == f'{FPS}/1', path
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'], check=True)
    screens = {}
    for name, (width, height, x, y) in {'main': (224, 152, 925, 263), 'side': (150, 124, 1248, 316)}.items():
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-t', '12', '-vf',
                                     f'crop={width}:{height}:{x}:{y},fps=2', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
        size = width*height
        frames = [raw[i:i+size] for i in range(0, len(raw), size)]
        unique = len({hashlib.sha256(f).digest() for f in frames})
        mean_delta = sum(sum(abs(a-b) for a, b in zip(first, second))/size
                         for first, second in zip(frames, frames[1:]))/(len(frames)-1)
        # Small codec fluctuations alone must not pass as scrolling text.
        assert len(frames) == 24, (path, name)
        if name == 'main':
            assert unique >= 20 and mean_delta > 0.2, (path, name, unique, mean_delta)
        screens[name] = dict(frames=len(frames), unique_frames=unique, mean_pixel_delta=round(mean_delta, 3))
    independence = {}
    for name, crop in {'main': '224:152:925:263', 'side': '150:124:1248:316'}.items():
        frames = [subprocess.check_output([
            'ffmpeg', '-v', 'error', '-ss', str(second), '-i', str(path),
            '-vf', 'crop=' + crop, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
            for second in [0, 12]]
        delta = sum(abs(a-b) for a, b in zip(*frames))/len(frames[0])
        independence[name] = round(delta, 3)
    # At the side screen's loop boundary the main simulation must keep going.
    assert independence['main'] > 2, independence
    assert independence['side'] < 2, independence
    return dict(duration=DURATION, fps=probe['avg_frame_rate'], screens=screens,
                delta_at_side_loop=independence)


def main():
    conf = json.loads((ROOT/'daylight.json').read_text())
    tz = controller.TIMEZONE
    now = datetime.now(tz)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = (midnight+timedelta(days=1)).astimezone(timezone.utc)
    cursor = midnight.astimezone(timezone.utc)
    hourly = []
    while cursor < end:
        local = cursor.astimezone(tz)
        look = controller.lighting_at(local, conf['latitude'], conf['longitude'])
        hourly.append(look)
        cursor += timedelta(minutes=30)
    from lighting_video import filter_graph, render_slot
    for look in hourly:
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(ROOT/'backgrounds/00-neo-room-live.mp4'),
                        '-filter_complex_threads', '2', '-filter_complex', filter_graph(look),
                        '-map', '[out]', '-frames:v', '1', '-f', 'null', '-'], check=True)
    look = controller.lighting_at(now, conf['latitude'], conf['longitude'])
    videos = {'current-half-hour': check_video(render_slot(ROOT, look))}
    seasonal = {}
    for date in ['2026-03-20', '2026-06-21', '2026-09-22', '2026-12-21']:
        seasonal[date] = [controller.lighting_at(datetime.fromisoformat(f'{date}T{minute//60:02}:{minute%60:02}').replace(tzinfo=tz), conf['latitude'], conf['longitude']) for minute in range(0,1440,30)]
    report = dict(checked_at=now.isoformat(), location=conf, live_desktop_verified=False,
                  live_limitation='Desktop IPC is denied by the execution sandbox; run apply-animation.sh in the desktop terminal.',
                  videos=videos, hourly=hourly, seasonal=seasonal)
    output = ROOT/'animation-source/verification.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    for name, result in videos.items():
        print(name, ':', ', '.join(f'{screen}={value["unique_frames"]}/24 moving frames' for screen,value in result['screens'].items()))
    for item in hourly:
        print(item['slot'], 'sun=', round(item['elevation'], 2))
    print('Report:', output)


if __name__ == '__main__':
    main()
