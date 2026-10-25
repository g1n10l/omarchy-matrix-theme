"""Continuous solar lighting sampled at half-hour boundaries."""
import subprocess
import hashlib
from video_output import video_output
from hacking_terminal import DURATION, FPS, terminal_asset, terminal_filter, terminal_strip, strip_filter
from system_monitor import monitor_asset
from disk_activity import disk_activity_filter


def screens_graph():
    # Each screen owns its timestamps. The side feed loops at its own EOF;
    # it must never set the lifetime or timestamps of the main terminal.
    return (f'[1:v]{strip_filter()}[terminal];'
            f'[2:v]setpts=N/{FPS}/TB[side];'
            '[0:v][terminal]overlay=x=925:y=263:shortest=0:eof_action=repeat[main_room];'
            '[main_room][side]overlay=x=1248:y=316:shortest=0:eof_action=repeat,'
            + disk_activity_filter() + ',format=yuv420p[out]')


def filter_graph(look, flicker=False, fps=24):
    window = (f"eq=brightness={look['brightness']:.6f}:gamma={look['gamma']:.6f}:"
              f"saturation={look['saturation']:.6f}:contrast={look.get('contrast', 1.0):.6f},"
              f"colorbalance=rs={look['red']:.6f}:bs={look['blue']:.6f}")
    graph = (f'[0:v]fps={fps},split=3[base][window][mask];[window]{window}[lit];'
             '[mask]format=gray,lut=y=0,drawbox=x=255:y=0:w=295:h=410:color=white:t=fill,'
             'gblur=sigma=12[wm];[base][lit][wm]maskedmerge[room]')
    # Cover the complete opening, rim and protruding bulb. The old ellipse cut
    # through the bulb and left a bright crescent along the shade. Feather only
    # outside the opening so its silhouette comes entirely from the source.
    lamp_mask = ('clip((X-597)/8,0,1)*clip((685-X)/8,0,1)*'
                 'clip((Y-296)/6,0,1)*clip((334-Y)/8,0,1)')
    reflection_mask = ('max(0.65*exp(-pow((X-643)/49,2)-pow((Y-325)/24,2)),'
                       'max(exp(-pow((X-735)/112,2)-pow((Y-382)/65,2)),'
                       'max(0.85*exp(-pow((X-705)/170,2)-pow((Y-459)/34,2)),'
                       '0.50*exp(-pow((X-579)/63,2)-pow((Y-428)/47,2)))))')
    amount = 0.0 if flicker else look['lamp_dim']
    graph += (f';[room]format=yuv444p,split=3[ra][rb][rm];'
              f'[rb]colorchannelmixer=rr={1-0.58*amount:.6f}:'
              f'gg={1-0.48*amount:.6f}:bb={1-0.35*amount:.6f},'
              f'eq=saturation={1-0.55*amount:.6f},format=yuv444p[unlit];'
              f"[rm]trim=end_frame=1,format=gray,geq=lum='255*({reflection_mask})',"
              f'loop=loop={12*fps-1}:size=1:start=0,setpts=N/{fps}/TB[reflections];'
              '[ra][unlit][reflections]maskedmerge[no_reflections]')
    if flicker:
        bulb_filter = ("eq=brightness='-0.025-0.045*pow(sin(37*t+sin(13*t)),8)'"
                       ":eval=frame:enable='between(t,1,6)'")
    else:
        bulb_filter = (f'eq=gamma={1-0.25*amount:.6f},'
                       f'colorchannelmixer=rr={1-0.82*amount:.6f}:'
                       f'gg={1-0.82*amount:.6f}:bb={1-0.82*amount:.6f},'
                       f'eq=saturation={1-0.85*amount:.6f}')
    graph += (f";[no_reflections]split=3[a][b][m];[b]{bulb_filter},format=yuv444p[dark];"
              f"[m]trim=end_frame=1,format=gray,geq=lum='255*({lamp_mask})',"
              f'loop=loop={12*fps-1}:size=1:start=0,setpts=N/{fps}/TB[lm];'
              '[a][dark][lm]maskedmerge,format=yuv420p[out]')
    return graph


def render_slot(root, look, flicker=False):
    source = root/'backgrounds/00-neo-room-live.mp4'
    terminal, terminal_revision = terminal_asset(root)
    strip = terminal_strip(root, terminal, terminal_revision)
    lighting = filter_graph(look, flicker, FPS)
    terminal_graph = terminal_filter(terminal)
    source_identity = f'{source.stat().st_mtime_ns}:{source.stat().st_size}:'
    side, side_revision = monitor_asset(root, look['slot'])
    fingerprint = (source_identity + lighting +
                   terminal_graph + terminal_revision + side_revision + screens_graph() + f':{DURATION}:{FPS}:strip-v1')
    revision = hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
    output = root/'daylight/half-hour'/(look['key']+'-lamp-off-v2-'+revision+('-flicker' if flicker else '')+'.mp4')
    if output.is_file():
        return output
    # Light a short room loop once. The long terminal sequence is composed
    # afterwards, avoiding thirty minutes of repeated spatial mask processing.
    room_revision = hashlib.sha256((source_identity + lighting).encode()).hexdigest()[:12]
    room = root/'daylight/room-loops'/(room_revision+'.mp4')
    if not room.exists():
        with video_output(room) as temporary:
            subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-y', '-filter_complex_threads', '2',
                            '-i', str(source), '-filter_complex', lighting, '-map', '[out]', '-an',
                            '-c:v', 'libx264', '-threads', '2', '-preset', 'fast', '-crf', '19',
                            '-movflags', '+faststart', str(temporary)], check=True)
    graph = screens_graph()
    with video_output(output) as temporary:
        subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-y', '-filter_complex_threads', '2',
                        '-stream_loop', '-1', '-i', str(room),
                        '-framerate', str(FPS), '-i', str(strip),
                        '-stream_loop', '-1', '-i', str(side),
                        '-filter_complex', graph, '-map', '[out]', '-t', str(DURATION), '-an',
                        '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '19',
                        '-movflags', '+faststart', str(temporary)], check=True)
    room.unlink(missing_ok=True)
    return output
