import os
import unittest
from system_monitor import measurement, display_rows


class MonitorTests(unittest.TestCase):
    def counters(self, now, total, idle, ticks, start=42):
        return dict(time=now, cpus={'cpu0': (total, idle)},
                    memory=dict(MemTotal=8192, MemAvailable=2048, SwapTotal=1024, SwapFree=512),
                    processes={(123, start): dict(pid=123, command='real-process', ticks=ticks, rss=512)},
                    load=['1.00', '2.00', '3.00'], uptime=3660)

    def test_actual_counter_deltas_and_memory(self):
        old = self.counters(10, 1000, 600, 100)
        new = self.counters(11, 1100, 675, 100+os.sysconf('SC_CLK_TCK'))
        sample = measurement(old, new)
        self.assertEqual(sample['cpus'], [25])
        self.assertEqual(sample['memory_used'], 6144)
        self.assertEqual(sample['swap_used'], 512)
        self.assertEqual(sample['processes'][0]['cpu'], 100)
        self.assertEqual(sample['processes'][0]['memory'], 6.25)
        rows = '\n'.join(display_rows(sample))
        self.assertIn('real-process', rows)
        self.assertIn('Up 1h 1m', rows)

    def test_reused_pid_does_not_inherit_old_process_cpu(self):
        sample = measurement(self.counters(10, 1000, 600, 100),
                             self.counters(11, 1100, 650, 900, start=99))
        self.assertEqual(sample['processes'][0]['cpu'], 0)

    def test_idle_counters_and_no_swap_are_valid(self):
        old = self.counters(10, 1000, 600, 100)
        new = self.counters(10, 1000, 600, 100)
        new['memory']['SwapTotal'] = new['memory']['SwapFree'] = 0
        sample = measurement(old, new)
        self.assertEqual(sample['cpus'], [0])
        self.assertIn('Swp 0.00/0.00 GiB', display_rows(sample))


if __name__ == '__main__':
    unittest.main()
