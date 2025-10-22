; Inno Setup 配置文件
; Basler 工業視覺系統 Windows 安裝程序
;
; 使用方法：
; 1. 在 Windows 上安裝 Inno Setup: https://jrsoftware.org/isdl.php
; 2. 使用 PyInstaller 打包應用程式到 dist/BaslerVisionSystem
; 3. 使用 Inno Setup Compiler 編譯此腳本
; 4. 輸出: releases/BaslerVision_Setup_v{version}.exe

#define MyAppName "Basler Vision System"
#define MyAppVersion GetEnv('APP_VERSION')
#define MyAppPublisher "Basler Industrial Vision"
#define MyAppExeName "BaslerVisionSystem.exe"
#define MyAppAssocName MyAppName + " 專案文件"
#define MyAppAssocExt ".bvp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; 基本信息
AppId={{B7A8E5D4-9C3F-4A12-8E6B-5D4C9A7E3B2F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\BaslerVisionSystem
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; LicenseFile=..\LICENSE  ; 註釋掉（專案中沒有 LICENSE 文件）
OutputDir=..\releases
OutputBaseFilename=BaslerVision_Setup_v{#MyAppVersion}
; SetupIconFile=..\resources\icon.ico  ; 註釋掉（icon.ico 文件尚未創建）
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; 系統需求
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; 權限
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; 主應用程式（PyInstaller 打包輸出）
Source: "..\dist\BaslerVisionSystem\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\BaslerVisionSystem\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 配置文件
Source: "..\basler_pyqt6\config\detection_params.json"; DestDir: "{app}\config"; Flags: ignoreversion

; 文檔
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; 關聯文件類型（可選）
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".myp"; ValueData: ""

[Code]
// 檢查是否已安裝舊版本
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

// 卸載舊版本
function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES','', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

// 安裝前處理
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then
  begin
    if (IsUpgrade()) then
    begin
      UnInstallOldVersion();
    end;
  end;
end;
