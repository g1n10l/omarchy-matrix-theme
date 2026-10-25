"""Remove generated movies dated before today, preserving the active wallpaper."""
from datetime import date, datetime
import fcntl
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

GENERATED = re.compile(r'^\d{4}[+-]\d{4}(?:-lamp-off-v2(?:-[0-9a-f]{12})?)?(?:-flicker)?\.mp4$')


def cleanup_videos(root, today, background, protected=()):
    cache = root/'daylight/half-hour'
    result = dict(removed=0, bytes_freed=0)
    keep = {Path(path).resolve() for path in protected}
    if not cache.is_dir() or cache.is_symlink():
        return result
    for folder in cache.iterdir():
        if folder.is_symlink() or not folder.is_dir():
            continue
        try:
            day = date.fromisoformat(folder.name)
        except ValueError:
            continue
        if folder.name != day.isoformat() or day >= today:
            continue
        for movie in folder.iterdir():
            if movie.is_symlink() or not movie.is_file() or not GENERATED.fullmatch(movie.name):
                continue
            # Re-read the link because another desktop action can change it.
            if movie.resolve() in keep or movie.resolve() == background.resolve():
                continue
            size = movie.stat().st_size
            movie.unlink()
            result['removed'] += 1
            result['bytes_freed'] += size
        if not any(folder.iterdir()):
            folder.rmdir()
    return result


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    background = Path.home()/'.local/state/omarchy/current/background'
    lock_path = Path.home()/'.cache/matrix-daylight.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        print(json.dumps(cleanup_videos(root, datetime.now(ZoneInfo('Europe/Warsaw')).date(), background)))
