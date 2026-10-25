"""Publish videos atomically, so a running player never reads a truncated MP4."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import tempfile


@contextmanager
def video_output(target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + target.stem + '-', suffix='.mp4', dir=target.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        yield temporary
        subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-xerror',
                        '-i', str(temporary), '-f', 'null', '-'], check=True)
        temporary.chmod(0o644)
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
