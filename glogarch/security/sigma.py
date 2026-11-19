# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Sigma rules -> Graylog (Lucene) queries (added 1.27).

A deliberately small, honest subset of the Sigma specification: what does not
convert is REFUSED with the reason, never approximated silently, because a rule
that quietly matches nothing looks exactly like a quiet network.

Supported
  * detection: named selections, each a map (AND of its fields), a list of maps
    (OR), or a list of keywords (searched in `message`);
  * values: a scalar or a list (OR; AND with `|all`), null = field absent;
  * modifiers: contains, startswith, endswith, all, re, exists, cased, gt, gte, lt, lte;
  * condition: and / or / not / parentheses, `1 of x*`, `any of x*`, `all of x*`,
    `1 of them`, `all of them`;
  * a per-site field map (Sigma field -> Graylog field).
Refused: aggregations (`| count() ...`), `near`, base64/base64offset, windash,
cidr, wide/utf16, expand, fieldref, and keyword lists with inner wildcards.

Graylog refuses a LEADING wildcard by default, so `contains`, `endswith` and a
value starting with `*` become a regular expression (`field:/.*x.*/`) on the
field, which Lucene evaluates against the indexed term: right for keyword
fields (GIM fields are keywords), NOT for the analyzed `message` field, where
values (and keywords) are searched as phrases instead, and a regex is refused. Matching on keyword fields is
case-sensitive (Sigma's default is case-insensitive): the page says so.
"""
from __future__ import annotations

import fnmatch
import re

import yaml

MAX_RULE_BYTES = 64 * 1024
# Analyzed (tokenized) text in Graylog: searched as phrases, never by regex.
# GELF's short_message is stored as `message` (measured on 7.2.2: a query on
# short_message matched nothing).
TEXT_FIELDS = {"message", "full_message"}
_GELF_FIELDS = {"short_message": "message"}
LEVELS = {"informational": "low", "low": "low", "medium": "medium", "high": "high", "critical": "high"}
_FIELD = re.compile(r"^[A-Za-z0-9_@][A-Za-z0-9_.@-]{0,99}$")   # never a leading '-' (a negation)
_UNSUPPORTED = {"base64", "base64offset", "windash", "cidr", "wide", "utf16", "utf16le", "utf16be",
                "expand", "fieldref"}
_LUCENE_SPECIAL = set('+-&|!(){}[]^"~:\\/ *?<>=')   # *? here are LITERAL ones (escaped in Sigma)
_REGEX_SPECIAL = set('.?+*|{}[]()"\\#@&<>~/')


class SigmaError(ValueError):
    pass


def neg(q: str) -> str:
    """A negation that also holds inside an OR: Lucene reads `a OR NOT b` as
    `a AND NOT b` (a pure negative clause adds nothing to an OR), so every NOT is
    written as `(*:* AND NOT x)` (found by review 2026-11-20, verified on 7.2.2)."""
    return f"(*:* AND NOT {q})"


def parse_rule(text: str) -> dict:
    if len(text.encode("utf-8", "replace")) > MAX_RULE_BYTES:
        raise SigmaError(f"Rule is larger than {MAX_RULE_BYTES // 1024} KiB")
    try:
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
    except yaml.YAMLError as e:
        raise SigmaError(f"Not valid YAML: {str(e).splitlines()[0][:200]}")
    if len(docs) != 1:
        raise SigmaError("Give one Sigma rule at a time")
    r = docs[0]
    if not isinstance(r, dict) or not isinstance(r.get("detection"), dict):
        raise SigmaError("Not a Sigma rule: no detection section")
    if not str(r.get("title") or "").strip():
        raise SigmaError("The rule has no title")
    det = r["detection"]
    if "condition" not in det:
        raise SigmaError("The detection section has no condition")
    tags = [str(t).lower() for t in (r.get("tags") or []) if isinstance(t, (str, int))]
    level = str(r.get("level") or "medium").lower()
    return {"sigma_id": str(r.get("id") or "")[:64], "title": str(r["title"]).strip()[:200],
            "level": level if level in LEVELS else "medium", "status": str(r.get("status") or "")[:30],
            "description": str(r.get("description") or "")[:2000], "tags": tags[:50],
            "logsource": r.get("logsource") if isinstance(r.get("logsource"), dict) else {},
            "detection": det}


def attack_ids(tags: list[str]) -> list[str]:
    """`attack.t1110.003` -> T1110.003 (technique tags only)."""
    out = []
    for t in tags:
        m = re.fullmatch(r"attack\.(t\d{4}(?:\.\d{3})?)", t.strip().lower())
        if m and m.group(1).upper() not in out:
            out.append(m.group(1).upper())
    return out


# --- values ---------------------------------------------------------------------

def _glob_parts(value: str) -> list[tuple[str, str]]:
    """Sigma value -> [(kind, text)], kind 'lit' | 'star' | 'one'. `\\*` is a literal *."""
    out, buf, i = [], "", 0
    while i < len(value):
        c = value[i]
        if c == "\\" and i + 1 < len(value) and value[i + 1] in "*?\\":
            buf += value[i + 1]
            i += 2
            continue
        if c in "*?":
            if buf:
                out.append(("lit", buf))
                buf = ""
            out.append(("star" if c == "*" else "one", c))
        else:
            buf += c
        i += 1
    if buf:
        out.append(("lit", buf))
    return out


def _regex_lit(s: str) -> str:
    return "".join("\\" + c if c in _REGEX_SPECIAL else c for c in s)


def _lucene_lit(s: str) -> str:
    return "".join("\\" + c if c in _LUCENE_SPECIAL else c for c in s)


def _phrase(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _glob_to_query(field: str, parts: list[tuple[str, str]]) -> str:
    if not any(k != "lit" for k, _ in parts):
        return f"{field}:{_phrase(''.join(t for _, t in parts))}"
    if parts and parts[0][0] != "lit":
        # a leading wildcard: Graylog refuses it as a wildcard query -> regex
        rx = "".join(_regex_lit(t) if k == "lit" else (".*" if k == "star" else ".") for k, t in parts)
        return f"{field}:/{rx}/"
    return f"{field}:" + "".join(_lucene_lit(t) if k == "lit" else t for k, t in parts)


def _lucene_regex(rx: str, field: str) -> str:
    """Sigma regexes are unanchored PCRE; Lucene's are anchored and smaller. Anchor
    the meaning (`^`/`$` kept by dropping the .* on that side), refuse what Lucene
    lacks (\\d, \\w, \\s, \\b, (?i), lookarounds, classes like [:alpha:])."""
    i = 0
    while i < len(rx):                      # walk the escapes: \\\\W is a backslash then W, not \\W
        c = rx[i]
        if c == "\\":
            nxt = rx[i + 1] if i + 1 < len(rx) else ""
            if nxt.isalnum():
                raise SigmaError(f"{field}|re: this regular expression uses PCRE syntax Lucene does not have")
            i += 2
            continue
        if rx.startswith("(?", i) or rx.startswith("[:", i):
            raise SigmaError(f"{field}|re: this regular expression uses PCRE syntax Lucene does not have")
        i += 1
    head, tail = rx.startswith("^"), rx.endswith("$") and not rx.endswith("\\$")
    core = rx[1 if head else 0:len(rx) - (1 if tail else 0)]
    if "^" in core.replace("[^", "") or ("$" in core.replace("\\$", "")):
        raise SigmaError(f"{field}|re: anchors are only supported at the start and end")
    core = re.sub(r"(?<!\\)/", r"\\/", core)          # escape an unescaped delimiter, once
    return ("" if head else ".*") + "(" + core + ")" + ("" if tail else ".*")


def _value_query(field: str, value, mods: list[str]) -> str:
    if value is None:
        return neg(f"_exists_:{field}")
    if "exists" in mods:
        if not isinstance(value, bool):
            raise SigmaError(f"{field}|exists takes true or false")
        return f"_exists_:{field}" if value else neg(f"_exists_:{field}")
    for op, sym in (("gte", ">="), ("gt", ">"), ("lte", "<="), ("lt", "<")):
        if op in mods:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SigmaError(f"{field}|{op} takes a number")
            return f"{field}:{sym}{value}"
    if isinstance(value, bool):
        value = "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{field}:{value}"
    if not isinstance(value, str):
        raise SigmaError(f"{field}: unsupported value type {type(value).__name__}")
    if value == "":
        raise SigmaError(f"{field}: an empty value is not supported (Graylog cannot tell empty from missing)")
    if "re" in mods:
        if field in TEXT_FIELDS:
            raise SigmaError(f"{field}|re: a regular expression cannot match the analyzed {field} field")
        return f"{field}:/{_lucene_regex(value, field)}/"
    if field in TEXT_FIELDS:
        if "startswith" in mods or "endswith" in mods or "contains" not in mods:
            raise SigmaError(f"{field}: on analyzed text only |contains (or keywords) can be matched exactly")
        # analyzed text: a regex sees single tokens only, so match the words as a phrase
        inner = "".join(t if k == "lit" else "\x00" for k, t in _glob_parts(value.strip("*")))
        if not inner or "\x00" in inner:
            raise SigmaError(f"{field}: wildcards inside a text value are not supported")
        return f"{field}:{_phrase(inner)}"
    parts = _glob_parts(value)
    if "contains" in mods:
        parts = [("star", "*")] + parts + [("star", "*")]
    elif "startswith" in mods:
        parts = parts + [("star", "*")]
    elif "endswith" in mods:
        parts = [("star", "*")] + parts
    return _glob_to_query(field, parts)


def _field_item(key: str, value, field_map: dict) -> str:
    name, *mods = key.split("|")
    mods = [m.lower() for m in mods]
    bad = [m for m in mods if m in _UNSUPPORTED or m not in {"contains", "startswith", "endswith", "all", "re", "exists",
                                                           "cased", "gt", "gte", "lt", "lte"}]
    if bad:
        raise SigmaError(f"{key}: modifier {bad[0]!r} is not supported")
    field = field_map.get(name, _GELF_FIELDS.get(name, name))
    if not _FIELD.match(field):
        raise SigmaError(f"{key}: {field!r} is not a usable Graylog field name (map it)")
    values = value if isinstance(value, list) else [value]
    if not values:
        raise SigmaError(f"{key}: empty value list")
    qs = [_value_query(field, v, mods) for v in values]
    if len(qs) == 1:
        return qs[0]
    return "(" + (" AND " if "all" in mods else " OR ").join(qs) + ")"


def _keyword(v) -> str:
    if not isinstance(v, (str, int, float)) or isinstance(v, bool):
        raise SigmaError("keywords must be text")
    s = str(v)
    inner = s.strip("*")
    if not inner or any(k != "lit" for k, _ in _glob_parts(inner)):
        raise SigmaError(f"keyword {s!r}: wildcards inside a keyword are not supported")
    return "message:" + _phrase(inner)


def selection_query(sel, field_map: dict) -> str:
    if isinstance(sel, dict):
        if not sel:
            raise SigmaError("empty selection")
        parts = [_field_item(str(k), v, field_map) for k, v in sel.items()]
        return parts[0] if len(parts) == 1 else "(" + " AND ".join(parts) + ")"
    if isinstance(sel, list):
        if not sel:
            raise SigmaError("empty selection")
        if all(isinstance(x, dict) for x in sel):
            parts = [selection_query(x, field_map) for x in sel]
        elif all(not isinstance(x, (dict, list)) for x in sel):
            parts = [_keyword(x) for x in sel]
        else:
            raise SigmaError("a selection mixes keywords and field maps")
        return parts[0] if len(parts) == 1 else "(" + " OR ".join(parts) + ")"
    if isinstance(sel, (str, int, float)) and not isinstance(sel, bool):
        return _keyword(sel)
    raise SigmaError("unsupported selection")


# --- condition ------------------------------------------------------------------

_TOKEN = re.compile(r"\s*(\(|\)|[A-Za-z0-9_*.\-]+)")


def _tokens(cond: str) -> list[str]:
    if "|" in cond:
        raise SigmaError("aggregation conditions (| count() ...) are not supported; use the rule's threshold")
    out, pos = [], 0
    cond = cond.strip()
    while pos < len(cond):
        m = _TOKEN.match(cond, pos)
        if not m:
            raise SigmaError(f"cannot read the condition near {cond[pos:pos + 20]!r}")
        out.append(m.group(1))
        pos = m.end()
    return out


class _Cond:
    def __init__(self, tokens: list[str], sels: dict[str, str]):
        self.t, self.i, self.sels = tokens, 0, sels

    def peek(self):
        return self.t[self.i].lower() if self.i < len(self.t) else None

    def take(self):
        if self.i >= len(self.t):
            raise SigmaError("the condition ends too early")
        tok = self.t[self.i]
        self.i += 1
        return tok

    def expr(self) -> str:
        parts = [self.term()]
        while self.peek() == "or":
            self.take()
            parts.append(self.term())
        return parts[0] if len(parts) == 1 else "(" + " OR ".join(parts) + ")"

    def term(self) -> str:
        parts = [self.factor()]
        while self.peek() == "and":
            self.take()
            parts.append(self.factor())
        return parts[0] if len(parts) == 1 else "(" + " AND ".join(parts) + ")"

    def factor(self) -> str:
        tok = self.peek()
        if tok is None:
            raise SigmaError("the condition ends too early")
        if tok == "not":
            self.take()
            return neg(self.factor())
        if tok == "(":
            self.take()
            e = self.expr()
            if self.peek() != ")":
                raise SigmaError("a parenthesis is not closed in the condition")
            self.take()
            return f"({e})" if not e.startswith("(") else e
        if tok in ("1", "any", "all"):
            self.take()
            if self.peek() != "of":
                raise SigmaError(f"expected 'of' after {tok!r}")
            self.take()
            pat = self.take()
            names = ([n for n in self.sels if not n.startswith("_")] if pat.lower() == "them"
                     else [n for n in self.sels if fnmatch.fnmatchcase(n, pat)])
            if not names:
                raise SigmaError(f"no selection matches {pat!r}")
            qs = [self.sels[n] for n in names]
            if len(qs) == 1:
                return qs[0]
            return "(" + (" AND " if tok == "all" else " OR ").join(qs) + ")"
        if tok in ("and", "or", ")", "of", "near"):
            raise SigmaError(f"unexpected {tok!r} in the condition")
        name = self.take()
        if name not in self.sels:
            raise SigmaError(f"the condition names {name!r}, which is not a selection")
        return self.sels[name]


def convert(rule: dict, field_map: dict | None = None) -> str:
    """A parsed rule -> one Graylog query. Raises SigmaError with the reason."""
    field_map = field_map or {}
    det = rule["detection"]
    sels = {}
    for name, sel in det.items():
        if name in ("condition", "timeframe"):
            continue
        sels[str(name)] = selection_query(sel, field_map)
    conds = det["condition"]
    conds = conds if isinstance(conds, list) else [conds]
    out = []
    for c in conds:
        if not isinstance(c, str):
            raise SigmaError("the condition must be text")
        p = _Cond(_tokens(c), sels)
        q = p.expr()
        if p.i != len(p.t):
            raise SigmaError(f"cannot read the condition after {' '.join(p.t[:p.i])!r}")
        out.append(q)
    return out[0] if len(out) == 1 else "(" + " OR ".join(out) + ")"


def parse_field_map(text: str) -> tuple[dict, list[str]]:
    """Lines `SigmaField=graylog_field` (# comments) -> (map, errors)."""
    out, errors = {}, []
    for n, ln in enumerate(str(text or "").splitlines(), 1):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if "=" not in ln:
            errors.append(f"line {n}: expected SigmaField=graylog_field")
            continue
        a, b = (x.strip() for x in ln.split("=", 1))
        if not _FIELD.match(a) or not _FIELD.match(b):
            errors.append(f"line {n}: field names may use letters, digits and _ . @ -")
            continue
        out[a] = b
    return out, errors
