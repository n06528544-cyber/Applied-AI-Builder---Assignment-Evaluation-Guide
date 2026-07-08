"""Pluggable LLM client.

The system is designed to work with *no* API key (deterministic extractor is
the default). When an LLM is configured it is used only as an *enhancer* for
free-form / unstructured documents; every LLM call is wrapped so a failure
degrades gracefully to the heuristic path instead of crashing the pipeline.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional


class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config.get("llm", {})
        self.provider = (self.cfg.get("provider") or "none").lower()
        self.model = self.cfg.get("model", "gpt-4o-mini")
        self.temperature = float(self.cfg.get("temperature", 0.1))
        self.max_tokens = int(self.cfg.get("max_tokens", 2000))
        self.base_url = self.cfg.get("base_url") or ""
        self.api_key = os.environ.get(self.cfg.get("api_key_env", "DDR_LLM_API_KEY"), "")

    @property
    def enabled(self) -> bool:
        return self.provider != "none" and bool(self.api_key)

    def complete(self, system: str, user: str) -> str:
        """Return raw completion text. Raises only if misconfigured."""
        if self.provider in ("openai", "ollama"):
            return self._complete_openai(system, user)
        if self.provider == "anthropic":
            return self._complete_anthropic(system, user)
        raise RuntimeError("LLM provider not configured (set llm.provider + API key).")

    # --- providers ---------------------------------------------------------

    def _complete_openai(self, system: str, user: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        resp = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    def _complete_anthropic(self, system: str, user: str) -> str:
        from anthropic import Anthropic
        client = Anthropic(api_key=self.api_key, base_url=self.base_url or None)
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if hasattr(block, "text"))

    @staticmethod
    def extract_json(text: str) -> Any:
        """Robustly pull a JSON object/array out of a model response."""
        text = text.strip()
        # strip code fences if present
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        if m:
            text = m.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # find the first balanced {...} or [...]
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            if start != -1:
                depth, buf = 0, []
                for ch in text[start:]:
                    buf.append(ch)
                    if ch == opener:
                        depth += 1
                    elif ch == closer:
                        depth -= 1
                        if depth == 0:
                            break
                try:
                    return json.loads("".join(buf))
                except json.JSONDecodeError:
                    continue
        raise ValueError("No JSON found in LLM response")
