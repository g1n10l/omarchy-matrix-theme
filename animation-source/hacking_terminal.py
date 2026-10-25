"""Deterministic, offline terminal animation with a thirty-minute cycle."""
import hashlib
import random
import subprocess

DURATION = 30 * 60
FPS = 2
FONT = '/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf'
STAGES = (
    ('RECON', 'discover lab hosts'),
    ('PORT SCAN', 'scan service ports'),
    ('ENUMERATION', 'enumerate lab services'),
    ('FINGERPRINT', 'inspect service banners'),
    ('AUDIT', 'audit sandbox policies'),
    ('ANALYSIS', 'correlate lab findings'),
    ('SANDBOX', 'replay simulated probes'),
    ('TRACE', 'trace virtual routes'),
    ('VERIFY', 'verify sandbox findings'),
    ('REPORT', 'build audit report'),
)


def terminal_rows():
    rng = random.Random(1999)
    rows = []
    for second in range(DURATION):
        stage, command = STAGES[second // 180]
        offset = second % 180
        if offset == 0:
            line = f'[{stage}] {second // 60:02d}:00'
        elif offset == 1:
            line = 'neo@matrix:~$ ' + command
        elif offset == 2:
            line = 'OFFLINE LAB / SIMULATION'
        elif offset >= 177:
            line = f'[OK] {stage.lower()} complete'
        else:
            host = f'10.0.{second // 180}.{rng.randrange(2, 254)}'
            token = f'{rng.getrandbits(32):08x}'
            line = rng.choice([
                f'{host} port {rng.choice([22, 80, 443, 8080])} open',
                f'probe {second:04d}  {token} OK',
                f'RX {token}  TX {rng.getrandbits(16):04x}',
                f'node {rng.randrange(1, 32):02d} route verified',
                f'[{offset * 100 // 177:02d}%] {stage.lower()} {token[:6]}',
                f'lab session {token} accepted',
            ])
        rows.append(line)
    # The final viewport matches the initial viewport at the loop boundary.
    return rows + rows[:20]


def terminal_asset(root):
    rows = terminal_rows()
    # Include the preceding viewport too: the last line can be partially
    # visible above y=6 at the seam, just as during ordinary scrolling.
    content = '\n'.join(rows[DURATION-20:DURATION] + rows) + '\n'
    revision = hashlib.sha256(content.encode()).hexdigest()[:12]
    path = root/'animation-source'/f'terminal-hacking-{revision}.txt'
    if not path.exists():
        path.write_text(content)
    return path, revision


def terminal_filter(path):
    return (f'drawtext=fontfile={FONT}:textfile={path}:expansion=none:'
            "fontcolor=0x449b36:fontsize=7:line_spacing=1:x=6:y='6-10*(t+20)',"
            'drawgrid=w=0:h=3:t=1:c=black@0.17,'
            "drawbox=x=6:y=143:w=4:h=2:color=0x83ce69:t=fill:enable='lt(mod(t,1),0.5)'")


def terminal_strip(root, path, revision):
    """Rasterize the text once; subsequent frames only crop the scroll strip."""
    strip = root/'animation-source'/f'terminal-hacking-{revision}.png'
    if not strip.exists():
        height = (DURATION + 40) * 10 + 152
        graph = (f'color=c=0x030a05:s=224x{height}:r=2:d=1,'
                 f'drawtext=fontfile={FONT}:textfile={path}:expansion=none:'
                 'fontcolor=0x449b36:fontsize=7:line_spacing=1:x=6:y=6')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', graph,
                        '-frames:v', '1', str(strip)], check=True)
    return strip


def strip_filter():
    return (f'loop=loop=-1:size=1:start=0,setpts=N/{FPS}/TB,'
            "crop=224:152:0:'10*(t+20)':exact=1,"
            'drawgrid=w=0:h=3:t=1:c=black@0.17,'
            "drawbox=x=6:y=143:w=4:h=2:color=0x83ce69:t=fill:enable='lt(mod(t,1),0.5)'")
