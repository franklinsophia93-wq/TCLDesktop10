#!/usr/bin/env python3
"""Comprova insercao do watchdog em codigo Android tipado; nao simula Wine."""
import importlib.util
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
module_path=root/"integration/winlator-overlay/patch_startup.py"
spec=importlib.util.spec_from_file_location("startup_patch",module_path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture="""package com.winlator;
import android.app.Activity;

public class XServerDisplayActivity {
    private String screenEffectProfile;
    public void onCreate() {
        setupUI();

        Executors.newSingleThreadExecutor().execute(() -> {
            runWindows();
        });
    }
}
"""
with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)
    java=source/"app/src/main/java/com/winlator/XServerDisplayActivity.java"
    java.parent.mkdir(parents=True)
    java.write_text(fixture,encoding="utf-8")
    module.patch(source)
    code=java.read_text(encoding="utf-8")
    assert "TCL_START_TIMEOUT_MS = 90000L" in code
    assert "container.setGraphicsDriver" in code
    assert "container.setDXWrapper(DXWrappers.WINED3D)" in code
    assert "flags[0]" in code
    assert "setPrimaryClip" in code
    assert code.index("TCL_START_TIMEOUT_MS") < code.index("Executors.newSingleThreadExecutor()")
    try:
        module.patch(source)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Nao pode aplicar patch duas vezes")
    print("Patch do watchdog validado (sem simular execucao de Wine).")
