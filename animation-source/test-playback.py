"""Check playback recovery without changing the live wallpaper."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from video_output import video_output

spec = importlib.util.spec_from_file_location('daylight', Path(__file__).with_name('daylight.py'))
daylight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daylight)


class PlaybackTests(unittest.TestCase):
    def check_recovery(self, states, restart):
        replies = ['', '', *[json.dumps(s) for s in states]]
        if restart:
            replies.append('')
        with patch.object(daylight, 'owe', side_effect=replies) as owe, patch.object(daylight.time, 'sleep'):
            daylight.ensure_playback()
            calls = [c.args for c in owe.call_args_list]
            self.assertIn(('resume',), calls)
            self.assertIn(('always-animate', 'on'), calls)
            self.assertEqual(('render-restart',) in calls, restart)

    def test_moving_video_is_not_restarted(self):
        self.check_recovery([dict(outputs=2, ready=True, time_pos=1), dict(outputs=2, ready=True, time_pos=1.4)], False)

    def test_loop_boundary_is_not_a_stall(self):
        self.check_recovery([dict(outputs=2, ready=True, time_pos=11.9), dict(outputs=2, ready=True, time_pos=.2)], False)

    def test_frozen_video_is_restarted(self):
        self.check_recovery([dict(outputs=2, ready=True, time_pos=1)]*2, True)

    def test_decoder_error_is_restarted(self):
        self.check_recovery([dict(outputs=2, ready=True, time_pos=1), dict(outputs=2, ready=False, error='decode failure')], True)

    def test_no_output_is_not_restarted(self):
        self.check_recovery([dict(outputs=0)], False)

    def test_half_hour_rounding(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo('Europe/Warsaw')
        before = daylight.lighting_at(datetime(2026, 10, 25, 10, 29, tzinfo=tz), 50.0647, 19.945)
        after = daylight.lighting_at(datetime(2026, 10, 25, 10, 30, tzinfo=tz), 50.0647, 19.945)
        self.assertIn('1000', before['key'])
        self.assertIn('1030', after['key'])
        self.assertNotEqual(before['brightness'], after['brightness'])
        for minute in range(30):
            self.assertEqual(before, daylight.lighting_at(datetime(2026, 10, 25, 10, minute, tzinfo=tz), 50.0647, 19.945))

    def test_repeated_clock_hour_has_distinct_cache(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime(2026, 10, 25, 2, 30, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.assertNotEqual(daylight.lighting_at(now, 50, 20)['key'], daylight.lighting_at(now.replace(fold=1), 50, 20)['key'])

    def test_missing_renderer_is_restarted(self):
        error = daylight.subprocess.CalledProcessError(1, ['owe', 'render-status'])
        with patch.object(daylight, 'owe', side_effect=['', '', error, '']) as owe:
            daylight.ensure_playback()
            self.assertEqual(owe.call_args.args, ('render-restart',))

    def test_failed_render_preserves_video(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'night.mp4'
            target.write_bytes(b'previous complete video')
            with self.assertRaises(RuntimeError):
                with video_output(target) as output:
                    output.write_bytes(b'incomplete video')
                    raise RuntimeError('encoder stopped')
            self.assertEqual(target.read_bytes(), b'previous complete video')
            self.assertEqual(list(Path(folder).iterdir()), [target])


if __name__ == '__main__':
    unittest.main()
