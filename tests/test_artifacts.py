import os
import tempfile
import unittest

from solutionsquery.artifacts import parse_file_blocks, safe_resolve, write_file_ops


class ParseFileBlocksTest(unittest.TestCase):
    def test_parses_multiple_blocks(self):
        text = (
            "Here are the files.\n"
            "```file src/main.py\nprint('hi')\n```\n"
            "and\n"
            "```file README.md\n# Title\n```"
        )
        ops = parse_file_blocks(text)
        self.assertEqual([op.path for op in ops], ["src/main.py", "README.md"])
        self.assertEqual(ops[0].content, "print('hi')\n")
        self.assertEqual(ops[1].content, "# Title\n")

    def test_ignores_plain_code_blocks(self):
        self.assertEqual(parse_file_blocks("```python\nprint(1)\n```"), [])

    def test_quoted_path(self):
        ops = parse_file_blocks('```file "my dir/a.txt"\nhello\n```')
        self.assertEqual(ops[0].path, "my dir/a.txt")


class SafeResolveTest(unittest.TestCase):
    def test_allows_nested_relative(self):
        with tempfile.TemporaryDirectory() as root:
            target = safe_resolve(root, "src/deep/main.py")
            self.assertTrue(target.startswith(os.path.abspath(root) + os.sep))

    def test_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                safe_resolve(root, "../evil.py")
            with self.assertRaises(ValueError):
                safe_resolve(root, "src/../../evil.py")

    def test_rejects_absolute(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                safe_resolve(root, "/etc/passwd")


class WriteFileOpsTest(unittest.TestCase):
    def test_writes_files_under_root(self):
        with tempfile.TemporaryDirectory() as root:
            written = write_file_ops(
                root,
                parse_file_blocks("```file a/b.txt\ncontent\n```"),
            )
            self.assertEqual(written, ["a/b.txt"])
            with open(os.path.join(root, "a", "b.txt"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "content\n")

    def test_refuses_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                write_file_ops(root, parse_file_blocks("```file ../evil.txt\nx\n```"))


if __name__ == "__main__":
    unittest.main()
