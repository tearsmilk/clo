#!/usr/bin/env bash
# Build Aseprite headless (batch mode + Lua scripting, no window, no Skia) for aseprite_tools.py.
# Aseprite's EULA: you may compile it for your own use; do not redistribute the binary.
#   bash scripts/build_aseprite.sh [DIR]      -> DIR/build/bin/aseprite   (default DIR=./aseprite_build)
# Needs: git, cmake, ninja, a C++17 compiler, X11 dev headers (laf links X11 even without a window):
#   apt-get install -y libxcursor-dev libxi-dev libxrandr-dev libgl1-mesa-dev libfontconfig1-dev
# Sandboxes that block GitHub archive downloads but allow git: libjpeg-turbo is cloned with git and the
# ExternalProject is pointed at it (the only dependency the build downloads as an archive).
set -euo pipefail
DIR="$(mkdir -p "${1:-./aseprite_build}" && cd "${1:-./aseprite_build}" && pwd)"
cd "$DIR"
[ -d src ] || git clone --recursive --shallow-submodules --depth 1 https://github.com/aseprite/aseprite.git src
if ! curl -fsSI https://codeload.github.com/libjpeg-turbo/libjpeg-turbo/zip/refs/tags/3.0.2 >/dev/null 2>&1; then
  [ -d libjpeg-turbo ] || git clone -q --depth 1 --branch 3.0.2 https://github.com/libjpeg-turbo/libjpeg-turbo.git
  python3 - "$DIR" <<'EOF'
import re, sys
d = sys.argv[1]
p = f'{d}/src/cmake/FindJpegTurbo.cmake'
s = open(p).read()
s = re.sub(r'    URL https://\S+\n    URL_HASH \S+\n', f'    SOURCE_DIR {d}/libjpeg-turbo\n', s)
s = s.replace('    DOWNLOAD_EXTRACT_TIMESTAMP ON\n', '')
open(p, 'w').write(s)
EOF
fi
mkdir -p build && cd build
cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DLAF_BACKEND=none \
      -DENABLE_NEWS=off -DENABLE_UPDATER=off -DENABLE_WEBSOCKET=off -DENABLE_CCACHE=off -DENABLE_TESTS=off ../src
ninja aseprite
echo "built: $(pwd)/bin/aseprite   ->   export ASEPRITE=$(pwd)/bin/aseprite"
