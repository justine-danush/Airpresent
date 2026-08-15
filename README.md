# AirPresent v2.0 🎯 Security & Instant QR Release

> **Wireless Air Mouse & Presentation Remote for Windows**  
> Turn your phone into a secure, motion-controlled air cursor for slideshows, presentations, and desktop navigation.

---

## 🌟 Key Features

- 📱 **Instant QR Code Auto-Pairing**: Point your phone camera at the ASCII QR Code on the PC screen to connect in 1 second!
- 🔐 **Dynamic 6-Digit Cryptographic PIN**: A new random security PIN is generated on server launch for strict authentication.
- 🛡️ **Timing-Safe Protection & Rate Limiting**: Built-in 256-bit session tokens, constant-time comparison, and brute-force protection.
- 🖱️ **Air Mouse Gyroscope Control**: Tilt or rotate your phone to control the mouse cursor smoothly.
- 🔘 **Ergonomic Round Dial Controller**: Large circular buttons for Left Click and Right Click.
- 📊 **Slide Controls**: Integrated `PREVIOUS`, `NEXT`, and `EXIT PRESENTATION (ESC)` buttons.
- 📱 **Dual Companion Options**:
  - **Universal Mobile Web App**: Open in Chrome/Safari on iOS or Android, or tap *Add to Home Screen*.
  - **Native Android Companion App**: High-frequency direct hardware sensor access with custom Adaptive Icon.
- 💻 **Standalone Windows Executable**: Double-click `AirPresent.exe` on any Windows PC without installing Python.

---

## 🚀 Quick Start Guide

### Option A: Instant QR Code Connection (Recommended)

1. Launch **`AirPresent.exe`** on your Windows presentation computer.
2. Point your phone's camera at the **ASCII QR Code** printed in the console window.
3. Open the link — your phone will connect and pair **automatically in 1 second**!

---

### Option B: Manual PIN Pairing

1. Launch `AirPresent.exe`.
2. Note the Web Address (e.g. `http://192.168.1.10:8765`) and 6-Digit PIN (e.g. `749312`).
3. Open that address on your phone browser or launch the native Android app.
4. Enter the 6-Digit PIN and tap **Connect Remote**.

---

## 🛠️ Building Executables from Source

### Building the Windows Executable (`.exe`)

```bash
pip install pyinstaller qrcode
python -m PyInstaller --noconfirm --onefile --console --name "AirPresent" --icon "icon.ico" --add-data "phone_app;phone_app" server.py
```

### Building the Android APK (`.apk`)

```bash
cd android-native
.\gradlew.bat assembleDebug
```

---

## 📂 Project Structure

```
AirPresent/
├── AirPresent.exe             # Compiled standalone Windows receiver (v2.0 Security & QR)
├── AirPresent.apk             # Compiled native Android companion app (v2.0)
├── server.py                  # Desktop receiver server with dynamic PIN & ASCII QR generator
├── phone_app/                 # Glassmorphism mobile web application
│   ├── index.html             # HTML layout & PWA manifest link
│   ├── style.css              # Custom styling & dynamic round dial controls
│   └── app.js                 # Auto-pairing URL hash handler & HTTP client
├── android-native/            # Native Android Studio project
│   ├── app/                   # Source code & AndroidManifest.xml
│   └── build.gradle           # Gradle build configuration
├── icon.ico                   # Windows application icon
└── README.md                  # Documentation
```

---

## 📄 License

MIT License. Free to modify and distribute.
