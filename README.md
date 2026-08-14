# AirPresent 🎯

> **Wireless Air Mouse & Presentation Remote for Windows**  
> Turn your phone into an intuitive air cursor and remote control for slideshows, presentations, and desktop navigation.

---

## 🌟 Key Features

- 🖱️ **Air Mouse Gyroscope Control**: Tilt or rotate your phone to control the mouse cursor smoothly on your presentation screen.
- 🔘 **Ergonomic Round Dial Controller**: Large, touch-friendly circular buttons for Left Click and Right Click.
- 📊 **Slide Controls**: Integrated `PREVIOUS`, `NEXT`, and `EXIT PRESENTATION (ESC)` buttons.
- 📱 **Dual Companion Options**:
  - **Universal Mobile Web App**: Open in Chrome/Safari on iOS or Android, or tap *Add to Home Screen*.
  - **Native Android APK**: High-frequency direct hardware sensor access without browser permissions.
- 💻 **Standalone Windows Executable**: Double-click `AirPresent.exe` on any Windows PC without installing Python.

---

## 🚀 Quick Start Guide

### Option A: Standalone Executable (Windows)

1. Launch `AirPresent.exe` on the presentation computer.
2. Note the LAN address (e.g., `http://192.168.1.10:8765`) shown in the console window.
3. Open that address on your mobile phone browser (or open the native **AirPresent** Android app).
4. Enter the 6-digit pairing passcode (`123456`) and tap **Connect**.
5. Tap **Start Air Cursor** and tilt your phone!

---

### Option B: Running from Source (Python)

Ensure Python 3.10+ is installed on your Windows PC:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/AirPresent.git
cd AirPresent

# Run the server
python server.py
```

---

## 📱 Mobile App (Android APK)

An `AirPresent.apk` file is provided directly in the root directory for Android users:

1. Copy `AirPresent.apk` to your Android device.
2. Install the APK (enable *Install from Unknown Sources* if prompted).
3. Enter your PC's IP address and tap **Connect Remote**.

---

## 🛠️ Building Executables from Source

### Building the Windows Executable (`.exe`)

PyInstaller packages Python and all web assets into a single standalone executable:

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --console --name "AirPresent" --add-data "phone_app;phone_app" server.py
```

The output executable will be created at `dist/AirPresent.exe`.

### Building the Android APK

Build using Gradle inside the `android-native` folder:

```bash
cd android-native
.\gradlew.bat assembleDebug
```

The compiled APK will be located at `android-native/app/build/outputs/apk/debug/app-debug.apk`.

---

## 📂 Project Structure

```
AirPresent/
├── AirPresent.exe             # Compiled standalone Windows receiver executable
├── AirPresent.apk             # Compiled native Android companion app
├── server.py                  # Desktop receiver server & Win32 API mouse controller
├── phone_app/                 # Glassmorphism mobile web application
│   ├── index.html             # HTML layout & PWA manifest link
│   ├── style.css              # Custom styling & dynamic round dial controls
│   ├── app.js                 # Web sensor handler & HTTP client
│   └── manifest.json          # PWA configuration
├── android-native/            # Native Android Studio project
│   ├── app/                   # Source code & AndroidManifest.xml
│   └── build.gradle           # Gradle build configuration
├── Run AirPresent.bat         # One-click launcher script
└── README.md                  # Documentation
```

---

## 🔒 Security Notice

AirPresent is designed for use on trusted local Wi-Fi networks (e.g., home, office, conference room). Both devices must be connected to the same LAN.

---

## 📄 License

MIT License. Free to modify and distribute.
