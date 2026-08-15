@echo off
title AirPresent Firewall Fixer
echo ============================================================
echo   AirPresent Windows Firewall Configuration
echo ============================================================
echo.
echo Adding inbound firewall rule for AirPresent on port 8765...
echo.
netsh advfirewall firewall add rule name="AirPresent Remote Server (TCP-In)" dir=in action=allow protocol=TCP localport=8765
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Windows Firewall rule added successfully!
    echo Your phone will now connect instantly to AirPresent.
) else (
    echo [ERROR] Please RIGHT-CLICK this file and select "Run as administrator".
)
echo.
pause
