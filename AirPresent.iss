; AirPresent Professional Windows Installer Script (Inno Setup 6)
; Automates app deployment, desktop shortcuts, and Windows Firewall rule creation.

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
OutputBaseFilename=AirPresent_Setup_v2.1.0
PrivilegesRequired=admin
SetupIconFile=icon.ico
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "AirPresent.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\AirPresent"; Filename: "{app}\AirPresent.exe"
Name: "{autodesktop}\AirPresent"; Filename: "{app}\AirPresent.exe"; Tasks: desktopicon

[Run]
; Automatically register Windows Defender Firewall Rule for port 8765 during installation
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""AirPresent Remote Server (TCP-In)"" dir=in action=allow protocol=TCP localport=8765"; Flags: runhidden
Filename: "{app}\AirPresent.exe"; Description: "Launch AirPresent Remote Server"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Automatically clean up firewall rule on uninstall
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""AirPresent Remote Server (TCP-In)"""; Flags: runhidden
