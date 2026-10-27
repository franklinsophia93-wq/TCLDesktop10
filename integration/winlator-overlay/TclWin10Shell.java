package com.winlator;

import android.app.AlertDialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.os.Handler;
import android.os.Looper;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Camada Windows 10 do desktop Wine. Aplicativos e janelas seguem no XServer
 * real; os botoes chamam comandos Wine na mesma sessao Box64.
 */
public final class TclWin10Shell extends FrameLayout {
    private final XServerDisplayActivity activity;
    private final LinearLayout startMenu;
    private final TextView clock;
    private final Handler handler = new Handler(Looper.getMainLooper());

    public TclWin10Shell(XServerDisplayActivity activity) {
        super(activity);
        this.activity = activity;
        setClipChildren(false);

        // Os espacos vazios permanecem transparentes e sem clique,
        // para que o mouse/toque alcance os aplicativos Win32.
        startMenu = new LinearLayout(activity);
        startMenu.setOrientation(LinearLayout.VERTICAL);
        startMenu.setPadding(dp(15), dp(12), dp(15), dp(12));
        startMenu.setBackground(shape(0xF41B2635, 8, 0xFF34455E));
        startMenu.setVisibility(View.GONE);
        int availableDp = (int)(getResources().getDisplayMetrics().heightPixels
                / getResources().getDisplayMetrics().density);
        int panelHeight = Math.max(175, Math.min(450, availableDp - 60));
        LayoutParams panelParams = new LayoutParams(dp(366), dp(panelHeight), Gravity.START | Gravity.BOTTOM);
        panelParams.leftMargin = dp(8);
        panelParams.bottomMargin = dp(44);
        addView(startMenu, panelParams);

        TextView brand = item("  TCL Desktop 10", 19, 0xFFFFFFFF);
        brand.setTypeface(Typeface.DEFAULT_BOLD);
        startMenu.addView(brand, new LinearLayout.LayoutParams(-1, dp(44)));
        startMenu.addView(line(), new LinearLayout.LayoutParams(-1, dp(1)));

        ScrollView scrolling = new ScrollView(activity);
        scrolling.setFillViewport(false);
        startMenu.addView(scrolling, new LinearLayout.LayoutParams(-1, 0, 1f));
        LinearLayout items = new LinearLayout(activity);
        items.setOrientation(LinearLayout.VERTICAL);
        scrolling.addView(items);

        addEntry(items, "▣   Explorador de Arquivos", () -> runWine("wine explorer.exe"));
        addEntry(items, "▤   Este Computador", () -> runWine("wine explorer.exe C:\\\\"));
        addEntry(items, "▤   Bloco de notas", () -> runWine("wine notepad.exe"));
        addEntry(items, "▣   Painel de Controle", () -> runWine("wine control.exe"));
        addEntry(items, ">_   Terminal Windows", () -> runWine("wine cmd.exe"));
        addEntry(items, "⌕   Executar programa .exe", this::showRunDialog);
        addEntry(items, "⚙   Configurações do ambiente", () -> {
            closeStart();
            activity.tclOpenSettings();
        });
        addEntry(items, "▭   Ocultar barra de tarefas", () -> {
            closeStart();
            setVisibility(View.GONE);
            android.widget.Toast.makeText(activity,
                    "Barra oculta. Saia e volte ao desktop para restaurar.",
                    android.widget.Toast.LENGTH_LONG).show();
        });

        LinearLayout taskbar = new LinearLayout(activity);
        taskbar.setOrientation(LinearLayout.HORIZONTAL);
        taskbar.setGravity(Gravity.CENTER_VERTICAL);
        taskbar.setBackgroundColor(0xF5141D2A);
        LayoutParams taskParams = new LayoutParams(-1, dp(44), Gravity.BOTTOM);
        addView(taskbar, taskParams);

        TextView start = item("⊞", 27, 0xFFFFFFFF);
        start.setGravity(Gravity.CENTER);
        start.setContentDescription("Abrir menu Iniciar do TCL Desktop 10");
        taskbar.addView(start, new LinearLayout.LayoutParams(dp(52), -1));
        start.setOnClickListener(v -> {
            startMenu.setVisibility(startMenu.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE);
        });
        taskbar.addView(separator(), new LinearLayout.LayoutParams(dp(1), dp(25)));

        TextView search = item("⌕  Pesquisar", 13, 0xFFCFD7E0);
        search.setGravity(Gravity.CENTER_VERTICAL);
        search.setPadding(dp(11), 0, dp(5), 0);
        taskbar.addView(search, new LinearLayout.LayoutParams(dp(155), -1));
        search.setOnClickListener(v -> showRunDialog());

        TextView files = item("▣", 23, 0xFF7DCEFF);
        files.setGravity(Gravity.CENTER);
        files.setContentDescription("Explorador de Arquivos do Wine");
        taskbar.addView(files, new LinearLayout.LayoutParams(dp(50), -1));
        files.setOnClickListener(v -> runWine("wine explorer.exe"));

        TextView notepad = item("▤", 22, 0xFFDCEFFF);
        notepad.setGravity(Gravity.CENTER);
        taskbar.addView(notepad, new LinearLayout.LayoutParams(dp(47), -1));
        notepad.setOnClickListener(v -> runWine("wine notepad.exe"));

        View spacer = new View(activity);
        taskbar.addView(spacer, new LinearLayout.LayoutParams(0, 1, 1));

        clock = item("", 12, 0xFFEAF1FD);
        clock.setGravity(Gravity.CENTER);
        clock.setPadding(dp(5), 0, dp(10), 0);
        taskbar.addView(clock, new LinearLayout.LayoutParams(dp(116), -1));
        tick();
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private GradientDrawable shape(int color, int roundDp, int stroke) {
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(color);
        bg.setCornerRadius(dp(roundDp));
        bg.setStroke(dp(1), stroke);
        return bg;
    }

    private View line() {
        View v = new View(activity);
        v.setBackgroundColor(0xFF465365);
        return v;
    }

    private View separator() {
        View v = new View(activity);
        v.setBackgroundColor(0xFF4B5E73);
        return v;
    }

    private TextView item(String value, int size, int color) {
        TextView text = new TextView(activity);
        text.setText(value);
        text.setTextColor(color);
        text.setTextSize(size);
        text.setGravity(Gravity.CENTER_VERTICAL);
        return text;
    }

    private void addEntry(LinearLayout parent, String label, Runnable onTap) {
        TextView entry = item(label, 15, Color.WHITE);
        entry.setPadding(dp(10), 0, dp(10), 0);
        entry.setBackground(shape(0x223F638A, 5, 0x00445566));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(41));
        params.bottomMargin = dp(5);
        parent.addView(entry, params);
        entry.setOnClickListener(v -> onTap.run());
    }

    private void closeStart() {
        startMenu.setVisibility(View.GONE);
    }

    private void runWine(String command) {
        closeStart();
        if (activity.tclLaunchProgram(command) < 0) {
            new AlertDialog.Builder(activity)
                .setTitle("TCL Desktop 10")
                .setMessage("O programa nao conseguiu iniciar. Verifique o ambiente Wine e o Box64.")
                .setPositiveButton("OK", null)
                .show();
        }
    }

    private void showRunDialog() {
        closeStart();
        final EditText command = new EditText(activity);
        command.setSingleLine(true);
        command.setTextColor(0xFF202C3B);
        command.setHint("Ex.: notepad.exe ou C:\\\\programa.exe");
        command.setText("notepad.exe");
        new AlertDialog.Builder(activity)
            .setTitle("Executar programa Windows")
            .setMessage("Digite o caminho ou nome de um executavel compativel com Wine.")
            .setView(command)
            .setPositiveButton("Executar", (d, which) -> {
                String value = command.getText().toString().trim();
                if (!value.isEmpty()) runWine("wine " + value);
            })
            .setNegativeButton("Cancelar", null)
            .show();
    }

    private void tick() {
        if (!isAttachedToWindow()) return;
        clock.setText(new SimpleDateFormat("HH:mm\n dd/MM/yyyy", Locale.getDefault()).format(new Date()));
        handler.postDelayed(this::tick, 30000);
    }

    @Override protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        tick();
    }

    @Override protected void onDetachedFromWindow() {
        handler.removeCallbacksAndMessages(null);
        super.onDetachedFromWindow();
    }
}
