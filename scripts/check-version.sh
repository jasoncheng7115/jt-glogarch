#!/bin/bash
# Sanity check: make sure the single source of truth for the version
# (glogarch/__init__.py::__version__) is NOT accidentally duplicated
# anywhere else in the repo. Run this before every release.
#
# Usage:   ./scripts/check-version.sh
# Exit 0:  version appears only in the canonical source (plus CHANGELOG entries)
# Exit 1:  version is hardcoded somewhere else — fix it

set -e
cd "$(dirname "$0")/.."

VER=$(python3 -c 'import glogarch; print(glogarch.__version__)')
echo "Canonical version: $VER"

# Allowed locations (glob patterns):
#   - glogarch/__init__.py          → source of truth
#   - github/CHANGELOG*.md          → historic version entries
#   - github/glogarch/__init__.py → mirror of source of truth
#   - contrib/                    → the parsing assets (never shipped; their sample
#                                   logs carry other products' versions, e.g. nginx/1.24.0)
# Anchored: a version inside a longer number is not one (an SVG path in app.js
# holds "-1.25.077", which an unanchored 1.25.0 matched).
BAD=$(grep -rnE "(^|[^0-9.])v?${VER//./\\.}([^0-9]|$)" \
    --include='*.py' \
    --include='*.html' \
    --include='*.js' \
    --include='*.css' \
    --include='*.toml' \
    --exclude-dir=zap --exclude-dir=.playwright --exclude-dir=.git \
    --exclude-dir=contrib \
    . 2>/dev/null \
    | grep -v 'glogarch/__init__.py' \
    | grep -v 'github/glogarch/__init__.py' \
    | grep -v '__pycache__' || true)

if [ -n "$BAD" ]; then
    echo ""
    echo "FAIL: version '$VER' is hardcoded outside the canonical source:"
    echo "$BAD"
    echo ""
    echo "Fix: replace hardcoded version with the appropriate runtime read:"
    echo "  - Python: from glogarch import __version__"
    echo "  - Jinja2: {{ version }}  (injected by web/routes/pages.py::_render)"
    echo "  - JavaScript: fetch /api/health -> .version"
    exit 1
fi

# README files SHOULD contain the version (title + badge) — assert they match.
README_FAIL=0
for readme in github/README.md github/README-zh_TW.md github/README-ja.md; do
    if ! grep -q "^# jt-glogarch v${VER//./\\.}" "$readme"; then
        echo "FAIL: $readme title is not '# jt-glogarch v${VER}'"
        README_FAIL=1
    fi
    if ! grep -q "version-${VER//./\\.}-green" "$readme"; then
        echo "FAIL: $readme version badge is not v${VER}"
        README_FAIL=1
    fi
done
if [ $README_FAIL -ne 0 ]; then
    exit 1
fi

echo "OK: version '$VER' has exactly one source of truth."
