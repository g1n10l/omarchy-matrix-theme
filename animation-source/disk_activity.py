"""Independent amber HDD indicators beside the two powered tower LEDs."""


def disk_activity_filter():
    filters = []
    for x, y, phase, period in [(1172, 707, 0, 3), (1230, 773, 0.5, 4)]:
        pulse = (f"lt(mod(t+{phase},{period}),0.5)+"
                 f"between(mod(t+{phase},{period}),1.5,1.99)")
        filters.extend([
            f'drawbox=x={x}:y={y}:w=3:h=3:color=0x30200b:t=fill',
            f"drawbox=x={x-1}:y={y-1}:w=5:h=5:color=0xa85416@0.25:t=fill:enable='{pulse}'",
            f"drawbox=x={x}:y={y}:w=3:h=3:color=0xff9b2f:t=fill:enable='{pulse}'",
        ])
    return ','.join(filters)
