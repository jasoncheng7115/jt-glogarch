# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Jason Cheng (Jason Tools)
"""Graylog query syntax for the AI: the rules it is told, and the mistakes
refused before a query reaches Graylog.

Owner, 2026-11-24 (with a screenshot of the model writing `source:/.*mail.*/i`):
"你會給 system prompt … 讓它可以更精準的下 graylog 語法 … graylog open 跟
enterprise 有些語法沒支援的差異 也要讓他知道".

Everything here was MEASURED on Graylog Open 7.2.2 + OpenSearch 2.19 with 3.9M
real messages from .36's archives (2026-11-24), through the same REST search
the tools use. Where Graylog's own documentation says otherwise, the
measurement wins and the difference is noted:
  * docs: "Use regex with case-insensitive flag" -> `source:/mail.*/i` returned
    599,559 = `source:/mail.*/ OR i` (582,711 + the word "i"): the flag is read
    as another search term, the count is silently wrong.
  * docs: lowercase operators "cause this error" -> that is the search page's
    validator; the REST search runs them as words:
    `source:mg1 and source:mail2` = 151,622 (the right answer is 0).
  * docs: "case-sensitive by default" -> only for keyword fields
    (user_name:root 21,218, user_name:ROOT 0); `message` (standard analyzer)
    and `source` (Graylog's analyzer_keyword: whole value, lower-cased) match
    any case.
  * a space inside `field:( )` means OR on `message` (71,278 = OR) but makes
    ONE token on `source` / keyword fields (`source:(mail mg1)` = 0).
  * `a OR NOT b` is read as `a AND NOT b` (17,038 = root AND NOT mail).
  * `$name$` (Enterprise search parameters) on Open: searched as text, 0 hits,
    no error.
  * an unquoted CIDR is a parse error (HTTP 500); quoted on a keyword field it
    matches nothing; addresses here are keyword fields.
  * leading wildcard: HTTP 500 (allow_leading_wildcard_searches is off).
"""
from __future__ import annotations

import re

# What the model is told (English: the system prompt is English, answers follow
# the page language). Kept short: the owner's model is a small quantised one.
GUIDE = """Graylog query rules (Graylog Open; measured, follow them exactly):
- AND, OR, NOT must be UPPER CASE. Lower-case and/or/not are searched as words and silently change the count.
- Inside field:( ) always write the operator: user_name:(root OR admin). A space there is NOT OR on most fields (it returned 0).
- "a OR NOT b" is read as "a AND NOT b"; write a OR (*:* AND NOT b).
- Keyword fields (user_name, event_outcome, source_ip, alert_signature, most fields) are case-sensitive and match the whole value: user_name:root, not ROOT; prefix with field:roo*; one character with ?.
- message and full_message match words in any case; quote a phrase: message:"session opened". Regex on message matches single words only.
- source (the sending host) matches the WHOLE host name in any case, never part of it: source:mail matches "mail" but not "mail.example.com"; use source:mail* for both. When unsure of host names, run top_values on source first.
- A query must not start a term with * or ? (Graylog refuses it): no source:*mail, no *error*.
- Regex is /pattern/ on one field and takes no flags: /x/i searches /x/ OR the word i. For case use [Mm]ail. Prefer a prefix wildcard to regex.
- Ranges: field:[400 TO 499], field:>=500, {} exclusive. On numeric fields only; addresses are text, so a range of IPs compares as text and is wrong.
- Addresses: quote them: source_ip:"203.0.113.9". CIDR (x.x.x.x/nn) works only on fields of type ip; on this kind of site addresses are keyword fields, so for a /24 use source_ip:203.0.113.* instead.
- Field exists: _exists_:user_name ; missing: NOT _exists_:user_name.
- Escape these characters in an unquoted value with a backslash: + - ! ( ) { } [ ] ^ " ~ * ? : \\ /
- Everything: * (never an empty query). Time ranges are tool arguments, not part of the query.
- Graylog Enterprise only, NOT on this Graylog Open: search parameters $name$ (searched as plain text, no hits), search filters, Data Lake / archive search, Illuminate content. jt-glogarch's own archives are searched in its Archives page, not through these tools.
- A count of 0 is a real answer only if the query is right: check the field name with list_fields and the values with top_values before saying "none"."""

_QUOTED = re.compile(r'"(?:\\.|[^"\\])*"')
# a regex term: /.../ not preceded by a word character (a path like a/b is not one)
_REGEX = re.compile(r'(?<![\w\\])/(?:\\.|[^/\\])+/([A-Za-z]*)')
_LOWER_OP = re.compile(r'(?:^|[\s(])(and|or|not)(?=[\s(])')
_PARAM = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*\$')
_LEADING = re.compile(r'(?:^|[\s(:])[*?](?![\s)]|$)')
_CIDR = re.compile(r'(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}\\?/\d{1,2}\b')
_GROUP = re.compile(r'([A-Za-z0-9_.@-]+):\(([^()]*)\)')
_OR_NOT = re.compile(r'\bOR\s+NOT\b')
_EVERYTHING = re.compile(r'\s*(\*|\*:\*)?\s*')


def query_problem(q: str) -> str | None:
    """Why this query would return a wrong count (or fail), or None.

    Only forms MEASURED to go wrong are refused; the message says how to write
    it, so the model can retry. Nothing here rewrites a query: a rewritten
    query would not be the one shown to the user."""
    if not isinstance(q, str) or _EVERYTHING.fullmatch(q):
        return None
    if _PARAM.search(q):
        return ("query: $name$ is a Graylog Enterprise search parameter; Graylog Open searches it as plain text "
                "and finds nothing. Put the value itself in the query.")
    bare = _QUOTED.sub('""', q)
    for m in _REGEX.finditer(bare):
        if m.group(1):
            return (f"query: Graylog regex takes no flags: /…/{m.group(1)} searches the regex OR the word "
                    f"\"{m.group(1)}\". Remove the flag; keyword fields are case-sensitive, so write the case "
                    "as stored or use a class like [Mm]ail.")
    bare = _REGEX.sub("R", bare)
    bare = re.sub(r"(?<![\w])\*:\*", "ALL", bare)        # "everything" is not a leading wildcard
    m = _LOWER_OP.search(bare)
    if m:
        return (f"query: \"{m.group(1)}\" in lower case is searched as a word, not an operator. Write "
                f"{m.group(1).upper()} in upper case (to search the word itself, quote it: \"{m.group(1)}\").")
    if _LEADING.search(bare):
        return ("query: Graylog does not allow a term that starts with * or ?; search a prefix instead, "
                "e.g. source:web* or user_name:admin*, or find the values with top_values first.")
    if _CIDR.search(bare):
        return ("query: an unquoted address/prefix like 10.0.0.0/8 is a syntax error. CIDR works only on fields "
                "of type ip; for an address field stored as text use a prefix wildcard such as "
                "source_ip:10.0.0.* (one /24), or list the addresses with OR.")
    for g in _GROUP.finditer(bare):
        inner = g.group(2).strip()
        terms = inner.split()
        if len(terms) > 1 and not any(t in ("AND", "OR", "NOT") for t in terms) and not inner.startswith('"'):
            return (f"query: write the operator inside {g.group(1)}:( ): {g.group(1)}:({' OR '.join(terms)}) "
                    "or with AND. Without it the result depends on the field type (it returned 0 on host "
                    "and account fields).")
    if _OR_NOT.search(bare):
        return ("query: \"a OR NOT b\" is read as \"a AND NOT b\". Write a OR (*:* AND NOT b).")
    return None
