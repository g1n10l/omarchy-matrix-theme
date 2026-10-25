import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
from daylight import lighting_at
from lighting_video import filter_graph
from weather_light import current_weather, apply_weather, validated

NOW=1792922400
SAMPLE=dict(time=NOW-300,cloud_cover=80,precipitation=2,weather_code=61)

class WeatherTests(unittest.TestCase):
    def test_clouds_and_rain_dim_daylight(self):
        look=lighting_at(datetime(2026,6,21,12,tzinfo=ZoneInfo('Europe/Warsaw')),50.0647,19.945)
        wet=apply_weather(look,dict(SAMPLE,source='test'))
        self.assertLess(wet['brightness'],look['brightness'])
        self.assertLess(wet['gamma'],look['gamma'])
        self.assertLess(wet['saturation'],look['saturation'])
        self.assertEqual(wet['lamp_dim'],look['lamp_dim'])
        self.assertEqual(wet['key'],look['key'])

    def test_fog_reduces_contrast(self):
        look=lighting_at(datetime(2026,6,21,12,tzinfo=ZoneInfo('Europe/Warsaw')),50,20)
        fog=apply_weather(look,dict(SAMPLE,weather_code=45,source='test'))
        clear=apply_weather(look,dict(SAMPLE,weather_code=0,source='test'))
        self.assertLess(fog['contrast'],clear['contrast'])

    def test_night_fog_does_not_light_up_window(self):
        look=lighting_at(datetime(2026,12,21,0,tzinfo=ZoneInfo('Europe/Warsaw')),50,20)
        fog=apply_weather(look,dict(SAMPLE,weather_code=45,source='test'))
        self.assertEqual(fog['contrast'],1)
        self.assertEqual(fog['brightness'],look['brightness'])

    def test_solar_fallback_keeps_original_filters(self):
        look=lighting_at(datetime(2026,6,21,12,tzinfo=ZoneInfo('Europe/Warsaw')),50,20)
        self.assertEqual(filter_graph(look),filter_graph(apply_weather(look,{'source':'solar-only'})))

    def test_cache_and_offline_expiry(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'cache.json'
            path.write_text(json.dumps(dict(location=[50,20],fetched_at=NOW,current=SAMPLE)))
            with patch('weather_light.urlopen') as request:
                self.assertEqual(current_weather(50,20,NOW,path)['source'],'cache')
                request.assert_not_called()
            with patch('weather_light.urlopen',side_effect=OSError('offline')):
                self.assertEqual(current_weather(50,20,NOW+1800,path)['source'],'stale-cache')
                self.assertEqual(current_weather(50,20,NOW+7*3600,path)['source'],'solar-only')

    def test_bad_cache_does_not_stop_wallpaper(self):
        for content in ['[]','null','{bad','{"location":[50,20],"attempted_at":"bad"}']:
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'cache.json';path.write_text(content)
                with patch('weather_light.urlopen',side_effect=OSError('offline')):
                    self.assertEqual(current_weather(50,20,NOW,path)['source'],'solar-only')

    def test_bad_weather_rejected(self):
        for field,value in [('cloud_cover',None),('precipitation',-1),('weather_code',45.5),('time',NOW-7*3600),('cloud_cover',float('nan'))]:
            with self.assertRaises(ValueError):validated(dict(SAMPLE,**{field:value}),NOW)

    def test_fresh_api_response_is_saved(self):
        from io import BytesIO
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'cache.json'
            with patch('weather_light.urlopen',return_value=BytesIO(json.dumps({'current':SAMPLE}).encode())):
                self.assertEqual(current_weather(50,20,NOW,path)['source'],'Open-Meteo')
            self.assertEqual(json.loads(path.read_text())['current']['cloud_cover'],80)

if __name__=='__main__':unittest.main()
