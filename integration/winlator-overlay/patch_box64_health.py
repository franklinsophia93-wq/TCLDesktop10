#!/usr/bin/env python3
"""Autorreparo da instalação do Box64 e diagnostico do carregador ARM64.

Modifica apenas codigo Java do upstream fixado; interrompe o build se as
assinaturas dos pontos de integracao mudarem.
"""
from pathlib import Path
import sys

def patch(source: Path):
    source = source.resolve()
    helper_file = source / "app/src/main/java/com/winlator/core/ProcessHelper.java"
    guest_file = source / "app/src/main/java/com/winlator/xenvironment/components/GuestProgramLauncherComponent.java"
    helper = helper_file.read_text(encoding="utf-8")
    guest = guest_file.read_text(encoding="utf-8")

    hook = "    public static String[] splitCommand(String command) {"
    diagnostic = """    public static void tclReportDiagnostic(String information) {
        android.util.Log.e("TCLDesktop10", information);
        synchronized (debugCallbacks) {
            for (Callback<String> callback : debugCallbacks) {
                callback.call("TCL PREFLIGHT: " + information);
            }
        }
    }

"""
    if helper.count(hook) != 1:
        raise RuntimeError("ProcessHelper mudou: sem ponto para relatar diagnosticos")
    helper = helper.replace(hook, diagnostic + hook, 1)

    old = """        if (!box64Version.equals(currentBox64Version)) {
            GeneralComponents.extractFile(GeneralComponents.Type.BOX64, context, box64Version, DefaultVersion.BOX64);
            preferences.edit().putString("current_box64_version", box64Version).apply();
        }"""
    new = """        File binary = new File(environment.getRootFS().getRootDir(), "usr/local/bin/box64");
        boolean usable = binary.isFile() && binary.length() > 1024 * 1024;
        if (!box64Version.equals(currentBox64Version) || !usable) {
            GeneralComponents.extractFile(GeneralComponents.Type.BOX64, context, box64Version, DefaultVersion.BOX64);
            usable = binary.isFile() && binary.length() > 1024 * 1024;
            if (usable) {
                FileUtils.chmod(binary, 0771);
                preferences.edit().putString("current_box64_version", box64Version).apply();
            } else {
                preferences.edit().remove("current_box64_version").apply();
                ProcessHelper.tclReportDiagnostic("Box64 ausente ou extracao incompleta: " + binary.getAbsolutePath());
            }
        }"""
    if guest.count(old) != 1:
        raise RuntimeError("Logica de instalacao Box64 do upstream mudou")
    guest = guest.replace(old, new, 1)

    anchor = '        String command = rootDir+"/usr/local/bin/box64 "+guestExecutable;'
    preflight = """        File box64 = new File(rootDir, "usr/local/bin/box64");
        File loader = new File(rootDir, "lib/ld-linux-aarch64.so.1");
        if (!box64.isFile() || box64.length() < 1024 * 1024 || !box64.canExecute()) {
            ProcessHelper.tclReportDiagnostic("Binario Box64 indisponivel: exists="
                + box64.exists() + " length=" + box64.length()
                + " executable=" + box64.canExecute() + " path=" + box64);
            return -1;
        }
        if (!loader.isFile() || loader.length() < 10000) {
            ProcessHelper.tclReportDiagnostic("Carregador Linux ARM64 indisponivel: exists="
                + loader.exists() + " length=" + loader.length() + " path=" + loader);
            return -1;
        }
"""
    if guest.count(anchor) != 1:
        raise RuntimeError("Lancamento Box64 do upstream mudou")
    guest = guest.replace(anchor, preflight + anchor, 1)
    helper_file.write_text(helper, encoding="utf-8")
    guest_file.write_text(guest, encoding="utf-8")
    print("Box64: verificacao de integridade, reextracao e diagnostico adicionados.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: patch_box64_health.py /repositorio-winlator")
    patch(Path(sys.argv[1]))
