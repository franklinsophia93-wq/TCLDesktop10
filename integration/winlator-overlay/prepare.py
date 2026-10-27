#!/usr/bin/env python3
"""Prepara TCL Desktop 10 a partir da fonte completa Winlator (nao simula .exe)."""
import re
import shutil
import sys
from pathlib import Path

APP_ID = "com.tcldesktop.windows"

def patch(source: Path):
    app = source / "app"
    base = app / "src/main"
    java_dir = base / "java/com/winlator"
    must_have = [
        base / "assets/rootfs.tzst",
        base / "assets/container_pattern.tzst",
        base / "assets/box64",
        base / "jniLibs",
        java_dir / "XServerDisplayActivity.java",
        base / "AndroidManifest.xml",
        base / "res/values/strings.xml",
        app / "build.gradle",
        source / "LICENSE",
    ]
    for file in must_have:
        if not file.exists():
            raise RuntimeError(f"Falta componente obrigatorio do runtime Windows: {file}")
    if (base / "assets/rootfs.tzst").stat().st_size < 10_000_000:
        raise RuntimeError("Root filesystem ausente ou incompleto")
    if not any((base / "jniLibs").rglob("*.so")):
        raise RuntimeError("Bibliotecas ARM64 nao encontradas")

    manifest_path = base / "AndroidManifest.xml"
    manifest = manifest_path.read_text(encoding="utf-8")
    pattern = (r'<activity android:name="com\.winlator\.MainActivity"(?P<attrs>[^>]*?)>\s*'
               r'<intent-filter>\s*<action android:name="android\.intent\.action\.MAIN"\s*/>\s*'
               r'<category android:name="android\.intent\.category\.LAUNCHER"\s*/>\s*'
               r'</intent-filter>\s*</activity>')
    match = re.search(pattern, manifest, re.S)
    if not match:
        raise RuntimeError("Manifest nao corresponde ao codigo versionado; compilacao interrompida")
    original = '<activity android:name="com.winlator.MainActivity"' + match.group("attrs") + '/>'
    launcher = """<activity android:name="com.winlator.TclDesktopActivity"
            android:exported="true"
            android:theme="@style/AppThemeFullscreenDark"
            android:screenOrientation="sensorLandscape">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>"""
    manifest = manifest[:match.start()] + original + "\n        " + launcher + manifest[match.end():]
    manifest = manifest.replace("com.winlator.FileProvider", APP_ID + ".FileProvider")
    old_icon = 'android:icon="@mipmap/ic_launcher"'
    if old_icon not in manifest:
        raise RuntimeError("Icone do AndroidManifest mudou; identidade TCL nao aplicada")
    manifest = manifest.replace(old_icon, 'android:icon="@drawable/tcl_launcher_icon"')
    # Um eventual icone circular tambem deve ser nosso.
    manifest = manifest.replace('android:roundIcon="@mipmap/ic_launcher_round"',
                                'android:roundIcon="@drawable/tcl_launcher_icon"')
    manifest_path.write_text(manifest, encoding="utf-8")
    drawable = base / "res/drawable"
    drawable.mkdir(exist_ok=True, parents=True)
    shutil.copy2(Path(__file__).with_name("tcl_launcher_icon.xml"),
                 drawable / "tcl_launcher_icon.xml")

    gradle_path = app / "build.gradle"
    gradle = gradle_path.read_text(encoding="utf-8")
    if "applicationId 'com.winlator'" not in gradle:
        raise RuntimeError("Application ID da base mudou")
    gradle_path.write_text(gradle.replace("applicationId 'com.winlator'",
                                         "applicationId '" + APP_ID + "'"), encoding="utf-8")

    # O nome localizado sobrescreve o nome principal no Android: atualizar todos.
    translated_count = 0
    for values in (base / "res").glob("values*/strings.xml"):
        strings = values.read_text(encoding="utf-8")
        updated, count = re.subn(r'(<string name="app_name">).*?(</string>)',
                                 r'\g<1>TCL Desktop 10\g<2>', strings, count=1)
        if count:
            values.write_text(updated, encoding="utf-8")
            translated_count += 1
    if translated_count < 2:
        raise RuntimeError("Nomes de traducao ausentes; verificar identidade TCL")

    for file in base.rglob("*.java"):
        data = file.read_text(encoding="utf-8")
        if "com.winlator.FileProvider" in data:
            file.write_text(data.replace("com.winlator.FileProvider",
                                         APP_ID + ".FileProvider"), encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("TclDesktopActivity.java"),
                 java_dir / "TclDesktopActivity.java")
    license_dir = base / "assets/tcl-licenses"
    license_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "LICENSE", license_dir / "WINLATOR-LICENSE.txt")
    (license_dir / "NOTICE.txt").write_text(
        "TCL Desktop 10: interface de inicializacao personalizada baseada no Winlator.\n"
        "Componentes Wine/Box64 e outros mantem suas respectivas licencas.\n"
        "Codigo upstream: https://github.com/brunodev85/winlator-app\n",
        encoding="utf-8")
    print("TCL Desktop 10 preparado com motor Wine/Box64 real.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: prepare.py /pasta-do-winlator")
    patch(Path(sys.argv[1]).resolve())
