#!/usr/bin/env python3
"""TCL Desktop 10: diagnosticos de inicializacao em vez de espera infinita."""
from pathlib import Path
import sys

def patch(source: Path):
    target = source / "app/src/main/java/com/winlator/XServerDisplayActivity.java"
    contents = target.read_text(encoding="utf-8")

    def replace_one(old, new, label):
        nonlocal contents
        if contents.count(old) != 1:
            raise RuntimeError(f"Origem mudou em {label}: {contents.count(old)} ocorrencias")
        contents = contents.replace(old, new, 1)

    replace_one("import android.app.Activity;\n",
                "import android.app.Activity;\nimport android.app.AlertDialog;\n"
                "import android.os.Handler;\nimport android.os.Looper;\n",
                "imports")

    fields = r"""    private String screenEffectProfile;
    private static final long TCL_START_TIMEOUT_MS = 60000L;
    private final StringBuilder tclLog = new StringBuilder();
    private final com.winlator.core.Callback<String> tclLogReceiver = (line) -> {
        if (line == null) return;
        synchronized (tclLog) {
            String shortLine = line.length() > 450 ? line.substring(0, 450) : line;
            tclLog.append(shortLine).append('\n');
            if (tclLog.length() > 3800) tclLog.delete(0, tclLog.length() - 3800);
        }
    };
"""
    replace_one("    private String screenEffectProfile;\n", fields, "diagnostic buffer")

    replace_one("        ProcessHelper.removeAllDebugCallbacks();\n",
                "        ProcessHelper.removeAllDebugCallbacks();\n"
                "        ProcessHelper.addDebugCallback(tclLogReceiver);\n",
                "log subscriber")
    replace_one("    protected void onDestroy() {\n",
                "    protected void onDestroy() {\n"
                "        ProcessHelper.removeDebugCallback(tclLogReceiver);\n",
                "cleanup")

    wine_debug = r'        envVars.put("WINEDEBUG", enableWineDebug && !wineDebugChannels.isEmpty() ? "+"+wineDebugChannels.replace(",", ",+") : "-all");'
    replace_one(wine_debug,
                '        envVars.put("WINEDEBUG", "+err,+seh");\n'
                '        envVars.put("BOX64_LOG", "1");',
                "Wine / Box64 stderr")

    watchdog = r"""        setupUI();

        // Wine pode travar antes de mapear a primeira janela; nesse caso
        // mostrar os ultimos registros do processo e permitir voltar.
        if (!isGenerateWineprefix() && container != null) {
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                if (isFinishing() || isDestroyed() || flags[0]) return;
                preloaderDialog.closeOnUiThread();
                String output;
                synchronized (tclLog) {
                    output = tclLog.length() == 0
                            ? "(Nenhum log do processo foi recebido)"
                            : tclLog.toString();
                }
                String report = "Nenhuma janela Windows apos 60 segundos.\n\n"
                    + "Conteiner: " + container.getName() + "\n"
                    + "Driver: " + container.getGraphicsDriver() + "\n"
                    + "DirectX: " + container.getDXWrapper() + "\n"
                    + "Android: " + android.os.Build.VERSION.RELEASE + "\n\n"
                    + "REGISTROS WINE / BOX64:\n" + output;
                new AlertDialog.Builder(this)
                    .setTitle("TCL Desktop 10 - Diagnostico")
                    .setMessage(report)
                    .setCancelable(false)
                    .setPositiveButton("Copiar relatorio", (d, which) -> {
                        android.content.ClipboardManager clipboard =
                            (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                        if (clipboard != null) clipboard.setPrimaryClip(
                            android.content.ClipData.newPlainText("TCL Desktop 10", report));
                    })
                    .setNeutralButton("Configuracoes", (d, which) -> {
                        startActivity(new Intent(this, MainActivity.class));
                        finish();
                    })
                    .setNegativeButton("Fechar", (d, which) -> finish())
                    .show();
            }, TCL_START_TIMEOUT_MS);
        }

        Executors.newSingleThreadExecutor().execute(() -> {"""
    replace_one("        setupUI();\n\n        Executors.newSingleThreadExecutor().execute(() -> {",
                watchdog, "watchdog")
    target.write_text(contents, encoding="utf-8")

    helper_path = source / "app/src/main/java/com/winlator/core/ProcessHelper.java"
    helper = helper_path.read_text(encoding="utf-8")
    needle = "        catch (Exception e) {}\n        return pid;"
    replacement = r"""        catch (Exception e) {
            android.util.Log.e("TCLDesktop10", "Processo nao iniciou", e);
            synchronized (debugCallbacks) {
                for (Callback<String> callback : debugCallbacks)
                    callback.call("PROCESS ERROR: " + e.toString());
            }
        }
        return pid;"""
    if helper.count(needle) != 1:
        raise RuntimeError("ProcessHelper mudou; impossivel coletar falhas")
    helper_path.write_text(helper.replace(needle, replacement, 1), encoding="utf-8")
    print("Diagnostico TCL: Wine/Box64 stderr + watchdog 60 s + excecoes de processo.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: patch_startup.py /repositorio-upstream")
    patch(Path(sys.argv[1]).resolve())
