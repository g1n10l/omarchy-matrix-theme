"""Record a compact htop-style display from actual Linux /proc counters."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from zoneinfo import ZoneInfo
from video_output import video_output

FPS = 2
SECONDS = 12


def read_counters(proc=Path('/proc')):
    cpus = {}
    for line in (proc/'stat').read_text().splitlines():
        fields = line.split()
        if re.fullmatch(r'cpu\d+', fields[0]):
            ticks = list(map(int, fields[1:9]))  # guest time is already in user/nice
            cpus[fields[0]] = (sum(ticks), ticks[3] + ticks[4])
    memory = {}
    for line in (proc/'meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        memory[key] = int(value.split()[0])
    processes = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry/'stat').read_text()
            name = stat[stat.index('(')+1:stat.rindex(')')]
            fields = stat[stat.rindex(')')+2:].split()
            key = (int(entry.name), int(fields[19]))
            processes[key] = dict(pid=key[0], command=re.sub(r'[^\w. /-]', '?', name),
                                  ticks=int(fields[11])+int(fields[12]),
                                  rss=max(0, int(fields[21]))*os.sysconf('SC_PAGE_SIZE')/1024)
        except (OSError, ValueError, IndexError):
            continue  # processes can exit between directory listing and read
    init = (proc/'1/comm').read_text().strip()
    return dict(time=time.monotonic(), cpus=cpus, memory=memory, processes=processes,
                scope='sandbox' if 'codex' in init else 'system',
                load=(proc/'loadavg').read_text().split()[:3],
                uptime=float((proc/'uptime').read_text().split()[0]))


def measurement(previous, current):
    elapsed = current['time']-previous['time']
    cpu = []
    for name, (total, idle) in current['cpus'].items():
        old_total, old_idle = previous['cpus'].get(name, (total, idle))
        delta = total-old_total
        cpu.append(max(0, min(100, 100*(1-(idle-old_idle)/delta))) if delta > 0 else 0)
    memory = current['memory']
    processes = []
    for key, process in current['processes'].items():
        old = previous['processes'].get(key)
        usage = (100*(process['ticks']-old['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed
                 if old is not None and elapsed > 0 else 0)
        processes.append(dict(pid=process['pid'], command=process['command'], cpu=max(0, usage),
                              memory=100*process['rss']/memory['MemTotal']))
    processes.sort(key=lambda p: (-p['cpu'], -p['memory'], p['pid']))
    return dict(captured_at=datetime.now(ZoneInfo('Europe/Warsaw')).isoformat(),
                scope=current.get('scope', 'system'),
                cpus=cpu, memory_total=memory['MemTotal'],
                memory_used=memory['MemTotal']-memory['MemAvailable'],
                swap_total=memory.get('SwapTotal', 0),
                swap_used=memory.get('SwapTotal', 0)-memory.get('SwapFree', 0),
                load=current['load'], uptime=current['uptime'],
                tasks=len(processes), processes=processes[:5])


def display_rows(sample):
    clock = datetime.fromisoformat(sample['captured_at']).strftime('%H:%M:%S')
    title = 'SANDBOX' if sample.get('scope') == 'sandbox' else 'SYSTEM'
    rows = [f'{title} {clock}  {len(sample["cpus"])} CPU']
    def bar(number, value):
        filled = round(value*7/100)
        return f'{number}[{"|"*filled}{" "*(7-filled)}]{value:4.0f}%'
    for index in range(0, min(8, len(sample['cpus'])), 2):
        row = bar(index, sample['cpus'][index])
        if index+1 < len(sample['cpus']):
            row += ' ' + bar(index+1, sample['cpus'][index+1])
        rows.append(row)
    rows.extend([
        f'Mem {sample["memory_used"]/1048576:.2f}/{sample["memory_total"]/1048576:.2f} GiB',
        f'Swp {sample["swap_used"]/1048576:.2f}/{sample["swap_total"]/1048576:.2f} GiB',
        'Load ' + ' '.join(sample['load']),
        f'Up {int(sample["uptime"]//3600)}h {int(sample["uptime"]%3600//60)}m  Tasks {sample["tasks"]}',
        '   PID CPU% MEM% COMMAND',
    ])
    rows.extend(f'{p["pid"]:6d} {p["cpu"]:4.0f} {p["memory"]:4.1f} {p["command"][:22]}'
                for p in sample['processes'])
    return rows


def monitor_asset(root, slot):
    directory = root/'daylight/system-monitor'
    directory.mkdir(parents=True, exist_ok=True)
    metadata = directory/'latest.json'
    video = directory/'latest.mp4'
    namespace = os.readlink('/proc/self/ns/pid')
    try:
        cached = json.loads(metadata.read_text())
        if (cached['slot'] == slot and cached.get('version') == 2
                and cached.get('pid_namespace') == namespace and video.exists()):
            return video, cached['revision']
    except (OSError, ValueError, KeyError):
        pass
    samples = []
    previous = read_counters()
    for _ in range(SECONDS*FPS):
        time.sleep(1/FPS)
        current = read_counters()
        samples.append(measurement(previous, current))
        previous = current
    revision = hashlib.sha256(json.dumps(samples, sort_keys=True).encode()).hexdigest()[:12]
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 150
PlayResY: 124
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,JetBrainsMono Nerd Font,6,&H0055AA44,&H0055AA44,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,3,2,2,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    def stamp(seconds):
        return f'0:00:{int(seconds):02d}.{int(seconds%1*100):02d}'
    with tempfile.TemporaryDirectory(prefix='matrix-monitor-') as folder:
        subtitles = Path(folder)/'monitor.ass'
        events = []
        for index, sample in enumerate(samples):
            text = r'\N'.join(display_rows(sample))
            events.append(f'Dialogue: 0,{stamp(index/FPS)},{stamp((index+1)/FPS)},Default,,0,0,0,,{{\\q2}}{text}')
        subtitles.write_text(header+'\n'.join(events)+'\n')
        with video_output(video) as temporary:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-filter_threads', '2', '-f', 'lavfi',
                            '-i', f'color=c=0x030805:s=150x124:r={FPS}:d={SECONDS}',
                            '-vf', f'ass={subtitles},perspective=x0=0:y0=2:x1=148:y1=0:x2=0:y2=116:x3=145:y3=122:sense=destination',
                            '-an', '-c:v', 'libx264', '-threads', '2', '-crf', '18', str(temporary)], check=True)
    pending = metadata.with_suffix('.tmp')
    pending.write_text(json.dumps(dict(version=2, slot=slot, revision=revision,
                                       pid_namespace=namespace, samples=samples), indent=2)+'\n')
    pending.replace(metadata)
    return video, revision
