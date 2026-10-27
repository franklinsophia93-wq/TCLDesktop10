#!/usr/bin/env python3
"""Testa alteracoes do watchdog em fontes simuladas; nao testa execucao Wine."""
import importlib.util
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tcl_patch", root / "integration/winlator-overlay/patch_startup.py")
patch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch_module)

source = r"""package com.winlator;
import android.app.Activity;
public class XServerDisplayActivity {
    private String screenEffectProfile;
    void dummy() {
        ProcessHelper.removeAllDebugCallbacks();
        envVars.put("WINEDEBUG", enableWineDebug && !wineDebugChannels.isEmpty() ? "+"+wineDebugChannels.replace(",", ",+") : "-all");
        setupUI();

        Executors.newSingleThreadExecutor().execute(() -> {
            runWindows();
        });
    }
    protected void onDestroy() {
        close();
    }
}"""
helper = """public class ProcessHelper {
    void foo() {
        try { doSomething(); }
        catch (Exception e) {}
        return pid;
    }
}"""
with tempfile.TemporaryDirectory() as tmp:
    workspace = Path(tmp)
    dst = workspace / "app/src/main/java/com/winlator/XServerDisplayActivity.java"
    ph = workspace / "app/src/main/java/com/winlator/core/ProcessHelper.java"
    ph.parent.mkdir(parents=True)
    dst.write_text(source)
    ph.write_text(helper)
    patch_module.patch(workspace)
    compiled = dst.read_text()
    changed_helper = ph.read_text()
    assert "TCL_START_TIMEOUT_MS = 60000L" in compiled
    assert 'envVars.put("BOX64_LOG", "1")' in compiled
    assert "tclLogReceiver" in compiled
    assert "ProcessHelper.addDebugCallback" in compiled
    assert "ProcessHelper.removeDebugCallback" in compiled
    assert "Copiar relatorio" in compiled
    assert "REGISTROS WINE / BOX64" in compiled
    assert "PROCESS ERROR" in changed_helper
    try:
        patch_module.patch(workspace)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Patch duplicado nao pode ser aceito")
    print("Testes de diagnostico aprovados (nao testa execucao de exe).")
