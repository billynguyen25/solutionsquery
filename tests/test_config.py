import os
import unittest
from unittest import mock

from solutionsquery.config import Config


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config.from_env()
        self.assertEqual(cfg.base_url, "https://api.openai.com/v1")
        self.assertEqual(cfg.model, "gpt-4o-mini")
        self.assertEqual(cfg.num_agents, 3)
        self.assertEqual(cfg.max_spiral_iterations, 8)
        self.assertEqual(cfg.output_dir, "solutionsquery-output")
        self.assertEqual(cfg.api_key, "")

    def test_overrides(self):
        env = {
            "LLM_API_KEY": "sk-test",
            "LLM_BASE_URL": "http://localhost:11434/v1/",
            "LLM_MODEL": "qwen2.5",
            "SQ_AGENTS": "5",
            "SQ_MAX_SPIRAL_ITERATIONS": "12",
            "SQ_OUTPUT_DIR": "/tmp/out",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = Config.from_env()
        self.assertEqual(cfg.api_key, "sk-test")
        self.assertEqual(cfg.base_url, "http://localhost:11434/v1")
        self.assertEqual(cfg.model, "qwen2.5")
        self.assertEqual(cfg.num_agents, 5)
        self.assertEqual(cfg.max_spiral_iterations, 12)
        self.assertEqual(cfg.output_dir, "/tmp/out")

    def test_bad_int_falls_back(self):
        with mock.patch.dict(os.environ, {"SQ_AGENTS": "nope"}, clear=True):
            self.assertEqual(Config.from_env().num_agents, 3)

    def test_require_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                Config.from_env().require_api_key()


if __name__ == "__main__":
    unittest.main()
