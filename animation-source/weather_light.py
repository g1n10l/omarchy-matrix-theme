"""Open-Meteo weather with bounded cache freshness and offline fallback."""
from datetime import datetime, timezone
import json
import math
import os
import sys
from pathlib import Path
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CACHE = Path.home()/'.cache/matrix-weather.json'


def validated(current, now):
    def number(key, lower, upper):
        value = current.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError('Invalid weather field: '+key)
        return float(value)
    result = dict(time=number('time', now-6*3600, now+600),
                  cloud_cover=number('cloud_cover', 0, 100),
                  precipitation=number('precipitation', 0, 500),
                  weather_code=number('weather_code', 0, 99))
    if result['weather_code'] != int(result['weather_code']):
        raise ValueError('Invalid weather code')
    return result


def save_cache(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.matrix-weather-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def current_weather(latitude, longitude, now=None, cache_path=CACHE):
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    location = [latitude, longitude]
    cache = {}
    try:
        cache = json.loads(cache_path.read_text())
        if not isinstance(cache, dict) or cache.get('location') != location:
            cache = {}
        for field in ['fetched_at', 'attempted_at']:
            value = cache.get(field, 0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value > now:
                cache[field] = 0
        data = validated(cache.get('current', {}), now)
        if int(cache.get('fetched_at', 0)//1800) == int(now//1800):
            return dict(data, source='cache')
    except (OSError, ValueError, TypeError, AttributeError):
        data = None
        if not isinstance(cache, dict):
            cache = {}
    # A failed request is retried after five minutes, without delaying every run.
    if now-cache.get('attempted_at', 0) < 300:
        return dict(data, source='stale-cache') if data else {'source': 'solar-only'}
    query = urlencode(dict(latitude=latitude, longitude=longitude,
                           current='cloud_cover,precipitation,weather_code',
                           timezone='Europe/Warsaw', timeformat='unixtime'))
    try:
        request = Request('https://api.open-meteo.com/v1/forecast?'+query,
                          headers={'User-Agent': 'MatrixWallpaper/1.0 (personal desktop)'})
        with urlopen(request, timeout=6) as response:
            payload = json.load(response)
        fresh = validated(payload['current'], now)
        save_cache(cache_path, dict(location=location, fetched_at=now, attempted_at=now, current=fresh))
        return dict(fresh, source='Open-Meteo')
    except (OSError, ValueError, KeyError, TypeError, TimeoutError) as error:
        print('Weather unavailable; using cached weather or solar lighting: '+str(error), file=sys.stderr)
        # Sandbox network denial must not suppress the real desktop's next request.
        if isinstance(getattr(error, 'reason', error), PermissionError):
            return dict(data, source='stale-cache') if data else {'source': 'solar-only'}
        try:
            save_cache(cache_path, dict(location=location, fetched_at=cache.get('fetched_at', 0),
                                       attempted_at=now, current=data))
        except OSError:
            pass
        return dict(data, source='stale-cache') if data else {'source': 'solar-only'}


def apply_weather(look, weather):
    result = dict(look)
    result['weather'] = weather
    if weather['source'] == 'solar-only':
        return result
    # Quantization avoids another full video render for insignificant model noise.
    clouds = round(weather['cloud_cover']/10)/10
    rain = min(1.0, round(weather['precipitation']*2)/2/5)
    code = int(weather['weather_code'])
    fog = 1.0 if code in (45, 48) else 0.0
    snow = 1.0 if code in (71, 73, 75, 77, 85, 86) else 0.0
    sun = max(0.0, min(1.0, (look['elevation']+12)/24))
    attenuation = max(0.30, 1-0.45*clouds-0.15*rain-0.20*fog)
    result['brightness'] = look['brightness']-sun*(0.018*clouds+0.012*rain+0.012*fog)
    result['gamma'] = max(0.15, look['gamma']*(1-sun*(0.06*clouds+0.04*rain)))
    result['saturation'] = max(0.10, look['saturation']*(1-0.20*clouds-0.12*rain-0.35*fog))
    result['red'] = look['red']*attenuation
    result['blue'] = look['blue']+sun*0.025*clouds
    result['contrast'] = 1-sun*(0.06*clouds+0.10*rain+0.35*fog+0.12*snow)
    return result
