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
python3 "$ROOT/integration/winlator-overlay/patch_startup.py" "$WORKDIR/winlator-app"
python3 "$ROOT/integration/winlator-overlay/patch_box64_health.py" "$WORKDIR/winlator-app"
python3 "$ROOT/integration/winlator-overlay/patch_runtime_assets.py" "$WORKDIR/winlator-app/app/src/main/assets"

(cd "$WORKDIR/winlator-app" && chmod +x gradlew && ./gradlew --no-daemon :app:assembleDebug)
APK="$WORKDIR/winlator-app/app/build/outputs/apk/debug/app-debug.apk"
test -s "$APK" || { echo "FALHA: APK nao produzido" >&2; exit 1; }
unzip -tqq "$APK"
unzip -Z1 "$APK" > "$WORKDIR/apk-entries.txt"
grep -Fxq 'AndroidManifest.xml' "$WORKDIR/apk-entries.txt"
grep -Fxq 'classes.dex' "$WORKDIR/apk-entries.txt"
grep -Fxq 'assets/rootfs.tzst' "$WORKDIR/apk-entries.txt"
grep -Eq '^lib/arm64-v8a/[^/]+\.so$' "$WORKDIR/apk-entries.txt"
# Garante que o APK contem Box64 com o carregador apontando para NOSSO pacote.
unzip -p "$APK" 'assets/box64/box64-0.4.4.tzst' > "$WORKDIR/box64.tzst"
zstd -dc "$WORKDIR/box64.tzst" | tar -xf - -C "$WORKDIR" './usr/local/bin/box64'
readelf -l "$WORKDIR/usr/local/bin/box64" | grep -Fq '/data/data/com.tclwin10/files/rootfs/lib/ld-linux-aarch64.so.1'
! strings "$WORKDIR/usr/local/bin/box64" | grep -Fq '/data/data/com.winlator'
# A etiqueta Android tambem deve identificar o app correto.
"$ANDROID_HOME/build-tools/35.0.0/aapt" dump badging "$APK" | grep -Fq "package: name='com.tclwin10'"
OUT="$ROOT/app/build/outputs/apk/debug/TCLDesktop10-debug.apk"
mkdir -p "$(dirname "$OUT")"
cp "$APK" "$OUT"
echo "APK compilado: $OUT (nao validado no TCL fisico)."
