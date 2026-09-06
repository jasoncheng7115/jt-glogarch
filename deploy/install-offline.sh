#!/bin/bash
# jt-glogarch OFFLINE (air-gapped) FIRST-INSTALL script
#
# Until v1.14.5 there was no air-gapped install path at all: upgrade-offline.sh
# aborts when /opt/jt-glogarch/glogarch is absent, and install.sh always reached
# for PyPI. A brand-new customer on an isolated network had nothing to run.
#
# This script is the missing half. It stages the bundle's source tree into
# /opt/jt-glogarch and then hands over to the SAME install.sh every online
# install uses, in --offline mode — so the two paths cannot drift apart.
#
#     tar xzf jt-glogarch-<ver>-offline.tar.gz
#     cd jt-glogarch-<ver>-offline
#     sudo bash install-offline.sh
#
# Requires on the target: Python 3.10+ (same major.minor as the build host) and
# openssl. Nothing else — pip never touches the network.
#
# Already installed? Use upgrade-offline.sh instead; this script refuses to run
# over an existing install so it can never clobber a live config or database.

set -e
INSTALL_DIR="/opt/jt-glogarch"
BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== jt-glogarch OFFLINE First Install ==="
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: must run as root (sudo)"
    exit 1
fi

if [ ! -f "$BUNDLE_DIR/src/pyproject.toml" ] || [ ! -d "$BUNDLE_DIR/src/glogarch" ]; then
    echo "Error: $BUNDLE_DIR does not look like an extracted offline bundle"
    echo "       (expected src/glogarch and src/pyproject.toml)."
    exit 1
fi
if ! ls "$BUNDLE_DIR"/jt_glogarch-*.whl >/dev/null 2>&1; then
    echo "Error: no jt_glogarch-*.whl in $BUNDLE_DIR."
    exit 1
fi

# Refuse to run over an existing install — that is upgrade-offline.sh's job,
# and only it backs up the database first.
if [ -d "$INSTALL_DIR/glogarch" ]; then
    echo "An existing install was found at $INSTALL_DIR."
    echo "Use the UPGRADE path instead, which backs up the database first:"
    echo ""
    echo "    sudo bash $BUNDLE_DIR/upgrade-offline.sh"
    exit 1
fi
# A config.yaml or database with no source tree means a half-removed install.
# Stop rather than silently adopting state we did not create.
for leftover in "$INSTALL_DIR/config.yaml" "$INSTALL_DIR/jt-glogarch.db"; do
    if [ -e "$leftover" ]; then
        echo "Error: $leftover exists but $INSTALL_DIR/glogarch does not."
        echo "       That is a partial/removed install. Move it aside and re-run,"
        echo "       or restore the install and use upgrade-offline.sh."
        exit 1
    fi
done

# Python check up front — a clear message beats a pip traceback.
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found. Install Python 3.10+ from your distro media."
    exit 1
fi
PYVER=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
BUNDLE_PY=$(ls "$BUNDLE_DIR"/*.whl 2>/dev/null | grep -oE 'cp3[0-9]+' | head -1 | sed 's/cp3/3./')
echo "Target Python: $PYVER"
if [ -n "$BUNDLE_PY" ] && [ "$BUNDLE_PY" != "$PYVER" ]; then
    echo ""
    echo "Error: this bundle carries compiled wheels for Python $BUNDLE_PY, but this"
    echo "       host runs Python $PYVER. Compiled wheels (uvloop, httptools,"
    echo "       pydantic-core, …) will not load across minor versions."
    echo "       Rebuild the bundle on a host running Python $PYVER."
    exit 1
fi

# --- Stage the source tree into /opt (what the CLI imports, and where
#     install.sh reads deploy/report-deps.sh + deploy/tls-env.sh from). ---
echo ""
echo "Staging source tree into $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r "$BUNDLE_DIR/src/glogarch" "$INSTALL_DIR/"
cp "$BUNDLE_DIR/src/pyproject.toml" "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/deploy"
for f in install.sh upgrade-offline.sh report-deps.sh tls-env.sh uninstall.sh \
         jt-glogarch.service config.yaml.example; do
    [ -f "$BUNDLE_DIR/deploy/$f" ] && cp "$BUNDLE_DIR/deploy/$f" "$INSTALL_DIR/deploy/"
done
# report-deps.sh also sits at the bundle root (upgrade-offline.sh sources it there).
[ -f "$BUNDLE_DIR/report-deps.sh" ] && cp "$BUNDLE_DIR/report-deps.sh" "$INSTALL_DIR/deploy/"
find "$INSTALL_DIR/glogarch" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
echo "  staged."

if [ ! -f "$INSTALL_DIR/deploy/install.sh" ]; then
    echo "Error: deploy/install.sh missing from the bundle — rebuild it with"
    echo "       scripts/build-offline-bundle.sh from v1.14.5 or later."
    exit 1
fi

# --- Hand over to the shared installer in offline mode. -------------------
echo ""
bash "$INSTALL_DIR/deploy/install.sh" --offline "$BUNDLE_DIR"

echo ""
echo "=== Offline install finished ==="
echo "  Next: systemctl enable --now jt-glogarch"
echo "        then open https://$(hostname):8990/ — it redirects to the"
echo "        first-run setup wizard at /setup."
