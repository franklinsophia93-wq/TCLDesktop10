#!/usr/bin/env bash
# Build reproduzivel do TCL Desktop 10 com runtime de execucao Wine e Box64.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UPSTREAM="https://github.com/brunodev85/winlator-app.git"
COMMIT="8077f374ef2d54127b088de9e8cd7b4af14d9c8b"
WORKDIR="${WORKDIR:-$(mktemp -d)}"
mkdir -p "$WORKDIR"
git clone --no-checkout "$UPSTREAM" "$WORKDIR/winlator-app"
git -C "$WORKDIR/winlator-app" checkout --detach "$COMMIT"
python3 "$ROOT/integration/winlator-overlay/prepare.py" "$WORKDIR/winlator-app"

(cd "$WORKDIR/winlator-app" && chmod +x gradlew && ./gradlew --no-daemon :app:assembleDebug)
APK="$WORKDIR/winlator-app/app/build/outputs/apk/debug/app-debug.apk"
test -s "$APK" || { echo "FALHA: APK nao produzido" >&2; exit 1; }
unzip -tqq "$APK"
unzip -Z1 "$APK" > "$WORKDIR/apk-entries.txt"
grep -Fxq 'AndroidManifest.xml' "$WORKDIR/apk-entries.txt"
grep -Fxq 'classes.dex' "$WORKDIR/apk-entries.txt"
grep -Fxq 'assets/rootfs.tzst' "$WORKDIR/apk-entries.txt"
grep -Eq '^lib/arm64-v8a/[^/]+\.so$' "$WORKDIR/apk-entries.txt"
OUT="$ROOT/app/build/outputs/apk/debug/TCLDesktop10-debug.apk"
mkdir -p "$(dirname "$OUT")"
cp "$APK" "$OUT"
echo "APK compilado: $OUT (nao validado no TCL fisico)."
