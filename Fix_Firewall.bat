@echo off
title AirPresent Firewall Unblocker & Configurator
echo ============================================================
echo   AirPresent Windows Firewall Unblocker
echo ============================================================
echo.
echo 1. Removing any existing Windows Firewall BLOCK rules...
netsh advfirewall firewall delete rule name="airpresent.exe"
netsh advfirewall firewall delete rule name="AirPresent"
netsh advfirewall firewall delete rule name="AirPresent Remote Server (TCP-In)"
netsh advfirewall firewall delete rule name="AirPresent Port 8765"

echo.
echo 2. Adding explicit ALLOW rules for AirPresent on all network profiles...
netsh advfirewall firewall add rule name="AirPresent Program" dir=in action=allow program="%~dp0AirPresent.exe" enable=yes profile=any
netsh advfirewall firewall add rule name="AirPresent Port 8765" dir=in action=allow protocol=TCP localport=8765 enable=yes profile=any

echo.
if %errorlevel% equ 0 (
    echo ============================================================
    echo [SUCCESS] Firewall BLOCK rules removed and ALLOW rules added!
    echo Your phone will now connect instantly.
    echo ============================================================
) else (
    echo [ERROR] Please RIGHT-CLICK this file and select "Run as administrator".
)
echo.
pause
