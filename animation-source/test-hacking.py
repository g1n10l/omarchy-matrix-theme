import unittest
import subprocess
import tempfile
from pathlib import Path
from hacking_terminal import DURATION, STAGES, terminal_rows, terminal_asset, terminal_filter, terminal_strip, strip_filter
from lighting_video import filter_graph


class TerminalTests(unittest.TestCase):
    def test_thirty_minute_story_and_loop_seam(self):
        rows = terminal_rows()
        self.assertEqual(DURATION, 1800)
        self.assertEqual(len(rows), DURATION + 20)
        self.assertEqual(rows[DURATION:], rows[:20])
        self.assertNotEqual(rows[:20], rows[12:32])
        for index, (stage, _) in enumerate(STAGES):
            self.assertIn(stage, rows[index * 180])
        self.assertIn('report complete', rows[1799])

    def test_reproducible_animation_across_lighting_slots(self):
        self.assertEqual(terminal_rows(), terminal_rows())

    def test_rendered_loop_boundary_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'animation-source').mkdir()
            path, _ = terminal_asset(root)
            frames = []
            for second in [0, 900, DURATION]:
                graph = (f'color=c=0x030a05:s=224x152:r=2:d=1,'
                         f'setpts=PTS+{second}/TB,' + terminal_filter(path))
                frames.append(subprocess.check_output([
                    'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', graph,
                    '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']))
            self.assertEqual(frames[0], frames[2])
            self.assertNotEqual(frames[0], frames[1])
            _, revision = terminal_asset(root)
            strip = terminal_strip(root, path, revision)
            cropped = []
            viewport = 'crop=' + strip_filter().split(',crop=', 1)[1]
            for second in [0, 900, DURATION]:
                graph = f'setpts=PTS+{second}/TB,' + viewport
                cropped.append(subprocess.check_output([
                    'ffmpeg', '-v', 'error', '-filter_threads', '2', '-framerate', '2', '-i', str(strip),
                    '-vf', graph, '-frames:v', '1',
                    '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']))
            self.assertEqual(cropped[0], cropped[2])
            self.assertNotEqual(cropped[0], cropped[1])

    def test_short_lighting_loop_uses_correct_mask_timing(self):
        look = dict(brightness=0, gamma=1, saturation=1, red=0, blue=0, lamp_dim=1)
        for flicker in [False, True]:
            graph = filter_graph(look, flicker, fps=2)
            self.assertIn('[0:v]fps=2', graph)
            self.assertEqual(graph.count('loop=loop=23:size=1:start=0,setpts=N/2/TB'), 2)


if __name__ == '__main__':
    unittest.main()
