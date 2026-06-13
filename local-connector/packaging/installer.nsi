; DaePoint Local Connector - NSIS Installer
; Requires: NSIS 3.x with Modern UI 2

!include "MUI2.nsh"
!include "LogicLib.nsh"

; ─── General ───
Name "DaePoint Local Connector"
OutFile "DaePointConnector-Setup.exe"
InstallDir "$LOCALAPPDATA\DaePoint\Connector"
InstallDirRegKey HKCU "Software\DaePoint\Connector" "InstallDir"
RequestExecutionLevel user
Unicode True

; ─── Version Info (will be overridden by build script if needed) ───
!define VERSION "2.0.0"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "DaePoint Local Connector"
VIAddVersionKey "FileDescription" "Hardware Connector para DaePoint POS"
VIAddVersionKey "LegalCopyright" "DaePoint POS 2026"
VIAddVersionKey "FileVersion" "${VERSION}"

; ─── Interface ───
!define MUI_ABORTWARNING

; ─── Pages ───
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Spanish"

; ─── Installer Sections ───
Section "DaePoint Local Connector" SecMain
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Files from PyInstaller output
    File /r "dist\DaePointConnector\*.*"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Registry keys
    WriteRegStr HKCU "Software\DaePoint\Connector" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\DaePoint\Connector" "Version" "${VERSION}"

    ; Uninstall registry key
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DaePointConnector" \
        "DisplayName" "DaePoint Local Connector"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DaePointConnector" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DaePointConnector" \
        "DisplayVersion" "${VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DaePointConnector" \
        "Publisher" "DaePoint POS"

    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\DaePoint"
    CreateShortCut "$SMPROGRAMS\DaePoint\DaePoint Local Connector.lnk" "$INSTDIR\DaePointConnector.exe"
    CreateShortCut "$SMPROGRAMS\DaePoint\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

    ; Desktop shortcut
    CreateShortCut "$DESKTOP\DaePoint Local Connector.lnk" "$INSTDIR\DaePointConnector.exe"

    ; Firewall rule (allow localhost only)
    nsExec::ExecToLog 'netsh advfirewall firewall add rule name="DaePoint Connector" dir=in action=allow program="$INSTDIR\DaePointConnector.exe" enable=yes profile=any remoteip=127.0.0.1'

SectionEnd

; ─── Auto-start Option ───
Section "Iniciar con Windows" SecAutoStart
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "DaePointConnector" '"$INSTDIR\DaePointConnector.exe" --minimized'
SectionEnd

; ─── Uninstaller ───
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$SMPROGRAMS\DaePoint\DaePoint Local Connector.lnk"
    Delete "$SMPROGRAMS\DaePoint\Uninstall.lnk"
    RMDir "$SMPROGRAMS\DaePoint"
    Delete "$DESKTOP\DaePoint Local Connector.lnk"

    ; Remove registry keys
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "DaePointConnector"
    DeleteRegKey HKCU "Software\DaePoint\Connector"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DaePointConnector"

    ; Remove firewall rules
    nsExec::ExecToLog 'netsh advfirewall firewall delete rule name="DaePoint Connector"'
SectionEnd

; ─── Callbacks ───
Function .onInit
    ; Check if already installed
    ReadRegStr $0 HKCU "Software\DaePoint\Connector" "InstallDir"
    ${If} $0 != ""
        MessageBox MB_YESNO|MB_ICONQUESTION "DaePoint Connector ya esta instalado. Desea reinstalarlo?" IDYES +2
        Abort
    ${EndIf}
FunctionEnd
