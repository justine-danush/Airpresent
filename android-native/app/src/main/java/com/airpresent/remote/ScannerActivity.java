package com.airpresent.remote;

import android.app.Activity;
import android.os.Bundle;
import android.view.KeyEvent;
import com.journeyapps.barcodescanner.CaptureManager;
import com.journeyapps.barcodescanner.DecoratedBarcodeView;

/** Custom QR Scanner Activity to prevent theme & classloader crashes. */
public class ScannerActivity extends Activity {
  private CaptureManager capture;
  private DecoratedBarcodeView barcodeScannerView;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    barcodeScannerView = new DecoratedBarcodeView(this);
    barcodeScannerView.setStatusText("Point camera at AirPresent QR Code on PC screen");
    setContentView(barcodeScannerView);

    capture = new CaptureManager(this, barcodeScannerView);
    capture.initializeFromIntent(getIntent(), savedInstanceState);
    capture.setShowMissingCameraPermissionDialog(false);
    capture.decode();
  }

  @Override
  protected void onResume() {
    super.onResume();
    if (capture != null) capture.onResume();
  }

  @Override
  protected void onPause() {
    if (capture != null) capture.onPause();
    super.onPause();
  }

  @Override
  protected void onDestroy() {
    if (capture != null) capture.onDestroy();
    super.onDestroy();
  }

  @Override
  protected void onSaveInstanceState(Bundle outState) {
    super.onSaveInstanceState(outState);
    if (capture != null) capture.onSaveInstanceState(outState);
  }

  @Override
  public boolean onKeyDown(int keyCode, KeyEvent event) {
    return (barcodeScannerView != null && barcodeScannerView.onKeyDown(keyCode, event)) || super.onKeyDown(keyCode, event);
  }
}
