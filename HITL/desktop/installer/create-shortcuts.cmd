@echo off
setlocal

set "DESKTOP_LINK=%USERPROFILE%\Desktop\HITL Academic Writing Scorer.lnk"
set "START_MENU_LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\HITL Academic Writing Scorer.lnk"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$target=$env:HITL_APP_EXE; $work=Split-Path -LiteralPath $target -Parent; $ws=New-Object -ComObject WScript.Shell; foreach($link in @($env:DESKTOP_LINK,$env:START_MENU_LINK)){ $s=$ws.CreateShortcut($link); $s.TargetPath=$target; $s.WorkingDirectory=$work; $s.IconLocation=$target + ',0'; $s.Save() }"
exit /b %errorlevel%
