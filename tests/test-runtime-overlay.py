#!/usr/bin/env python3
"""Testa o patch TCL sem fingir que executou Windows ou que compilou APK."""
import importlib.util
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source_file = root / "integration/winlator-overlay/prepare.py"
spec = importlib.util.spec_from_file_location("tcl_prepare", source_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

manifest = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.winlator">
<application android:label="@string/app_name" android:icon="@mipmap/ic_launcher">
<activity android:name="com.winlator.MainActivity"
    android:theme="@style/AppThemeDark"
    android:exported="true"
    android:screenOrientation="sensor"
    android:configChanges="keyboard|keyboardHidden|orientation|screenSize|screenLayout|smallestScreenSize|density|navigation">
    <intent-filter>
        <action android:name="android.intent.action.MAIN"/>
        <category android:name="android.intent.category.LAUNCHER"/>
    </intent-filter>
</activity>
<provider android:authorities="com.winlator.FileProvider"/>
</application></manifest>"""

with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    base = work / "app/src/main"
    java = base / "java/com/winlator"
    libs = base / "jniLibs/arm64-v8a"
    assets = base / "assets"
    values = base / "res/values"
    for folder in (java, libs, assets / "box64", values):
        folder.mkdir(parents=True)
    (base / "AndroidManifest.xml").write_text(manifest)
    (values / "strings.xml").write_text(
        '<resources><string name="app_name">Winlator</string></resources>')
    for lang in ("pt", "ru"):
        translated = base / ("res/values-" + lang)
        translated.mkdir(exist_ok=True)
        (translated / "strings.xml").write_text(
            '<resources><string name="app_name">Winlator</string></resources>')
    (work / "app/build.gradle").write_text("applicationId 'com.winlator'")
    (work / "LICENSE").write_text("Upstream test fixture")
    (assets / "rootfs.tzst").write_bytes(b"0" * 10_000_001)
    (assets / "container_pattern.tzst").write_bytes(b"test")
    (libs / "libtest.so").write_bytes(b"test")
    (java / "XServerDisplayActivity.java").write_text("package com.winlator;")
    (java / "ProviderUse.java").write_text('String s="com.winlator.FileProvider";')
    hardcoded = [
        ("cpp/winlator/include/winlator.h", "/data/data/com.winlator/cache"),
        ("cpp/gladiorenderer/include/gladio.h", "/data/data/com.winlator/files/rootfs/tmp/.X11-unix/X0"),
        ("cpp/vortekrenderer/include/vortek.h", "/data/data/com.winlator/files/rootfs/tmp/.vortek/V0"),
        ("java/com/winlator/core/AppUtils.java", "/data/data/com.winlator/storage"),
    ]
    for relative, old_path in hardcoded:
        fixture = base / relative
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text('static final String PATH = "' + old_path + '";')

    mod.patch(work)
    rewritten = (base / "AndroidManifest.xml").read_text()
    assert rewritten.count("android.intent.action.MAIN") == 1
    assert "com.winlator.TclDesktopActivity" in rewritten
    assert "com.tcldesktop.windows.FileProvider" in rewritten
    assert "com.winlator.FileProvider" not in rewritten
    assert 'android:icon="@drawable/tcl_launcher_icon"' in rewritten
    assert (base / "res/drawable/tcl_launcher_icon.xml").exists()
    assert "com.tcldesktop.windows" in (work / "app/build.gradle").read_text()
    assert "TCL Desktop 10" in (values / "strings.xml").read_text()
    assert "TCL Desktop 10" in (base / "res/values-pt/strings.xml").read_text()
    assert "TCL Desktop 10" in (base / "res/values-ru/strings.xml").read_text()
    assert "com.tcldesktop.windows.FileProvider" in (java / "ProviderUse.java").read_text()
    for relative, old_path in hardcoded:
        content = (base / relative).read_text()
        assert old_path not in content, relative
        assert "/data/data/com.tcldesktop.windows/" in content, relative
    assert (java / "TclDesktopActivity.java").exists()
    assert (assets / "tcl-licenses/WINLATOR-LICENSE.txt").exists()
    print("Verificacoes do overlay aprovadas (sem compilacao ou teste Wine).")
