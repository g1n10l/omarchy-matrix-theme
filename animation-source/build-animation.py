from pathlib import Path
import subprocess
from video_output import video_output
from disk_activity import disk_activity_filter
p=Path(__file__).resolve().parent
rows=[
'root@localhost:~# ./trace',
'connecting to relay 07...',
'carrier detected',
'handshake .......... OK',
'route 192.168.0.12',
'checking encrypted channel',
'RX 0xAF09  TX 0x77E2',
'packet 00481 accepted',
'packet 00482 accepted',
'signal integrity: 99.8%',
'listening on port 1999',
'................................',
'node 03 > node 07 > node 12',
'cipher stream synchronized',
'loading trace buffer...',
'01001000 01100101 01101100',
'RX 0x6B21  TX 0x00FF',
'searching routing table',
'connection established',
'watching incoming traffic',
'packet 00483 accepted',
'packet 00484 accepted',
'keepalive received',
'................................',
]
(p/'terminal-main.txt').write_text('\n'.join(rows*3))
(p/'terminal-side.txt').write_text('\n'.join(['LINK 07 ONLINE','RX 000A21F0','TX 001FB092','SIGNAL 99.8%','BUFFER READY','CHECKSUM OK','ROUTE ACTIVE','RELAY 03 OK','MONITORING...','----------------','PORT 1999','TRACE RUNNING']*5))
font='/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf'
# Screen overlays stay inside the glass. Every time expression repeats in 12 s.
f=[
'[0:v]crop=1672:940:0:0,setsar=1[room]',
f"[1:v]drawtext=fontfile={font}:textfile={p/'terminal-main.txt'}:expansion=none:fontcolor=0x449b36:fontsize=7:line_spacing=1:x=6:y='6-mod(t*16,192)',drawgrid=w=0:h=3:t=1:c=black@0.17,drawbox=x=6:y=143:w=4:h=2:color=0x83ce69:t=fill:enable='lt(mod(t,1),0.5)',eq=brightness='0.002*sin(2*PI*t*2)+0.001*sin(2*PI*t*7)':eval=frame[main]",
f"[2:v]drawtext=fontfile={font}:textfile={p/'terminal-side.txt'}:expansion=none:fontcolor=0x3f8b31:fontsize=5:line_spacing=1:x=4:y='4-mod(t*6,72)',drawgrid=w=0:h=3:t=1:c=black@0.2,perspective=x0=0:y0=2:x1=148:y1=0:x2=0:y2=116:x3=145:y3=122:sense=destination[side]",
'[room][main]overlay=x=925:y=263[r1]',
'[r1][side]overlay=x=1248:y=316[r2]',
"[r2]drawbox=x=1181:y=705:w=4:h=4:color=0x2c4310:t=fill:enable='lt(mod(t,0.5),0.14)',drawbox=x=1239:y=772:w=3:h=3:color=0x82cf36:t=fill:enable='lt(mod(t,0.75),0.15)',drawbox=x=1566:y=605:w=4:h=4:color=0x314b16:t=fill:enable='lt(mod(t,1.5),0.25)',format=yuv420p[out]"
]
f[-1] = f[-1].replace('format=yuv420p[out]', disk_activity_filter()+',format=yuv420p[out]')
(p/'animation.ffscript').write_text(';\n'.join(f))
out=p.parent/'backgrounds/00-neo-room-live.mp4'
cmd=['ffmpeg','-hide_banner','-loglevel','warning','-y','-filter_complex_threads','2','-loop','1','-framerate','24','-i',str(p/'neo-room.png'),'-f','lavfi','-i','color=c=0x030a05:s=224x152:r=24:d=12','-f','lavfi','-i','color=c=0x030805:s=150x124:r=24:d=12','-filter_complex',';'.join(f),'-map','[out]','-t','12','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-movflags','+faststart',str(out)]
with video_output(out) as temporary:
    cmd[-1] = str(temporary)
    subprocess.run(cmd,check=True)
print(out)
