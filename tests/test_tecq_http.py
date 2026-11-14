import os
import tempfile
import unittest

from chimera.http_server import ChimeraApplication


class TECQHTTPTests(unittest.TestCase):
    def test_configured_tecq_runtime_is_visible_and_advances(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = ChimeraApplication(
                database=os.path.join(tmp, "http-tecq.sqlite3"),
                tecq_cells=32,
            )
            try:
                state = app.state()
                self.assertEqual(state["tecq"]["cells"], 32)
                result = app.tick(1)
                self.assertEqual(result["frames"][0]["tecq_result"]["tick"], 1)
                self.assertEqual(result["state"]["tecq"]["tick"], 1)
            finally:
                app.close()

    def test_invalid_tecq_cell_count_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ChimeraApplication(
                    database=os.path.join(tmp, "invalid.sqlite3"),
                    tecq_cells=1,
                )


if __name__ == "__main__":
    unittest.main()
