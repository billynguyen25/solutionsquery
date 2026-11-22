import json
import os
import tempfile
import unittest
from unittest import mock

from solutionsquery.agents import PERSONAS
from solutionsquery.cli import main, slugify
from tests.fakes import FakeClient


def bid_reply(name):
    doc = {
        "title": f"{name}'s plan",
        "summary": f"summary from {name}",
        "approach": ["step one"],
        "pros": ["fast"],
        "cons": ["risky"],
        "effort": "M",
    }
    return f"Pitch from {name}.\n\n```json\n{json.dumps(doc)}\n```"


class SlugifyTest(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(slugify("Build a Todo App!"), "build-a-todo-app")
        self.assertEqual(slugify("!!!"), "project")


class EndToEndTest(unittest.TestCase):
    def test_full_flow_pick_and_spiral(self):
        script = [
            "STATUS: in_progress\nFirst pass.\n```file hello.py\nprint('hello')\n```",
            "STATUS: done\nFinished.\n```file hello.py\nprint('hello world')\n```",
        ]
        fake = FakeClient(
            by_persona={p.name: bid_reply(p.name) for p in PERSONAS[:3]},
            script=script,
        )
        with tempfile.TemporaryDirectory() as tmp:
            env = {"LLM_API_KEY": "sk-test"}
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch("solutionsquery.cli.ChatClient", return_value=fake):
                rc = main([
                    "build a hello world app",
                    "--agents", "3",
                    "--pick", "2",
                    "--output-dir", tmp,
                    "--no-color",
                ])
            self.assertEqual(rc, 0)
            projects = os.path.join(tmp, "projects")
            dirs = os.listdir(projects)
            self.assertEqual(len(dirs), 1)
            self.assertIn("build-a-hello-world-app", dirs[0])
            proj = os.path.join(projects, dirs[0])
            with open(os.path.join(proj, "hello.py"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "print('hello world')\n")
            self.assertTrue(os.path.exists(os.path.join(proj, "SESSION.md")))
            with open(os.path.join(proj, "SESSION.md"), encoding="utf-8") as fh:
                session = fh.read()
            self.assertIn("build a hello world app", session)
            self.assertIn("WINNER", session)

    def test_missing_api_key_exits(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                main(["some need", "--no-color"])


if __name__ == "__main__":
    unittest.main()
