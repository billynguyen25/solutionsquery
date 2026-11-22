import os
import tempfile
import unittest

from solutionsquery.agents import PERSONAS
from solutionsquery.bid import Bid
from solutionsquery.spiral import parse_status, run_spiral
from tests.fakes import FakeClient


def make_bid():
    return Bid(persona=PERSONAS[0], raw="", title="Plan", summary="s", approach=["a"], effort="M")


class ParseStatusTest(unittest.TestCase):
    def test_done(self):
        self.assertEqual(parse_status("STATUS: done\nrest"), "done")

    def test_in_progress(self):
        self.assertEqual(parse_status("STATUS: in_progress"), "in_progress")

    def test_default(self):
        self.assertEqual(parse_status("no status line"), "in_progress")


class RunSpiralTest(unittest.TestCase):
    def test_stops_on_done_and_writes_files(self):
        script = [
            "STATUS: in_progress\nBuilding.\n```file main.py\nprint(1)\n```",
            "STATUS: in_progress\nRefining.\n```file util.py\nX = 2\n```",
            "STATUS: done\nAll done.\n```file main.py\nprint('final')\n```",
        ]
        client = FakeClient(script=script)
        with tempfile.TemporaryDirectory() as root:
            result = run_spiral(client, PERSONAS[0], "need", make_bid(), root, max_iterations=8)
            self.assertEqual(result.iterations, 3)
            self.assertEqual(result.files, ["main.py", "util.py"])
            with open(os.path.join(root, "main.py"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "print('final')\n")
            self.assertIn("All done", result.final_text)

    def test_respects_max_iterations(self):
        script = [
            "STATUS: in_progress\n```file f%d.py\nx\n```" % i for i in range(5)
        ]
        client = FakeClient(script=script)
        with tempfile.TemporaryDirectory() as root:
            result = run_spiral(client, PERSONAS[1], "need", make_bid(), root, max_iterations=3)
            self.assertEqual(result.iterations, 3)
            self.assertEqual(result.files, ["f0.py", "f1.py", "f2.py"])

    def test_unsafe_paths_are_skipped(self):
        script = ["STATUS: done\n```file ../evil.py\nx\n```\n```file ok.py\ny\n```"]
        client = FakeClient(script=script)
        with tempfile.TemporaryDirectory() as root:
            result = run_spiral(client, PERSONAS[2], "need", make_bid(), root, max_iterations=2)
            self.assertEqual(result.files, ["ok.py"])
            self.assertFalse(os.path.exists(os.path.join(root, "..", "evil.py")))

    def test_conversation_grows(self):
        script = [
            "STATUS: in_progress\n```file a.py\n1\n```",
            "STATUS: done\nfinished",
        ]
        client = FakeClient(script=script)
        with tempfile.TemporaryDirectory() as root:
            run_spiral(client, PERSONAS[0], "need", make_bid(), root, max_iterations=5)
        last = client.calls[-1]
        roles = [m["role"] for m in last]
        self.assertEqual(roles, ["system", "user", "assistant", "user"])


if __name__ == "__main__":
    unittest.main()
