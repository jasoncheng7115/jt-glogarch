# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Is the model going round in circles? (owner 2026-11-26: "如果遇到 loop 思考怎麼辦")

Three shapes, all cheap to check while a reply streams in:

  * the tail of the text is one block repeated back to back (`periodic_tail`):
    the classic degenerate loop, exact repetition;
  * the same sentence keeps coming back with other text between it
    (`repeated_sentences`): a reasoning model that "reconsiders" the same step
    again and again, slightly reworded around a fixed sentence;
  * the same tool called again with the same arguments in one answer
    (`call_key`, used by the chat loop).

Answers are checked only for the first shape, with a longer minimum: a table
or an HTML page repeats markup line by line by design, never a 60-character
block four times in a row with nothing different in between.
"""
from __future__ import annotations

import json
import re

# reasoning: a block of >= 30 characters three times in a row, or one sentence
# (>= 25 characters, not markup or code) seven times in the last 12,000 characters
REASONING_PERIOD = (30, 3)
REASONING_SENTENCE_MIN = 25
REASONING_SENTENCE_REPEATS = 7
REASONING_WINDOW = 12000
# answer: a block of >= 30 characters five times in a row (a Chinese sentence is
# often under 60 characters)
ANSWER_PERIOD = (30, 5)
MAX_PERIOD = 2000
CHECK_EVERY = 600          # characters of new text between two checks

_SPLIT = re.compile(r"(?<=[.!?。！？\n])\s*")
_WS = re.compile(r"\s+")
_CODE = re.compile(r"[<>{}|=;]")


def periodic_tail(text: str, min_period: int, repeats: int, max_period: int = MAX_PERIOD,
                  collapse: bool = True) -> int:
    """Length of the block the text ends with `repeats` times in a row, or 0.
    With `collapse`, whitespace is collapsed first, so a loop that varies only in
    line breaks counts (the length is then of the collapsed block)."""
    t = text[-(max_period * repeats + 200):]
    t = _WS.sub(" ", t).rstrip() if collapse else t.rstrip()
    n = len(t)
    for p in range(min_period, min(max_period, n // repeats) + 1):
        tail = t[n - p:]
        if t[n - p * repeats:] == tail * repeats:
            return p
    return 0


def _norm(sentence: str) -> str:
    return _WS.sub(" ", sentence.strip().lower())


def repeated_sentences(text: str, min_len: int = REASONING_SENTENCE_MIN,
                       repeats: int = REASONING_SENTENCE_REPEATS, window: int = REASONING_WINDOW) -> str:
    """A sentence that comes back word for word `repeats` times in the last `window`
    characters, or "". Lines of markup, code or tables are skipped: an HTML draft or
    a list of hosts repeats its shape on every line by design."""
    counts: dict[str, int] = {}
    for s in _SPLIT.split(text[-window:]):
        k = _norm(s)
        if len(k) < min_len or _CODE.search(k):
            continue
        counts[k] = counts.get(k, 0) + 1
        if counts[k] >= repeats:
            return s.strip()[:160]
    return ""


def reasoning_loop(text: str) -> str:
    """Why the reasoning looks stuck ("" when it does not)."""
    p = periodic_tail(text, *REASONING_PERIOD)
    if p:
        return f"the same {p}-character passage repeated {REASONING_PERIOD[1]} times in a row"
    s = repeated_sentences(text)
    if s:
        return f"the same sentence over and over: {s!r}"
    return ""


def answer_loop(text: str) -> int:
    """Where a looping answer should be cut (the end of the first copy), or 0."""
    p = periodic_tail(text, *ANSWER_PERIOD, collapse=False)
    if not p:
        return 0
    # keep everything up to the end of the first copy
    body = text.rstrip()
    block, k = body[-p:], ANSWER_PERIOD[1]
    while body.endswith(block * (k + 1)):
        k += 1
    return max(0, len(body) - p * (k - 1))


class Watch:
    """Checks a growing text every CHECK_EVERY new characters (the stream calls
    it with the whole text so far)."""

    def __init__(self, kind: str):
        self.kind = kind          # "reasoning" | "answer"
        self.checked = 0

    def check(self, text: str) -> str:
        if len(text) - self.checked < CHECK_EVERY:
            return ""
        self.checked = len(text)
        if self.kind == "reasoning":
            return reasoning_loop(text)
        cut = answer_loop(text)
        return f"answer repeats itself from character {cut}" if cut else ""


def call_key(name: str, args) -> str:
    """The same tool with the same arguments, whatever the key order or spacing."""
    try:
        canon = json.dumps(args, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        canon = str(args)
    return f"{name}|{canon}"
