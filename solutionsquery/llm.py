from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable, List, Optional


class LLMError(Exception):
    pass


TokenCallback = Callable[[str], None]
Message = dict


class ChatClient:
    """Minimal OpenAI-compatible chat completions client (stdlib only)."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 180,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        on_token: Optional[TokenCallback] = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": on_token is not None,
        }
        if payload["stream"]:
            try:
                return self._stream(payload, on_token)
            except LLMError:
                payload["stream"] = False
        return self._complete(payload, on_token)

    def _post(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            return urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMError(
                f"LLM request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMError(
                f"Could not reach LLM endpoint {self.base_url}: {exc.reason}"
            ) from exc

    def _complete(self, payload: dict, on_token: Optional[TokenCallback]) -> str:
        with self._post(payload) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Unexpected LLM response shape: {str(data)[:300]}"
            ) from exc
        if on_token is not None:
            on_token(text)
        return text

    def _stream(self, payload: dict, on_token: TokenCallback) -> str:
        chunks: List[str] = []
        with self._post(payload) as resp:
            for raw_line in resp:
                for token in parse_sse_line(raw_line.decode("utf-8", errors="replace")):
                    chunks.append(token)
                    on_token(token)
        return "".join(chunks)


def parse_sse_line(line: str) -> List[str]:
    line = line.strip()
    if not line.startswith("data:"):
        return []
    data = line[len("data:"):].strip()
    if not data or data == "[DONE]":
        return []
    try:
        chunk = json.loads(data)
    except json.JSONDecodeError:
        return []
    try:
        content = chunk["choices"][0].get("delta", {}).get("content")
    except (KeyError, IndexError, TypeError):
        return []
    return [content] if content else []
