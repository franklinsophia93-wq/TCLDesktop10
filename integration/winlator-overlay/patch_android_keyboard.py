#!/usr/bin/env python3
"""Permite acionar teclado Android a partir do desktop Wine.
A API X11 nao expoe diretamente todos os campos Edit Win32;
duplo toque intencional evita exibir IME em cada clique de jogo.
"""
import sys
from pathlib import Path

def one(source: str, old: str, new: str, what: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise RuntimeError(f"Incompatibilidade em {what}: {matches} ocorrencias")
    return source.replace(old, new, 1)

def patch(root: Path):
    base = root / "app/src/main/java/com/winlator"
    touch_file = base / "widget/TouchpadView.java"
    activity_file = base / "XServerDisplayActivity.java"
    touch = touch_file.read_text(encoding="utf-8")
    activity = activity_file.read_text(encoding="utf-8")

    touch = one(touch,
        "    private Runnable fourFingersTapCallback;",
        """    private Runnable fourFingersTapCallback;
    private Runnable tclKeyboardRequestedCallback;
    private long tclLastTapMillis = 0L;
    private int tclLastTapX = -9999;
    private int tclLastTapY = -9999;""",
        "keyboard gesture fields")

    touch = one(touch,
        """            case 1:
                if (finger1.isTap()) {
                    if (moveCursorToTouchpoint) xServer.injectPointerMove(finger1.x, finger1.y);
                    pressPointerButtonLeft(finger1);
                }
                break;""",
        """            case 1:
                if (finger1.isTap()) {
                    // Um duplo toque no mesmo campo envia o clique ao Wine antes
                    // de solicitar o IME. Nao intercepta a digitacao nativa.
                    long now = System.currentTimeMillis();
                    boolean samePosition = Math.abs(finger1.x - tclLastTapX) <= 28
                            && Math.abs(finger1.y - tclLastTapY) <= 28;
                    boolean openKeyboard = tclKeyboardRequestedCallback != null
                            && now - tclLastTapMillis < 450 && samePosition;
                    tclLastTapMillis = openKeyboard ? 0L : now;
                    tclLastTapX = finger1.x;
                    tclLastTapY = finger1.y;
                    if (moveCursorToTouchpoint) xServer.injectPointerMove(finger1.x, finger1.y);
                    pressPointerButtonLeft(finger1);
                    if (openKeyboard) {
                        // A liberacao do botao do mouse e feita 30ms depois.
                        postDelayed(() -> {
                            if (tclKeyboardRequestedCallback != null)
                                tclKeyboardRequestedCallback.run();
                        }, 130L);
                    }
                }
                break;""",
        "single tap gesture")

    touch = one(touch,
        """    public void setFourFingersTapCallback(Runnable fourFingersTapCallback) {
        this.fourFingersTapCallback = fourFingersTapCallback;
    }""",
        """    public void setFourFingersTapCallback(Runnable fourFingersTapCallback) {
        this.fourFingersTapCallback = fourFingersTapCallback;
    }

    /** Teclado Android opcional: duplo toque apenas no desktop completo. */
    public void setTclKeyboardRequestedCallback(Runnable callback) {
        this.tclKeyboardRequestedCallback = callback;
    }""",
        "keyboard callback")

    activity = one(activity,
        "        touchpadView.setSensitivity(globalCursorSpeed);",
        """        touchpadView.setSensitivity(globalCursorSpeed);
        if (container != null && shortcut == null && !getIntent().hasExtra("exec_path")) {
            touchpadView.setTclKeyboardRequestedCallback(this::tclOpenAndroidKeyboard);
        }""",
        "activate keyboard gesture on desktop only")

    activity = one(activity,
        "    public void tclOpenSettings() {",
        """    /** Exibe teclado Android que ja alimenta eventos de teclas do XServer/Wine. */
    public void tclOpenAndroidKeyboard() {
        if (isFinishing() || isDestroyed()) return;
        runOnUiThread(() -> AppUtils.showKeyboard(this));
    }

    public void tclOpenSettings() {""",
        "Android IME action")

    touch_file.write_text(touch, encoding="utf-8")
    activity_file.write_text(activity, encoding="utf-8")
    print("IME Android: botao no shell + duplo toque no mesmo local, sem bloquear jogos.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: patch_android_keyboard.py /winlator-app")
    patch(Path(sys.argv[1]).resolve())
