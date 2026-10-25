"""Seasonal solar geometry and Warsaw timezone regression checks."""
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import unittest
from daylight import TIMEZONE, lighting_at, preview_time, solar_position

LAT, LON = 50.0647, 19.9450


def local(value):
    return preview_time(value)


class SolarTests(unittest.TestCase):
    def test_explicit_warsaw(self):
        self.assertEqual(TIMEZONE.key, 'Europe/Warsaw')
        self.assertEqual(local('2026-06-21T12:00').utcoffset(), timedelta(hours=2))
        self.assertEqual(local('2026-12-21T12:00').utcoffset(), timedelta(hours=1))

    def test_supplied_offset_converts_the_instant(self):
        self.assertEqual(local('2026-06-21T10:00Z').isoformat(), '2026-06-21T12:00:00+02:00')
        self.assertEqual(local('2026-12-21T11:00Z').isoformat(), '2026-12-21T12:00:00+01:00')

    def test_same_instant_has_same_solar_position_and_lighting(self):
        for value in ['2026-01-01T00:00', '2026-06-21T12:30', '2026-10-25T02:30+01:00']:
            date = local(value)
            utc = date.astimezone(timezone.utc)
            self.assertAlmostEqual(solar_position(date, LAT, LON)[0], solar_position(utc, LAT, LON)[0], places=10)
            self.assertEqual(lighting_at(date, LAT, LON), lighting_at(utc, LAT, LON))

    def test_spring_clock_jump(self):
        self.assertEqual(local('2026-03-29T00:30Z').isoformat(), '2026-03-29T01:30:00+01:00')
        self.assertEqual(local('2026-03-29T01:00Z').isoformat(), '2026-03-29T03:00:00+02:00')
        with self.assertRaises(ValueError):
            local('2026-03-29T02:30')

    def test_autumn_repeated_hour(self):
        first, second = local('2026-10-25T00:30Z'), local('2026-10-25T01:30Z')
        self.assertEqual(first.hour, second.hour)
        self.assertEqual((first.fold, second.fold), (0, 1))
        self.assertNotEqual(lighting_at(first, LAT, LON)['key'], lighting_at(second, LAT, LON)['key'])

    def test_solstice_and_equinox_peak_elevations(self):
        # At solar noon, elevation is approximately 90 - latitude + declination.
        # Solstice declination is +/-23.44 degrees; equinox declination is near zero.
        for date, declination in [('2026-06-21', 23.44), ('2026-12-21', -23.44), ('2026-03-20', 0), ('2026-09-22', 0)]:
            start = local(date+'T00:00')
            peak = max(solar_position(start+timedelta(minutes=i), LAT, LON)[0] for i in range(1440))
            self.assertAlmostEqual(peak, 90-LAT+declination, delta=.7)

    def test_summer_brighter_and_longer_than_winter(self):
        summer = lighting_at(local('2026-06-21T12:00'), LAT, LON)
        winter = lighting_at(local('2026-12-21T12:00'), LAT, LON)
        self.assertGreater(summer['brightness'], winter['brightness'])
        self.assertGreater(summer['gamma'], winter['gamma'])
        hours = {}
        for date in ['2026-06-21', '2026-12-21']:
            start = local(date+'T00:00')
            hours[date] = sum(solar_position(start+timedelta(minutes=i), LAT, LON)[0] > -.833 for i in range(1440))/60
        self.assertGreater(hours['2026-06-21'], 16)
        self.assertLess(hours['2026-12-21'], 9)

    def test_every_half_hour_of_leap_and_normal_year(self):
        for year in [2024, 2026]:
            date = datetime(year, 1, 1, tzinfo=timezone.utc)
            end = datetime(year+1, 1, 1, tzinfo=timezone.utc)
            while date < end:
                look = lighting_at(date, LAT, LON)
                for name in ['elevation', 'brightness', 'gamma', 'saturation', 'red', 'blue', 'lamp_dim']:
                    self.assertTrue(math.isfinite(look[name]))
                self.assertGreater(look['gamma'], 0)
                self.assertTrue(0 <= look['lamp_dim'] <= 1)
                self.assertTrue(-90 <= look['elevation'] <= 90)
                date += timedelta(minutes=30)


if __name__ == '__main__':
    unittest.main()
