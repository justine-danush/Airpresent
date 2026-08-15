; AirPresent Professional Windows Installer Script (Inno Setup 6)

[Setup]
AppName=AirPresent Wireless Air Remote
AppVersion=2.1.0
AppPublisher=AirPresent
AppPublisherURL=https://github.com/justine-danush/Airpresent
DefaultDirName={autopf}\AirPresent
DefaultGroupName=AirPresent
UninstallDisplayIcon={app}\AirPresent.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=.
OutputBaseFilename=AirPresent_Setup
PrivilegesRequired=admin
SetupIconFile=icon.ico
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "AirPresent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "phone_app\*"; DestDir: "{app}\phone_app"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AirPresent"; Filename: "{app}\AirPresent.exe"
Name: "{autodesktop}\AirPresent"; Filename: "{app}\AirPresent.exe"; Tasks: desktopicon

[Run]
; Remove any existing BLOCK rules created by Windows Firewall
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""airpresent.exe"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""AirPresent"""; Flags: runhidden

; Add explicit ALLOW rules on ALL network profiles (Private, Public, Domain)
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""AirPresent Program"" dir=in action=allow program=""{app}\AirPresent.exe"" enable=yes profile=any"; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""AirPresent Port 8765"" dir=in action=allow protocol=TCP localport=8765 enable=yes profile=any"; Flags: runhidden

Filename: "{app}\AirPresent.exe"; Description: "Launch AirPresent Remote Server"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""AirPresent Program"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""AirPresent Port 8765"""; Flags: runhidden
