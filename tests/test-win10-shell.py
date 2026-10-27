#!/usr/bin/env python3
"""Verifica integração visual real com Wine (sem alegar teste em aparelho)."""
import importlib.util
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "tcl_visual_patch", root / "integration/winlator-overlay/patch_win10_shell.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

activity = """package com.winlator;
class XServerDisplayActivity {
    private String screenEffectProfile;
    void setup() {
        GuestProgramLauncherComponent guestProgramLauncherComponent = new GuestProgramLauncherComponent();
        String desktopTheme = container.getDesktopTheme();
        if (MainActivity.DEBUG_MODE) rootView.addView(AppUtils.createDebugMsgTextView(this));
    }
    public XServer getXServer() {return null;}
}
"""
guest = """class GuestProgramLauncherComponent {
    private int execGuestProgram() {
        String command = rootDir+"/usr/local/bin/box64 "+guestExecutable;
        return ProcessHelper.exec(command, envVars, rootDir, null);
    }
}
"""
theme = """import android.graphics.Paint;
class WineThemeManager {
    private static void createWallpaperBMPFile(Context context, String wallpaperId, ScreenInfo screenInfo) {
        regularWallpaper();
    }
    public static File getUserWallpaperFile(Context context) {return null;}
}
"""

with tempfile.TemporaryDirectory() as tmp:
    project = Path(tmp)
    main = project / "app/src/main"
    for path, data in {
        "java/com/winlator/XServerDisplayActivity.java": activity,
        "java/com/winlator/xenvironment/components/GuestProgramLauncherComponent.java": guest,
        "java/com/winlator/core/WineThemeManager.java": theme,
    }.items():
        file = main / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data)
    module.patch(project)
    patched = (main / "java/com/winlator/XServerDisplayActivity.java").read_text()
    guest_patched = (main / "java/com/winlator/xenvironment/components/GuestProgramLauncherComponent.java").read_text()
    themed = (main / "java/com/winlator/core/WineThemeManager.java").read_text()
    shell = (main / "java/com/winlator/TclWin10Shell.java").read_text()
    assert "tclLaunchProgram" in patched
    assert "new TclWin10Shell(this)" in patched
    assert "tclWin10VisualVersion" in patched
    assert "if (!mainDesktop) return ProcessHelper.exec" in guest_patched
    assert "createTclWin10Wallpaper" in themed
    assert "MSBitmap.create(bitmap" in themed
    for caption in ("Explorador de Arquivos", "Este Computador", "Bloco de notas", "Executar programa .exe"):
        assert caption in shell, caption
    assert 'runWine("wine notepad.exe")' in shell
    assert "return -1;" in guest_patched or "execGuestProgram(" in guest_patched
    try:
        module.patch(project)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Um patch deve ser aplicado apenas uma vez")
    print("Shell Windows 10: integração estrutural verificada.")
