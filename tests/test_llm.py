import io
import json
import unittest
import urllib.error
from unittest import mock

from solutionsquery.llm import ChatClient, LLMError, parse_sse_line


class ParseSseLineTest(unittest.TestCase):
    def test_content_delta(self):
        line = 'data: {"choices": [{"delta": {"content": "hello"}}]}'
        self.assertEqual(parse_sse_line(line), ["hello"])

    def test_done_and_noise(self):
        self.assertEqual(parse_sse_line("data: [DONE]"), [])
        self.assertEqual(parse_sse_line("event: message"), [])
        self.assertEqual(parse_sse_line("data: {broken"), [])
        self.assertEqual(parse_sse_line('data: {"choices": [{"delta": {}}]}'), [])


def make_http_error(code=401, body=b"unauthorized"):
    return urllib.error.HTTPError(
        url="http://x/v1/chat/completions", code=code, msg="err",
        hdrs=None, fp=io.BytesIO(body),
    )


class ChatClientTest(unittest.TestCase):
    def setUp(self):
        self.client = ChatClient("sk-test", "http://llm.local/v1", "test-model")

    def test_complete_parses_content(self):
        payload = {"choices": [{"message": {"content": "hi there"}}]}
        resp = io.BytesIO(json.dumps(payload).encode())

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return resp.getvalue()

        with mock.patch("urllib.request.urlopen", return_value=Resp()):
            self.assertEqual(
                self.client.chat([{"role": "user", "content": "yo"}]), "hi there"
            )

    def test_http_error_raises_llm_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=make_http_error()):
            with self.assertRaises(LLMError) as ctx:
                self.client.chat([{"role": "user", "content": "yo"}])
            self.assertIn("HTTP 401", str(ctx.exception))

    def test_stream_falls_back_to_complete(self):
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(json.loads(req.data.decode()))
            if calls[-1].get("stream"):
                raise make_http_error(400, b"streaming unsupported")
            payload = {"choices": [{"message": {"content": "full text"}}]}

            class Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return json.dumps(payload).encode()

            return Resp()

        tokens = []
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text = self.client.chat([{"role": "user", "content": "yo"}], on_token=tokens.append)
        self.assertEqual(text, "full text")
        self.assertEqual(tokens, ["full text"])
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0]["stream"])
        self.assertFalse(calls[1]["stream"])

    def test_stream_consumes_sse(self):
        lines = [
            b'data: {"choices": [{"delta": {"content": "Hel"}}]}\n',
            b'data: {"choices": [{"delta": {"content": "lo"}}]}\n',
            b"data: [DONE]\n",
        ]

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def __iter__(self):
                return iter(lines)

        tokens = []
        with mock.patch("urllib.request.urlopen", return_value=Resp()):
            text = self.client.chat([{"role": "user", "content": "yo"}], on_token=tokens.append)
        self.assertEqual(text, "Hello")
        self.assertEqual(tokens, ["Hel", "lo"])


if __name__ == "__main__":
    unittest.main()
