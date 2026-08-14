package com.airpresent.remote;

import android.app.*;
import android.os.*;
import android.hardware.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.*;

/** Native Android companion: reads the gyroscope directly, not through Chrome. */
public class MainActivity extends Activity implements SensorEventListener {
  private final ExecutorService io = Executors.newSingleThreadExecutor();
  private final AtomicBoolean motionSending = new AtomicBoolean(false);
  private float pendingDx = 0f, pendingDy = 0f;

  private SensorManager sensors; private Sensor motionSensor; private boolean useGyroscope; private String token = "";
  private TextView state; private TextView statusDot; private EditText address; private Button airButton; private boolean airOn = false;
  private float lastX, lastY; private long lastMove;

  @Override public void onCreate(Bundle saved) {
    super.onCreate(saved);
    sensors = (SensorManager) getSystemService(SENSOR_SERVICE);
    motionSensor = sensors.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
    useGyroscope = motionSensor != null;
    if (motionSensor == null) {
      motionSensor = sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
    }
    buildUi();
  }

  private int dpToPx(int dp) {
    return Math.round(dp * getResources().getDisplayMetrics().density);
  }

  private GradientDrawable roundedDrawable(int startColor, int endColor, float radius, int strokeColor, int strokeWidth) {
    GradientDrawable d = (startColor == endColor) ? new GradientDrawable() : new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT, new int[]{startColor, endColor});
    d.setShape(GradientDrawable.RECTANGLE);
    d.setCornerRadius(radius);
    if (startColor == endColor) d.setColor(startColor);
    if (strokeWidth > 0) d.setStroke(strokeWidth, strokeColor);
    return d;
  }

  private TextView createLabel(String text, float size, int color, boolean bold) {
    TextView v = new TextView(this);
    v.setText(text);
    v.setTextSize(size);
    v.setTextColor(color);
    v.setGravity(Gravity.CENTER);
    if (bold) v.setTypeface(Typeface.DEFAULT_BOLD);
    return v;
  }

  private Button createStyledButton(String text, int startColor, int endColor, int textColor, float radius, View.OnClickListener click) {
    Button b = new Button(this);
    b.setText(text);
    b.setTextSize(17);
    b.setTextColor(textColor);
    b.setTypeface(Typeface.DEFAULT_BOLD);
    b.setBackground(roundedDrawable(startColor, endColor, radius, 0, 0));
    b.setPadding(dpToPx(24), dpToPx(18), dpToPx(24), dpToPx(18));
    b.setOnClickListener(click);
    b.setElevation(6f);
    return b;
  }

  private Button createCircleButton(String text, int startColor, int endColor, View.OnClickListener click) {
    Button b = new Button(this);
    b.setText(text);
    b.setTextSize(15);
    b.setTextColor(Color.WHITE);
    b.setTypeface(Typeface.DEFAULT_BOLD);
    b.setGravity(Gravity.CENTER);

    GradientDrawable d = new GradientDrawable(GradientDrawable.Orientation.TL_BR, new int[]{startColor, endColor});
    d.setShape(GradientDrawable.OVAL);
    d.setStroke(dpToPx(2), Color.argb(80, 255, 255, 255));
    b.setBackground(d);
    b.setOnClickListener(click);
    b.setElevation(8f);

    int size = dpToPx(118);
    LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(size, size);
    lp.setMargins(dpToPx(10), dpToPx(10), dpToPx(10), dpToPx(10));
    b.setLayoutParams(lp);
    return b;
  }

  private void buildUi() {
    ScrollView scroll = new ScrollView(this);
    scroll.setFillViewport(true);
    scroll.setBackgroundColor(Color.rgb(11, 15, 25));

    LinearLayout root = new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setGravity(Gravity.CENTER);
    root.setPadding(dpToPx(24), dpToPx(36), dpToPx(24), dpToPx(36));

    // Brand Header
    LinearLayout header = new LinearLayout(this);
    header.setOrientation(LinearLayout.HORIZONTAL);
    header.setGravity(Gravity.CENTER);
    
    TextView title = createLabel("AirPresent", 30, Color.WHITE, true);
    TextView proBadge = createLabel(" PRO", 12, Color.rgb(56, 189, 248), true);
    proBadge.setBackground(roundedDrawable(Color.argb(35, 56, 189, 248), Color.argb(35, 56, 189, 248), 12f, Color.argb(80, 56, 189, 248), 2));
    proBadge.setPadding(dpToPx(10), dpToPx(4), dpToPx(10), dpToPx(4));

    header.addView(title);
    header.addView(proBadge);
    root.addView(header);

    // Status Pill Card
    LinearLayout statusPill = new LinearLayout(this);
    statusPill.setOrientation(LinearLayout.HORIZONTAL);
    statusPill.setGravity(Gravity.CENTER);
    statusPill.setPadding(dpToPx(20), dpToPx(12), dpToPx(20), dpToPx(12));
    statusPill.setBackground(roundedDrawable(Color.rgb(22, 31, 48), Color.rgb(22, 31, 48), 24f, Color.argb(30, 255, 255, 255), 1));
    
    LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    statusParams.setMargins(0, dpToPx(16), 0, dpToPx(20));
    statusPill.setLayoutParams(statusParams);

    statusDot = createLabel("● ", 16, Color.rgb(245, 158, 11), true);
    state = createLabel("Enter PC address and connect.", 14, Color.rgb(148, 163, 184), false);
    statusPill.addView(statusDot);
    statusPill.addView(state);
    root.addView(statusPill);

    // Connection Card
    LinearLayout connCard = new LinearLayout(this);
    connCard.setOrientation(LinearLayout.VERTICAL);
    connCard.setGravity(Gravity.CENTER);
    connCard.setPadding(dpToPx(20), dpToPx(20), dpToPx(20), dpToPx(20));
    connCard.setBackground(roundedDrawable(Color.rgb(22, 31, 48), Color.rgb(22, 31, 48), 28f, Color.argb(20, 255, 255, 255), 1));

    address = new EditText(this);
    address.setHint("192.168.0.101:8765");
    address.setText("192.168.0.101:8765");
    address.setTextColor(Color.WHITE);
    address.setHintTextColor(Color.rgb(100, 116, 139));
    address.setTextSize(18);
    address.setGravity(Gravity.CENTER);
    address.setBackground(roundedDrawable(Color.rgb(15, 23, 42), Color.rgb(15, 23, 42), 18f, Color.argb(40, 255, 255, 255), 1));
    address.setPadding(dpToPx(16), dpToPx(16), dpToPx(16), dpToPx(16));

    LinearLayout.LayoutParams addrParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    addrParams.setMargins(0, 0, 0, dpToPx(16));
    address.setLayoutParams(addrParams);
    connCard.addView(address);

    Button connectBtn = createStyledButton("CONNECT REMOTE", Color.rgb(56, 189, 248), Color.rgb(129, 140, 248), Color.rgb(11, 15, 25), 18f, v -> pair());
    LinearLayout.LayoutParams connBtnParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    connectBtn.setLayoutParams(connBtnParams);
    connCard.addView(connectBtn);
    root.addView(connCard);

    // Hero Air Cursor Toggle Button
    airButton = createStyledButton("START AIR CURSOR", Color.rgb(56, 189, 248), Color.rgb(59, 130, 246), Color.rgb(11, 15, 25), 24f, v -> {
      airOn = !airOn;
      updateAirButtonState();
      lastX = lastY = 0;
    });
    LinearLayout.LayoutParams airParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    airParams.setMargins(0, dpToPx(20), 0, dpToPx(20));
    airButton.setLayoutParams(airParams);
    airButton.setPadding(dpToPx(24), dpToPx(22), dpToPx(24), dpToPx(22));
    airButton.setTextSize(19);
    root.addView(airButton);

    // ROUND DIAL CONTROLLER for Left & Right Click
    LinearLayout dialHousing = new LinearLayout(this);
    dialHousing.setOrientation(LinearLayout.HORIZONTAL);
    dialHousing.setGravity(Gravity.CENTER);
    dialHousing.setPadding(dpToPx(12), dpToPx(12), dpToPx(12), dpToPx(12));
    dialHousing.setBackground(roundedDrawable(Color.argb(25, 255, 255, 255), Color.argb(10, 255, 255, 255), 999f, Color.argb(40, 255, 255, 255), 2));

    LinearLayout.LayoutParams dialParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    dialParams.setMargins(0, 0, 0, dpToPx(20));
    dialHousing.setLayoutParams(dialParams);

    Button leftCircle = createCircleButton("LEFT\nCLICK", Color.rgb(129, 140, 248), Color.rgb(99, 102, 241), v -> send("{\"type\":\"click\",\"button\":\"left\"}"));
    Button rightCircle = createCircleButton("RIGHT\nCLICK", Color.rgb(45, 212, 191), Color.rgb(20, 184, 166), v -> send("{\"type\":\"click\",\"button\":\"right\"}"));

    dialHousing.addView(leftCircle);
    dialHousing.addView(rightCircle);
    root.addView(dialHousing);

    // Slide Controls Grid (2 columns)
    LinearLayout slidesRow = new LinearLayout(this);
    slidesRow.setOrientation(LinearLayout.HORIZONTAL);
    LinearLayout.LayoutParams p1 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
    p1.setMargins(0, 0, dpToPx(8), dpToPx(16));
    LinearLayout.LayoutParams p2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
    p2.setMargins(dpToPx(8), 0, 0, dpToPx(16));

    Button prevBtn = createStyledButton("‹ PREVIOUS", Color.rgb(30, 41, 59), Color.rgb(30, 41, 59), Color.rgb(226, 232, 240), 18f, v -> send("{\"type\":\"key\",\"key\":\"previous\"}"));
    Button nextBtn = createStyledButton("NEXT ›", Color.argb(80, 56, 189, 248), Color.argb(80, 59, 130, 246), Color.WHITE, 18f, v -> send("{\"type\":\"key\",\"key\":\"next\"}"));
    slidesRow.addView(prevBtn, p1);
    slidesRow.addView(nextBtn, p2);
    root.addView(slidesRow);

    // Exit Button
    Button escapeBtn = createStyledButton("EXIT PRESENTATION (ESC)", Color.argb(35, 244, 63, 94), Color.argb(35, 244, 63, 94), Color.rgb(253, 164, 175), 18f, v -> send("{\"type\":\"key\",\"key\":\"escape\"}"));
    LinearLayout.LayoutParams escParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    escapeBtn.setLayoutParams(escParams);
    root.addView(escapeBtn);

    scroll.addView(root);
    setContentView(scroll);
  }

  private void updateAirButtonState() {
    if (airButton == null) return;
    if (airOn) {
      airButton.setText("PAUSE AIR CURSOR");
      airButton.setBackground(roundedDrawable(Color.rgb(16, 185, 129), Color.rgb(5, 150, 105), 24f, 0, 0));
      airButton.setTextColor(Color.WHITE);
      statusDot.setTextColor(Color.rgb(56, 189, 248));
      state.setText(useGyroscope ? "Gyro active — rotate wrist" : "Motion active — tilt phone");
    } else {
      airButton.setText("START AIR CURSOR");
      airButton.setBackground(roundedDrawable(Color.rgb(56, 189, 248), Color.rgb(59, 130, 246), 24f, 0, 0));
      airButton.setTextColor(Color.rgb(11, 15, 25));
      statusDot.setTextColor(token.isEmpty() ? Color.rgb(245, 158, 11) : Color.rgb(16, 185, 129));
      state.setText(token.isEmpty() ? "Enter PC address and connect." : "Connected to PC");
    }
  }

  private String base() {
    return "http://" + address.getText().toString().trim();
  }

  private void pair() {
    io.execute(() -> {
      try {
        String result = post("/pair", "{\"code\":\"123456\"}");
        Matcher match = Pattern.compile("\\\"token\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"").matcher(result);
        if (!match.find()) throw new IOException("No session token");
        token = match.group(1);
        runOnUiThread(() -> {
          statusDot.setTextColor(Color.rgb(16, 185, 129));
          state.setText("Connected. Ready for motion.");
          updateAirButtonState();
        });
      } catch (Exception e) {
        runOnUiThread(() -> {
          statusDot.setTextColor(Color.rgb(244, 63, 94));
          state.setText("Could not connect: " + e.getMessage());
        });
      }
    });
  }

  private String post(String path, String json) throws Exception {
    HttpURLConnection c = (HttpURLConnection) new URL(base() + path).openConnection();
    c.setRequestMethod("POST");
    c.setRequestProperty("Content-Type", "application/json");
    c.setDoOutput(true);
    try (OutputStream o = c.getOutputStream()) {
      o.write(json.getBytes(StandardCharsets.UTF_8));
    }
    if (c.getResponseCode() != 200) throw new IOException("HTTP " + c.getResponseCode());
    try (InputStream i = c.getInputStream()) {
      return new String(i.readAllBytes(), StandardCharsets.UTF_8);
    }
  }

  private void send(String event) {
    if (token.isEmpty()) return;
    io.execute(() -> {
      try {
        post("/control", event.substring(0, event.length() - 1) + ",\"token\":\"" + token + "\"}");
      } catch (Exception ignored) {}
    });
  }

  private void sendMotion(float dx, float dy) {
    if (token.isEmpty()) return;
    synchronized (this) {
      pendingDx += dx;
      pendingDy += dy;
    }
    if (motionSending.compareAndSet(false, true)) {
      io.execute(() -> {
        try {
          float sendDx, sendDy;
          synchronized (this) {
            sendDx = pendingDx;
            sendDy = pendingDy;
            pendingDx = 0f;
            pendingDy = 0f;
          }
          post("/control", "{\"type\":\"move\",\"dx\":" + sendDx + ",\"dy\":" + sendDy + ",\"token\":\"" + token + "\"}");
        } catch (Exception ignored) {
        } finally {
          motionSending.set(false);
        }
      });
    }
  }

  @Override public void onResume() {
    super.onResume();
    if (motionSensor != null) sensors.registerListener(this, motionSensor, SensorManager.SENSOR_DELAY_GAME);
  }

  @Override public void onPause() {
    sensors.unregisterListener(this);
    super.onPause();
  }

  @Override public void onSensorChanged(SensorEvent e) {
    if (!airOn || token.isEmpty()) return;
    long now = SystemClock.elapsedRealtime();
    if (now - lastMove < 20) return;

    float dx, dy;
    if (useGyroscope) {
      dx = (e.values[1] + e.values[2]) * 45f;
      dy = e.values[0] * 45f;
    } else {
      float x = e.values[0], y = e.values[1];
      if (lastX == 0 && lastY == 0) { lastX = x; lastY = y; return; }
      dx = (x - lastX) * 400f;
      dy = (y - lastY) * 400f;
      lastX = x; lastY = y;
    }
    lastMove = now;

    if (Math.abs(dx) > 0.05f || Math.abs(dy) > 0.05f) {
      sendMotion(dx, dy);
      runOnUiThread(() -> {
        statusDot.setTextColor(Color.rgb(56, 189, 248));
        state.setText("Motion active — cursor moving");
      });
    }
  }

  @Override public void onAccuracyChanged(Sensor s, int a) {}

  @Override public void onDestroy() {
    io.shutdownNow();
    super.onDestroy();
  }
}



