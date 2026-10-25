from datetime import date
from pathlib import Path
import tempfile
import unittest
from video_cleanup import cleanup_videos

class CleanupTests(unittest.TestCase):
    def test_old_movies_removed_today_future_and_originals_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            paths=['daylight/half-hour/2026-10-24/1000+0200.mp4',
                   'daylight/half-hour/2026-10-23/1030+0200-lamp-off-v2-123456abcdef-flicker.mp4',
                   'daylight/half-hour/2026-10-25/1000+0100.mp4',
                   'daylight/half-hour/2026-10-26/1000+0100.mp4',
                   'backgrounds/00-neo-room-live.mp4','daylight/day.mp4',
                   'daylight/half-hour/2026-10-24/notes.txt']
            for name in paths:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'video')
            result=cleanup_videos(root,date(2026,10,25),root/'background')
            self.assertEqual(result,dict(removed=2,bytes_freed=10))
            for name in paths[:2]:self.assertFalse((root/name).exists())
            for name in paths[2:]:self.assertTrue((root/name).exists())
            self.assertFalse((root/'daylight/half-hour/2026-10-23').exists())

    def test_active_and_prepared_movies_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'daylight/half-hour/2026-10-24';folder.mkdir(parents=True)
            active=folder/'1000+0200.mp4';active.write_bytes(b'a')
            prepared=folder/'1030+0200.mp4';prepared.write_bytes(b'b')
            background=root/'background';background.symlink_to(active)
            result=cleanup_videos(root,date(2026,10,25),background,protected=(prepared,))
            self.assertEqual(result['removed'],0)
            self.assertTrue(active.exists());self.assertTrue(prepared.exists())

    def test_symlinks_and_unknown_files_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'daylight/half-hour/2026-10-24';folder.mkdir(parents=True)
            outside=root/'original.mp4';outside.write_bytes(b'original')
            (folder/'1000+0200.mp4').symlink_to(outside)
            (folder/'unknown.mp4').write_bytes(b'unknown')
            (folder.parent/'2026-10-23').symlink_to(folder,target_is_directory=True)
            result=cleanup_videos(root,date(2026,10,25),root/'background')
            self.assertEqual(result['removed'],0);self.assertEqual(outside.read_bytes(),b'original')

if __name__=='__main__':unittest.main()
