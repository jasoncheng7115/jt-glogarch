#!/bin/bash
# jt-glogarch — PDF Reports runtime dependencies (Chromium + CJK font)
# Author: Jason Cheng (Jason Tools)
#
# The PDF Reports feature renders HTML via a headless Chromium (Playwright) and
# needs a CJK font so Traditional-Chinese reports don't come out as blank tofu
# boxes. The `playwright` Python package itself is installed by pip (the
# [report] extra); this helper installs the two HOST-level pieces pip can't:
#
#   1. The Chromium browser binary — into a SHARED path ($INSTALL_DIR/.playwright)
#      that the unprivileged service user (jt-glogarch) can read. (The default
#      ~/.cache/ms-playwright lands in root's home, unreadable by the service.)
#   2. A CJK font (WenQuanYi Zen Hei).
#
# Everything here is BEST-EFFORT: core archiving works without PDF reports, so a
# failure warns loudly but never aborts the install/upgrade.
#
# Sourced by install.sh / upgrade.sh (online) and upgrade-offline.sh (offline).
#   install_report_deps <PIP_FLAGS> [BUNDLE_DIR]
# When BUNDLE_DIR is given (offline), Chromium + font come from the bundle
# instead of the network; BUNDLE_DIR/chromium-*.tar.gz and BUNDLE_DIR/fonts/*.

install_report_deps() {
    local pip_flags="$1"
    local bundle_dir="$2"
    local service_user="jt-glogarch"
    local install_dir="/opt/jt-glogarch"
    local browsers_dir="$install_dir/.playwright"

    echo ""
    echo "=== PDF Reports runtime deps (Chromium + CJK font) ==="

    # --- 1. CJK font (so Chinese reports aren't blank boxes) ---
    if fc-list :lang=zh 2>/dev/null | grep -qiE "wenquanyi|noto sans cjk|noto.*cjk"; then
        echo "  [font] CJK font already present — skip."
    elif [ -n "$bundle_dir" ]; then
        local font
        font=$(ls "$bundle_dir"/fonts/*.ttc "$bundle_dir"/fonts/*.ttf 2>/dev/null | head -1)
        if [ -n "$font" ]; then
            mkdir -p /usr/share/fonts/truetype/jt-glogarch
            cp "$font" /usr/share/fonts/truetype/jt-glogarch/
            fc-cache -f >/dev/null 2>&1 || true
            echo "  [font] installed from bundle: $(basename "$font")"
        else
            echo "  [font] ⚠ no bundled CJK font — Chinese PDFs may show blank boxes."
        fi
    elif command -v apt-get >/dev/null 2>&1; then
        if apt-get install -y fonts-wqy-zenhei >/dev/null 2>&1; then
            fc-cache -f >/dev/null 2>&1 || true
            echo "  [font] installed fonts-wqy-zenhei via apt."
        else
            echo "  [font] ⚠ could not apt-install fonts-wqy-zenhei — install a CJK font manually."
        fi
    else
        echo "  [font] ⚠ apt-get not found — install a CJK font (e.g. WenQuanYi) manually."
    fi

    # --- 2. Chromium browser into the shared, service-readable path ---
    mkdir -p "$browsers_dir"
    if ls -d "$browsers_dir"/chromium-*/ >/dev/null 2>&1; then
        echo "  [chromium] already present in $browsers_dir — skip."
    elif [ -n "$bundle_dir" ]; then
        local tb
        tb=$(ls "$bundle_dir"/chromium-*.tar.gz 2>/dev/null | head -1)
        if [ -n "$tb" ]; then
            tar xzf "$tb" -C "$browsers_dir"
            echo "  [chromium] extracted from bundle: $(basename "$tb")"
        else
            echo "  [chromium] ⚠ no bundled Chromium — PDF rendering unavailable offline."
        fi
    else
        if PLAYWRIGHT_BROWSERS_PATH="$browsers_dir" python3 -m playwright install chromium >/dev/null 2>&1; then
            echo "  [chromium] installed via playwright."
        else
            echo "  [chromium] ⚠ 'playwright install chromium' failed — PDF rendering unavailable."
            echo "             (is the [report] extra installed? pip install '$install_dir'[report])"
        fi
        # Chromium's shared-library prerequisites (libnss3, libatk, …). Needs apt.
        if command -v apt-get >/dev/null 2>&1; then
            python3 -m playwright install-deps chromium >/dev/null 2>&1 \
                || echo "  [chromium] (note: install-deps for OS libraries failed — see 'playwright install-deps')"
        fi
    fi

    # The service reads Chromium as jt-glogarch; hand ownership over.
    chown -R "$service_user":"$service_user" "$browsers_dir" 2>/dev/null || true
    echo "=== Reports deps step complete ==="
}
