package com.winlator;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Shader;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.winlator.container.Container;
import com.winlator.container.ContainerManager;
import com.winlator.xenvironment.RootFS;
import com.winlator.xenvironment.RootFSInstaller;

/** Iniciador exclusivo do TCL Desktop 10; o motor de executaveis continua no Wine. */
public final class TclDesktopActivity extends Activity {
    private int dp(float value) {
        return (int)(getResources().getDisplayMetrics().density * value + 0.5f);
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        if (startExistingDesktop()) return;
        showWelcome();
    }

    private boolean startExistingDesktop() {
        try {
            RootFS filesystem = RootFS.find(this);
            if (!filesystem.isValid() || filesystem.getVersion() < RootFSInstaller.LATEST_VERSION)
                return false;
            ContainerManager manager = new ContainerManager(this);
            if (manager.getContainers().isEmpty()) return false;
            Container defaultContainer = manager.getContainers().get(0);
            Intent display = new Intent(this, XServerDisplayActivity.class);
            display.putExtra("container_id", defaultContainer.id);
            startActivity(display);
            finish();
            return true;
        } catch (RuntimeException ignored) {
            return false;
        }
    }

    private TextView action(String name, Runnable callback) {
        TextView view = new TextView(this);
        view.setText(name);
        view.setTextSize(15);
        view.setTextColor(0xFFFFFFFF);
        view.setGravity(Gravity.CENTER);
        view.setPadding(dp(14), dp(12), dp(14), dp(12));
        view.setBackgroundColor(0xEA20538B);
        view.setOnClickListener(v -> callback.run());
        return view;
    }

    private void openSettings() {
        startActivity(new Intent(this, MainActivity.class));
    }

    private void showWelcome() {
        FrameLayout screen = new FrameLayout(this);
        screen.addView(new DesktopWallpaper(), new FrameLayout.LayoutParams(-1, -1));
        setContentView(screen);

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(25), dp(25), dp(25), dp(70));
        screen.addView(page, new FrameLayout.LayoutParams(-1, -1));

        TextView title = new TextView(this);
        title.setText("TCL Desktop 10");
        title.setTextColor(0xFFFFFFFF);
        title.setTextSize(30);
        page.addView(title);

        TextView summary = new TextView(this);
        summary.setText("Configure o ambiente Windows para instalar e executar programas .exe.");
        summary.setTextColor(0xFFDDEAF8);
        summary.setTextSize(16);
        summary.setPadding(0, dp(14), 0, dp(20));
        page.addView(summary);

        page.addView(action("Configurar ambiente Windows", this::openSettings));

        FrameLayout taskbar = new FrameLayout(this);
        taskbar.setBackgroundColor(0xF00B192C);
        screen.addView(taskbar, new FrameLayout.LayoutParams(-1, dp(52), Gravity.BOTTOM));
        TextView start = action("⊞  Iniciar", this::openSettings);
        taskbar.addView(start, new FrameLayout.LayoutParams(dp(130), -1, Gravity.LEFT));

        TextView status = new TextView(this);
        status.setText("TCL 40 NXTPAPER 4G  •  Preparação inicial");
        status.setTextColor(0xFFE5F0FC);
        status.setGravity(Gravity.RIGHT | Gravity.CENTER_VERTICAL);
        status.setTextSize(12);
        status.setPadding(dp(6), 0, dp(12), 0);
        taskbar.addView(status, new FrameLayout.LayoutParams(-2, -1, Gravity.RIGHT));
    }

    private final class DesktopWallpaper extends View {
        private final Paint brush = new Paint(Paint.ANTI_ALIAS_FLAG);
        DesktopWallpaper() { super(TclDesktopActivity.this); }
        @Override protected void onDraw(Canvas canvas) {
            int width = getWidth(), height = getHeight();
            brush.setShader(new LinearGradient(0, 0, width, height,
                    0xFF031329, 0xFF1768AA, Shader.TileMode.CLAMP));
            canvas.drawRect(0, 0, width, height, brush);
            brush.setShader(null);
            brush.setColor(0x9968CFFF);
            brush.setStrokeWidth(dp(2));
            brush.setStyle(Paint.Style.STROKE);
            float cx = width * 0.68f;
            float cy = height * 0.45f;
            canvas.drawRect(cx - width * .13f, cy - height * .23f,
                    cx + width * .13f, cy + height * .23f, brush);
            canvas.drawLine(cx, cy - height * .23f, cx, cy + height * .23f, brush);
            canvas.drawLine(cx - width * .13f, cy, cx + width * .13f, cy, brush);
            brush.setStyle(Paint.Style.FILL);
        }
    }
}
