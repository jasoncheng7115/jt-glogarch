#!/bin/bash
# Build a SELF-CONTAINED offline upgrade bundle for air-gapped customer sites.
#
# Run this on an INTERNET-CONNECTED machine whose Python major.minor matches the
# target host (both must be CPython 3.10 on linux x86_64 for the compiled wheels
# — uvloop/httptools/etc. — to be compatible). It produces:
#
#     dist/jt-glogarch-<ver>-offline.tar.gz
#
# containing: the jt_glogarch wheel + EVERY runtime dependency wheel +
# upgrade-offline.sh. Copy that single tarball to the air-gapped host and follow
# deploy/upgrade-offline.sh. pip on the target never touches the network.
#
# Usage:  bash scripts/build-offline-bundle.sh
set -e
cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

VERSION=$(python3 -c 'import glogarch; print(glogarch.__version__)')
BUNDLE_NAME="jt-glogarch-${VERSION}-offline"
STAGE="dist/${BUNDLE_NAME}"

echo "=== Building offline bundle for jt-glogarch v${VERSION} ==="
PYVER=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
echo "Build Python: ${PYVER} on $(uname -srm)"
echo "  NOTE: the target host must run the same Python ${PYVER} on the same"
echo "        platform for the compiled dependency wheels to load."
echo ""

rm -rf "$STAGE"
mkdir -p "$STAGE"

# 1. Build the jt-glogarch wheel (bundles templates/static via package-data).
echo "[1/4] Building jt_glogarch wheel..."
python3 -m pip wheel --no-deps --no-build-isolation -w "$STAGE" "$REPO_ROOT" 2>&1 | tail -2

# 2. Download EVERY runtime dependency as a wheel (full transitive closure,
#    including the uvicorn[standard] extras). Excludes the optional [report]
#    extra (Playwright/Chromium) — that is installed separately where wanted.
#    Deps are read from the freshly-built wheel's METADATA (Requires-Dist) so we
#    avoid pip's dynamic-version "UNKNOWN" problem with local source trees.
echo "[2/4] Downloading runtime dependency wheels..."
BUILT_WHEEL=$(ls "$STAGE"/jt_glogarch-*.whl | head -1)
python3 - "$BUILT_WHEEL" > "$STAGE/requirements.txt" << 'PYEOF'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
meta = next(n for n in z.namelist() if n.endswith("METADATA"))
for line in z.read(meta).decode().splitlines():
    if line.startswith("Requires-Dist:"):
        req = line.split(":", 1)[1].strip()
        if "extra ==" in req:      # skip optional [report]/[dev] extras
            continue
        print(req)
PYEOF
echo "  runtime deps:"; sed 's/^/    /' "$STAGE/requirements.txt"
python3 -m pip download --dest "$STAGE" -r "$STAGE/requirements.txt" 2>&1 | tail -3

# 2b. PDF Reports [report] extra — bundle the Playwright wheel + its deps so the
#     offline target can `pip install playwright` without the network.
echo "[2b/4] Downloading PDF Reports wheels (Playwright + PyMuPDF + Pillow)..."
python3 -m pip download --dest "$STAGE" playwright pymupdf pillow 2>&1 | tail -2 \
    || echo "  WARNING: could not download report wheels — offline bundle will lack PDF Reports."

# 2c. Chromium browser + a CJK font, so offline hosts render Chinese PDFs.
#     Chromium goes into a temp browsers path, then tarred; report-deps.sh on
#     the target extracts it into /opt/jt-glogarch/.playwright.
echo "[2c/4] Bundling Chromium browser + CJK font..."
BROWSERS_TMP="$(mktemp -d)"
if PLAYWRIGHT_BROWSERS_PATH="$BROWSERS_TMP" python3 -m playwright install chromium >/dev/null 2>&1; then
    tar czf "$STAGE/chromium-browser.tar.gz" -C "$BROWSERS_TMP" . 2>/dev/null
    echo "  Chromium bundled ($(du -h "$STAGE/chromium-browser.tar.gz" | cut -f1))."
else
    echo "  WARNING: 'playwright install chromium' failed on build host — bundle lacks the browser."
fi
rm -rf "$BROWSERS_TMP"
mkdir -p "$STAGE/fonts"
CJK_FONT=$(fc-list :lang=zh 2>/dev/null | grep -oiE "/[^:]*(wqy-zenhei\.ttc|NotoSansCJK[^:]*\.(ttc|otf))" | head -1)
if [ -n "$CJK_FONT" ] && [ -f "$CJK_FONT" ]; then
    cp "$CJK_FONT" "$STAGE/fonts/"
    echo "  CJK font bundled: $(basename "$CJK_FONT")."
else
    echo "  WARNING: no CJK font on build host — apt install fonts-wqy-zenhei and rebuild for Chinese PDFs."
fi
# Ship report-deps.sh alongside upgrade-offline.sh (used in offline mode).
for p in "$REPO_ROOT/deploy/report-deps.sh" "$REPO_ROOT/github/deploy/report-deps.sh"; do
    [ -f "$p" ] && cp "$p" "$STAGE/report-deps.sh" && break
done

# 3. Include the source tree + upgrade script. The source is synced to
#    /opt/jt-glogarch on the target so that `python -m glogarch` run from /opt
#    (the CLI) uses the new code too — the wheel only updates dist-packages
#    (which the systemd service uses). This mirrors the online git-pull, which
#    updates the /opt source in place.
echo "[3/4] Adding source tree + upgrade-offline.sh..."
mkdir -p "$STAGE/src"
cp -r "$REPO_ROOT/glogarch" "$STAGE/src/"
cp "$REPO_ROOT/pyproject.toml" "$STAGE/src/"
find "$STAGE/src" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE/src" -name '*.pyc' -delete 2>/dev/null || true
# The upgrade script lives at deploy/ in a shipped checkout, or github/deploy/
# in the dev working tree — accept either.
UPGRADE_SH=""
for p in "$REPO_ROOT/deploy/upgrade-offline.sh" "$REPO_ROOT/github/deploy/upgrade-offline.sh"; do
    [ -f "$p" ] && UPGRADE_SH="$p" && break
done
if [ -z "$UPGRADE_SH" ]; then
    echo "Error: deploy/upgrade-offline.sh not found under $REPO_ROOT"; exit 1
fi
cp "$UPGRADE_SH" "$STAGE/upgrade-offline.sh"
chmod +x "$STAGE/upgrade-offline.sh"
cat > "$STAGE/README-OFFLINE.txt" << EOF
jt-glogarch ${VERSION} — OFFLINE upgrade bundle
================================================
On the air-gapped target host (as root):

  tar xzf ${BUNDLE_NAME}.tar.gz
  cd ${BUNDLE_NAME}
  sudo bash upgrade-offline.sh

Requires: an existing jt-glogarch install and Python ${PYVER} on the same
platform this bundle was built on. pip never touches the network.
Wheels included: $(ls "$STAGE"/*.whl 2>/dev/null | wc -l)

PDF Reports (beta): this bundle ships the Playwright wheel, the Chromium
browser ($([ -f "$STAGE/chromium-browser.tar.gz" ] && echo "included" || echo "MISSING")) and a CJK font
($([ -f "$STAGE"/fonts/* ] 2>/dev/null && echo "included" || echo "MISSING")). upgrade-offline.sh installs all three.
  NOTE: Chromium needs OS shared libraries (libnss3, libatk1.0, libxkbcommon,
  libgbm, libasound2, …). On a fully air-gapped host install these from your
  distro's install media BEFORE running reports; the bundle cannot carry .debs.
  Verify after upgrade:  sudo -u jt-glogarch env PLAYWRIGHT_BROWSERS_PATH=/opt/jt-glogarch/.playwright \\
                           python3 -m playwright install --dry-run chromium
EOF

# 4. Tar it up.
echo "[4/4] Packaging tarball..."
tar czf "dist/${BUNDLE_NAME}.tar.gz" -C dist "${BUNDLE_NAME}"
WHEELS=$(ls "$STAGE"/*.whl 2>/dev/null | wc -l)
SIZE=$(du -h "dist/${BUNDLE_NAME}.tar.gz" | cut -f1)

echo ""
echo "=== Bundle ready ==="
echo "  dist/${BUNDLE_NAME}.tar.gz  (${SIZE}, ${WHEELS} wheels)"
echo "  Copy it to the air-gapped host and run upgrade-offline.sh."
