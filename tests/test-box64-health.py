#!/usr/bin/env python3
"""Verifica que o patch Box64 preserva o contrato e evita cache falso."""
import importlib.util
import tempfile
from pathlib import Path

base = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("box64_patch", base / "integration/winlator-overlay/patch_box64_health.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

helper = """package com.winlator.core;
public abstract class ProcessHelper {
    public static String[] splitCommand(String command) { return null; }
}
"""
guest = """package com.winlator.xenvironment.components;
public class GuestProgramLauncherComponent {
    private void extractBox64File() {
        if (!box64Version.equals(currentBox64Version)) {
            GeneralComponents.extractFile(GeneralComponents.Type.BOX64, context, box64Version, DefaultVersion.BOX64);
            preferences.edit().putString("current_box64_version", box64Version).apply();
        }
    }
    private void start() {
        String command = rootDir+"/usr/local/bin/box64 "+guestExecutable;
    }
}
"""
with tempfile.TemporaryDirectory() as dirname:
    project = Path(dirname)
    jroot = project / "app/src/main/java/com/winlator"
    jroot.mkdir(parents=True)
    (jroot / "core").mkdir()
    (jroot / "xenvironment/components").mkdir(parents=True)
    helper_file = jroot / "core/ProcessHelper.java"
    guest_file = jroot / "xenvironment/components/GuestProgramLauncherComponent.java"
    helper_file.write_text(helper)
    guest_file.write_text(guest)
    module.patch(project)
    h = helper_file.read_text()
    g = guest_file.read_text()
    assert "tclReportDiagnostic" in h
    assert "reextracao" not in g
    assert 'preferences.edit().remove("current_box64_version").apply()' in g
    assert "FileUtils.chmod(binary, 0771)" in g
    assert 'new File(rootDir, "lib/ld-linux-aarch64.so.1")' in g
    assert "return -1;" in g
    assert "box64.canExecute()" in g
    try:
        module.patch(project)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Patch nao deve ser aplicado duas vezes")
print("Integridade e diagnostico Box64: testes de estrutura aprovados.")
