@echo off
REM Git Push Script for VisionGate Deployment (Windows Version)
REM This batch file will execute the git push script using Git Bash

echo === VisionGate Git Push Script (Windows) ===
echo Preparing to push deployment files to repository...

REM Check if Git Bash is available
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git for Windows from https://git-scm.com/
    pause
    exit /b 1
)

REM Execute the git push script using Git Bash
echo Executing git push script...
bash -c "./git-push.sh"

echo.
echo === Git Push Complete ===
echo.
echo Next steps:
echo 1. SSH into your VPS: ssh visiongate@your-vps-ip
echo 2. Navigate to app directory: cd /home/visiongate/visiongate-app
echo 3. Pull latest changes: git pull
echo 4. Make scripts executable: chmod +x deploy.sh backup.sh
echo 5. Run deployment script: ./deploy.sh
echo.
echo Your VisionGate application will be deployed to your VPS!
pause