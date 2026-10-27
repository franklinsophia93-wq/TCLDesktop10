#!/usr/bin/env python3
"""Testa gesto de teclado Android no XServer (nao simula aparelho fisico)."""
import importlib.util
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
p = repo / "integration/winlator-overlay/patch_android_keyboard.py"
spec = importlib.util.spec_from_file_location("keyboard_patch", p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

touch = """package com.winlator.widget;
class TouchpadView {
    private Runnable fourFingersTapCallback;
    void handleFingerUp(Finger finger1) {
        switch (numFingers) {
            case 1:
                if (finger1.isTap()) {
                    if (moveCursorToTouchpoint) xServer.injectPointerMove(finger1.x, finger1.y);
                    pressPointerButtonLeft(finger1);
                }
                break;
        }
    }
    public void setFourFingersTapCallback(Runnable fourFingersTapCallback) {
        this.fourFingersTapCallback = fourFingersTapCallback;
    }
}
"""
activity = """package com.winlator;
class XServerDisplayActivity {
    void setupUI() {
        touchpadView.setSensitivity(globalCursorSpeed);
    }
    public void tclOpenSettings() {
    }
}
"""
with tempfile.TemporaryDirectory() as tmp:
    source = Path(tmp)
    java = source / "app/src/main/java/com/winlator"
    (java / "widget").mkdir(parents=True)
    (java / "widget/TouchpadView.java").write_text(touch)
    (java / "XServerDisplayActivity.java").write_text(activity)
    module.patch(source)
    patched_touch = (java / "widget/TouchpadView.java").read_text()
    patched_activity = (java / "XServerDisplayActivity.java").read_text()
    shell = (repo / "integration/winlator-overlay/TclWin10Shell.java").read_text()
    assert "tclLastTapMillis < 450" in patched_touch
    assert "tclKeyboardRequestedCallback" in patched_touch
    assert "postDelayed(() ->" in patched_touch
    assert "setTclKeyboardRequestedCallback(this::tclOpenAndroidKeyboard)" in patched_activity
    assert "AppUtils.showKeyboard(this)" in patched_activity
    assert 'setContentDescription("Abrir teclado Android para digitar nos programas Windows")' in shell
    assert 'keyboard.setOnClickListener(v -> activity.tclOpenAndroidKeyboard())' in shell
    assert "Teclado do celular (ou 2 toques)" in shell
    try:
        module.patch(source)
    except RuntimeError:
        pass
    else:
        raise AssertionError("O patch nao deve ser executado duas vezes")
print("Gesto e atalho do teclado Android: verificacoes de codigo aprovadas.")
