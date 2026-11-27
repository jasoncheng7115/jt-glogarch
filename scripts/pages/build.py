#!/usr/bin/env python3
"""Build github/docs/{index.html, how.html, pages-i18n.js} and the old-URL redirects.

    python3 scripts/pages/build.py          # writes the files, prints lint problems (exit 1 if any)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lib  # noqa: E402
import common  # noqa: E402
import home  # noqa: E402
import how  # noqa: E402

DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "github", "docs"))

REDIRECT = """<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>jt-glogarch</title>
<meta http-equiv="refresh" content="0; url=index.html?lang={lang}">
<link rel="canonical" href="index.html?lang={lang}">
</head><body><p><a href="index.html?lang={lang}">jt-glogarch</a></p>
<script>location.replace('index.html?lang={lang}' + location.hash)</script>
</body></html>
"""


def main():
    common.register()
    out = {"index.html": home.build(), "how.html": how.build()}
    out["pages-i18n.js"] = lib.js_dict()
    # the pages used to be one file per language: keep those links working
    out["index_zh-TW.html"] = REDIRECT.format(lang="zh-TW")
    out["index_ja.html"] = REDIRECT.format(lang="ja")
    for name, s in out.items():
        with open(os.path.join(DOCS, name), "w", encoding="utf-8") as f:
            f.write(s)
        print(f"{name}: {len(s):,} bytes")
    print(f"texts: {len(lib.TR)}")
    probs = lib.lint()
    for p in probs:
        print("LINT:", p)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
