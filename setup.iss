[Setup]
AppId={{F1A2E8D5-9C42-4E7B-A891-3D5F2E7B9C1A}}
AppName=AI Transcription PC
AppVersion=1.0.0
AppPublisher=AI Transcription
DefaultDirName={localappdata}\Programs\AI Transcription PC
DefaultGroupName=AI Transcription PC
DisableProgramGroupPage=yes
OutputDir=.\dist-installer
OutputBaseFilename=AITranscriptionPCSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Files]
Source: ".\dist\AITranscriptionPC\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AI Transcription PC"; Filename: "{app}\AI Transcription PC.exe"
Name: "{userstartup}\AI Transcription PC"; Filename: "{app}\AI Transcription PC.exe"; Tasks: startupshortcut
Name: "{userdesktop}\AI Transcription PC"; Filename: "{app}\AI Transcription PC.exe"

[Tasks]
Name: "startupshortcut"; Description: "Run AI Transcription PC when I sign in"; Flags: unchecked

[Run]
Filename: "{app}\AI Transcription PC.exe"; Description: "Launch AI Transcription PC now"; Flags: nowait postinstall skipifsilent
