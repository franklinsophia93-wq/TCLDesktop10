#!/usr/bin/env python3
"""Instala shell TCL inspirado no Windows 10 no desktop Wine real."""
from pathlib import Path
import sys

def replace_one(source, before, after, label):
    if source.count(before) != 1:
        raise RuntimeError(f"Contrato do upstream mudou em {label}: {source.count(before)}")
    return source.replace(before, after, 1)

def patch(root: Path):
    app = root / "app/src/main"
    source = app / "java/com/winlator/XServerDisplayActivity.java"
    guest_file = app / "java/com/winlator/xenvironment/components/GuestProgramLauncherComponent.java"
    theme_file = app / "java/com/winlator/core/WineThemeManager.java"
    shell_file = Path(__file__).with_name("TclWin10Shell.java")

    # Interface TCL na MESMA Activity que desenha os programas Windows.
    activity = source.read_text(encoding="utf-8")
    activity = replace_one(
        activity, "    private String screenEffectProfile;",
        "    private GuestProgramLauncherComponent tclGuestLauncher;\n"
        "    private String screenEffectProfile;", "field shell")
    activity = replace_one(
        activity,
        "        GuestProgramLauncherComponent guestProgramLauncherComponent = new GuestProgramLauncherComponent();",
        "        GuestProgramLauncherComponent guestProgramLauncherComponent = new GuestProgramLauncherComponent();\n"
        "        tclGuestLauncher = guestProgramLauncherComponent;", "Wine guest instance")
    activity = replace_one(
        activity,
        "        if (MainActivity.DEBUG_MODE) rootView.addView(AppUtils.createDebugMsgTextView(this));",
        "        if (container != null && shortcut == null && !getIntent().hasExtra(\"exec_path\")) {\n"
        "            rootView.addView(new TclWin10Shell(this),\n"
        "                new FrameLayout.LayoutParams(-1, -1));\n"
        "        }\n"
        "        if (MainActivity.DEBUG_MODE) rootView.addView(AppUtils.createDebugMsgTextView(this));",
        "install taskbar")
    activity = replace_one(
        activity,
        "    public XServer getXServer() {",
        "    public int tclLaunchProgram(String wineCommand) {\n"
        "        if (tclGuestLauncher == null) return -1;\n"
        "        return tclGuestLauncher.launchTclProgram(wineCommand);\n"
        "    }\n\n"
        "    public void tclOpenSettings() {\n"
        "        startActivity(new Intent(this, MainActivity.class));\n"
        "    }\n\n"
        "    public XServer getXServer() {", "TCL shell actions")
    source.write_text(activity, encoding="utf-8")

    # Programas secundários NÃO encerram o ambiente ao serem fechados.
    guest = guest_file.read_text(encoding="utf-8")
    # Na inicializacao o XServerDisplayActivity limpa o objeto EnvVars depois de
    # ligar o Wine. Copiamos as variaveis para os atalhos do menu Iniciar.
    guest = replace_one(
        guest,
        "    public void setEnvVars(EnvVars envVars) {\\n        this.envVars = envVars;\\n    }".replace("\\\\n", "\\n"),
        "    public void setEnvVars(EnvVars envVars) {\\n"
        "        this.envVars = new EnvVars();\\n"
        "        if (envVars != null) this.envVars.putAll(envVars);\\n"
        "    }".replace("\\\\n", "\\n"),
        "preserve env for secondaries")
    guest = replace_one(
        guest,
        "    private int execGuestProgram() {",
        "    public int launchTclProgram(String wineCommand) {\n"
        "        if (wineCommand == null || wineCommand.trim().isEmpty()) return -1;\n"
        "        return execGuestProgram(wineCommand, false);\n"
        "    }\n\n"
        "    private int execGuestProgram() {\n"
        "        return execGuestProgram(guestExecutable, true);\n"
        "    }\n\n"
        "    private int execGuestProgram(String launchCommand, boolean mainDesktop) {",
        "secondary wine launcher")
    guest = replace_one(
        guest,
        '        String command = rootDir+"/usr/local/bin/box64 "+guestExecutable;',
        '        String command = rootDir+"/usr/local/bin/box64 "+launchCommand;\n'
        '        if (!mainDesktop) return ProcessHelper.exec(command, envVars, rootDir, null);',
        "secondary command process")
    guest_file.write_text(guest, encoding="utf-8")

    # Papel de parede desenhado no BMP do PRÓPRIO WINE, abaixo dos programas.
    theme = theme_file.read_text(encoding="utf-8")
    theme = replace_one(
        theme,
        "import android.graphics.Paint;",
        "import android.graphics.Paint;\nimport android.graphics.Path;\n"
        "import android.graphics.LinearGradient;\nimport android.graphics.Shader;",
        "Canvas imports")
    theme = replace_one(
        theme,
        "    private static void createWallpaperBMPFile(Context context, String wallpaperId, ScreenInfo screenInfo) {",
        "    private static void createWallpaperBMPFile(Context context, String wallpaperId, ScreenInfo screenInfo) {\n"
        "        if (wallpaperId.equals(DEFAULT_WALLPAPER_ID)) {\n"
        "            createTclWin10Wallpaper(context, screenInfo);\n"
        "            return;\n"
        "        }",
        "default Wine wallpaper")

    wallpaper = r"""
    /** Criado como BMP do Wine, nao cobre nem intercepta janelas .exe. */
    private static void createTclWin10Wallpaper(Context context, ScreenInfo screenInfo) {
        final int height = 540;
        final int width = Math.max(960, (int)Math.ceil((float)height * screenInfo.width / screenInfo.height));
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setShader(new LinearGradient(0, 0, width, height,
            new int[]{0xFF071B36, 0xFF0B467D, 0xFF0870B6},
            new float[]{0.0f, 0.56f, 1.0f}, Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, width, height, paint);
        paint.setShader(null);

        // Feixe de luz e janelas de quatro paineis inspiradas no Windows 10.
        final float cx = width * 0.73f, cy = height * 0.49f;
        final float left = width * 0.56f, right = width * 0.89f;
        final float top = height * 0.16f, bottom = height * 0.82f;
        paint.setColor(0x4220CFFF);
        canvas.drawRect(left - 18, top - 18, right + 18, bottom + 18, paint);
        paint.setColor(0xCC44C7FA);
        Path pane = new Path();
        pane.moveTo(left, top + 20);
        pane.lineTo(cx - 5, top + 5);
        pane.lineTo(cx - 5, cy - 5);
        pane.lineTo(left, cy - 13);
        pane.close();
        canvas.drawPath(pane, paint);
        paint.setColor(0xE6B7F3FF);
        Path pane2 = new Path();
        pane2.moveTo(cx + 6, top + 5);
        pane2.lineTo(right, top - 13);
        pane2.lineTo(right, cy - 2);
        pane2.lineTo(cx + 6, cy - 5);
        pane2.close();
        canvas.drawPath(pane2, paint);
        paint.setColor(0xC230ADF1);
        Path pane3 = new Path();
        pane3.moveTo(left, cy + 1);
        pane3.lineTo(cx - 5, cy + 6);
        pane3.lineTo(cx - 5, bottom - 7);
        pane3.lineTo(left, bottom - 25);
        pane3.close();
        canvas.drawPath(pane3, paint);
        paint.setColor(0xDC85DFFF);
        Path pane4 = new Path();
        pane4.moveTo(cx + 6, cy + 6);
        pane4.lineTo(right, cy + 2);
        pane4.lineTo(right, bottom + 11);
        pane4.lineTo(cx + 6, bottom - 7);
        pane4.close();
        canvas.drawPath(pane4, paint);

        // Brilho suave espalhado pelo escritorio.
        paint.setShader(new LinearGradient(left - 110, cy, right + 120, cy,
            new int[]{0x0018BFFF, 0x3B40C9FF, 0x0018BFFF},
            null, Shader.TileMode.CLAMP));
        canvas.drawRect(left - 110, top - 20, right + 120, bottom + 20, paint);
        paint.setShader(null);
        RootFS rootFS = RootFS.find(context);
        File cache = new File(rootFS.getRootDir(), RootFS.USER_CACHE_PATH);
        cache.mkdirs();
        MSBitmap.create(bitmap, new File(cache, "wallpaper.bmp"));
        bitmap.recycle();
    }

"""
    theme = replace_one(
        theme,
        "    public static File getUserWallpaperFile(Context context) {",
        wallpaper + "    public static File getUserWallpaperFile(Context context) {",
        "wallpaper method")
    theme_file.write_text(theme, encoding="utf-8")

    # Aplica o novo BMP uma vez em conteineres ja existentes.
    anchor = "        String desktopTheme = container.getDesktopTheme();"
    activity = source.read_text(encoding="utf-8")
    activity = replace_one(
        activity, anchor,
        "        if (!\"v6\".equals(container.getExtra(\"tclWin10VisualVersion\"))) {\n"
        "            container.putExtra(\"desktopTheme\", null);\n"
        "            container.putExtra(\"tclWin10VisualVersion\", \"v6\");\n"
        "            containerDataChanged = true;\n"
        "        }\n"
        + anchor,
        "force wallpaper update")
    source.write_text(activity, encoding="utf-8")

    target = app / "java/com/winlator/TclWin10Shell.java"
    target.write_text(shell_file.read_text(encoding="utf-8"), encoding="utf-8")
    print("TCL Desktop 10: papel de parede nativo Wine e shell Windows 10 instalados.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: patch_win10_shell.py /winlator-app")
    patch(Path(sys.argv[1]).resolve())
