; ============================================================================
; Inno Setup 配置文件
; Basler Vision System (C++ 版本) Windows 安裝程序
; ============================================================================
;
; 使用方法：
; 1. 在 Windows 上安裝 Inno Setup: https://jrsoftware.org/isdl.php
; 2. 使用 CMake 編譯 C++ 專案
; 3. 使用 Inno Setup Compiler 編譯此腳本
; 4. 輸出: releases/BaslerVisionSystem_v{version}_Setup.exe
;
; ============================================================================

#define MyAppName "Basler Vision System"
#define MyAppVersion GetEnv('APP_VERSION')
#if MyAppVersion == ""
#define MyAppVersion "2.0.0"
#endif
#define MyAppPublisher "Basler Industrial Vision"
#define MyAppURL "https://github.com/your-repo/Real-time_item_monitoring_system"
#define MyAppExeName "BaslerVisionSystem.exe"
#define MyAppAssocName MyAppName + " 專案文件"
#define MyAppAssocExt ".bvp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; 基本信息
AppId={{C8B9F6E5-AD4G-5B23-9F7C-6E5D0B8F4C3A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\BaslerVisionSystem
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 輸出配置
OutputDir=..\..\releases
OutputBaseFilename=BaslerVisionSystem_v{#MyAppVersion}_Setup
SetupIconFile=..\assets\setup_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; 安裝精靈圖片
WizardImageFile=..\assets\wizard_image.bmp
WizardSmallImageFile=..\assets\wizard_small.bmp

; 壓縮配置
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4

; 安裝精靈樣式
WizardStyle=modern
WizardResizable=no
WizardSizePercent=100

; 系統需求
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; 權限
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 安裝日誌
SetupLogging=yes

[Languages]
; 注意：中文語言文件需要額外安裝，CI 環境僅使用英文
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
english.BeveledLabel=Basler Vision System (C++ Edition)

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; ============================================================================
; 主應用程式
; ============================================================================
Source: "..\build\Release\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; ============================================================================
; Qt6 依賴庫 (由 windeployqt 生成)
; ============================================================================
Source: "..\build\Release\*.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\build\Release\platforms\*"; DestDir: "{app}\platforms"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\build\Release\styles\*"; DestDir: "{app}\styles"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\build\Release\imageformats\*"; DestDir: "{app}\imageformats"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\build\Release\multimedia\*"; DestDir: "{app}\multimedia"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\build\Release\tls\*"; DestDir: "{app}\tls"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\build\Release\networkinformation\*"; DestDir: "{app}\networkinformation"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ============================================================================
; Assets 資源文件
; ============================================================================
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; ============================================================================
; 配置文件
; ============================================================================
Source: "..\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ============================================================================
; Visual C++ Runtime (如需要)
; ============================================================================
Source: "vcredist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist

; ============================================================================
; 文檔
; ============================================================================
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
; 創建額外目錄
Name: "{app}\recordings"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\config"; Permissions: users-modify

[Icons]
; 開始選單
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\使用手冊"; Filename: "{app}\README.md"

; 桌面圖標
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"

; 快速啟動
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; 安裝 Visual C++ Runtime (如果存在)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet /norestart"; StatusMsg: "正在安裝 Visual C++ Runtime..."; Flags: waituntilterminated skipifdoesntexist

; 啟動應用程式
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; 關聯文件類型
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".bvp"; ValueData: ""

; 應用程式路徑
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"

[UninstallDelete]
; 卸載時刪除的文件和目錄
Type: filesandordirs; Name: "{app}\logs"
Type: dirifempty; Name: "{app}\recordings"
Type: dirifempty; Name: "{app}\config"

[Code]
// ============================================================================
// Pascal Script 區段
// ============================================================================

var
  DownloadPage: TDownloadWizardPage;

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

// 判斷是否為升級安裝
function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

// 卸載舊版本
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

// 初始化安裝程序
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// 準備安裝前的處理
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then begin
    if (IsUpgrade()) then begin
      UnInstallOldVersion();
    end;
  end;
end;

// 注意：移除了自定義的 DirExists 和 FileExists 函數
// 因為它們會導致無限遞迴錯誤
// 現在使用 skipifsourcedoesntexist flag 代替 Check 函數

// 安裝後的處理
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then begin
    // 可以在這裡添加安裝完成後的處理
  end;
end;

// 卸載前確認
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox('確定要卸載 {#MyAppName} 嗎？', mbConfirmation, MB_YESNO) = IDYES;
end;

// 卸載後清理
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then begin
    // 清理用戶數據（可選）
    if MsgBox('是否刪除所有配置文件和用戶數據？', mbConfirmation, MB_YESNO) = IDYES then begin
      DelTree(ExpandConstant('{app}'), True, True, True);
    end;
  end;
end;
