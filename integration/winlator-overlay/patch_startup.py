#!/usr/bin/env python3
"""Corrige espera infinita de splash e acrescenta recuperação explícita para GPU Mali."""
from pathlib import Path
import sys

def patch(source: Path):
    target = source / "app/src/main/java/com/winlator/XServerDisplayActivity.java"
    text = target.read_text(encoding="utf-8")

    def replace_once(needle, replacement, what):
        nonlocal text
        if text.count(needle) != 1:
            raise RuntimeError(f"Versão upstream incompatível ({what}): {text.count(needle)} ocorrências")
        text = text.replace(needle, replacement, 1)

    replace_once("import android.app.Activity;\n",
                 "import android.app.Activity;\nimport android.app.AlertDialog;\n"
                 "import android.os.Handler;\nimport android.os.Looper;\n",
                 "Android imports")

    replace_once("    private String screenEffectProfile;\n",
                 "    private String screenEffectProfile;\n"
                 "    private static final long TCL_START_TIMEOUT_MS = 90000L;\n",
                 "Class attributes")

    anchor = "        setupUI();\n\n        Executors.newSingleThreadExecutor().execute(() -> {"
    snippet = """        setupUI();

        // TCL Desktop 10: nunca bloquear o usuario indefinidamente num spinner
        // quando o Wine nao conseguir mapear nenhuma janela X11.
        if (!isGenerateWineprefix() && container != null) {
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                if (isFinishing() || isDestroyed() || flags[0]) return;
                preloaderDialog.closeOnUiThread();
                String report = "O ambiente Windows nao abriu uma janela em 90 segundos.\\n"
                    + "Isso pode ocorrer por driver grafico, Wine ou configuracao do conteiner.\\n\\n"
                    + "Conteiner: " + container.getName() + "\\n"
                    + "GPU/driver: " + container.getGraphicsDriver() + "\\n"
                    + "DirectX: " + container.getDXWrapper() + "\\n"
                    + "Android: " + android.os.Build.VERSION.RELEASE + "\\n\\n"
                    + "O modo compativel usa VirGL e WineD3D (mais lento; nem todo jogo funciona).";
                new AlertDialog.Builder(this)
                    .setTitle("TCL Desktop 10 - Falha ao iniciar")
                    .setMessage(report)
                    .setCancelable(false)
                    .setPositiveButton("Modo compativel", (d, which) -> {
                        container.setGraphicsDriver(GraphicsDrivers.VORTEK + "," + GraphicsDrivers.VIRGL);
                        container.setDXWrapper(DXWrappers.WINED3D);
                        container.saveData();
                        AppUtils.restartActivity(this);
                    })
                    .setNeutralButton("Copiar diagnostico", (d, which) -> {
                        android.content.ClipboardManager clip =
                            (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                        if (clip != null) clip.setPrimaryClip(
                            android.content.ClipData.newPlainText("TCL Desktop 10", report));
                        // Permite sair normalmente e alterar manualmente as configuracoes.
                    })
                    .setNegativeButton("Fechar", (d, which) -> finish())
                    .show();
            }, TCL_START_TIMEOUT_MS);
        }

        Executors.newSingleThreadExecutor().execute(() -> {"""
    replace_once(anchor, snippet, "startup UI and worker")

    target.write_text(text, encoding="utf-8")
    print("TCL Desktop 10: monitor de inicializacao + modo grafico compativel adicionados.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: patch_startup.py /pasta-do-winlator")
    patch(Path(sys.argv[1]).resolve())
