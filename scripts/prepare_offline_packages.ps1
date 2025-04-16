# Create directories for offline packages
$packagesDir = "packages"
$offlineDir = Join-Path $packagesDir "offline"
$pipDir = Join-Path $offlineDir "pip"

New-Item -ItemType Directory -Force -Path $pipDir

# Ensure requirements.txt has the latest dependencies
Write-Host "Checking for required packages..."
$requirementsContent = Get-Content -Path "requirements.txt" -Raw

# Check for nest-asyncio
if (-not ($requirementsContent -match "nest-asyncio")) {
    Write-Host "Adding nest-asyncio to requirements.txt"
    Add-Content -Path "requirements.txt" -Value "nest-asyncio>=1.5.8"
}

# Check for Flask-WTF (for CSRF protection)
if (-not ($requirementsContent -match "Flask-WTF")) {
    Write-Host "Adding Flask-WTF to requirements.txt"
    Add-Content -Path "requirements.txt" -Value "Flask-WTF>=1.0.1"
}

# Download pip packages for ARM64 platform
Write-Host "Downloading Python packages for ARM64..."
python -m pip download --platform manylinux_2_31_aarch64 --only-binary=:all: -r requirements.txt -d $pipDir

# Download platform-independent packages
Write-Host "Downloading platform-independent packages..."
python -m pip download --no-binary=:all: --no-deps -r requirements.txt -d $pipDir

# Create a README file with installation instructions
$readmePath = Join-Path $offlineDir "README.md"
$readmeContent = @"
# AMSLPR Offline Installation Package

## Installation Instructions

1. Copy the entire 'packages' directory to your Raspberry Pi
2. Install the packages using pip:

```bash
pip install --no-index --find-links=./packages/offline/pip -r requirements.txt
```

## Recent Changes

- Added CSRF token protection in camera form
- Added event loop initialization with nest-asyncio for async operations
- Added nest-asyncio package dependency

## Troubleshooting

If you encounter an internal server error when accessing the /cameras page, ensure that:
1. The nest-asyncio package is installed
2. Redis is running (for session management)
3. The CSRF protection is properly configured
"@

Set-Content -Path $readmePath -Value $readmeContent

Write-Host "Package download complete. Copy the entire 'packages' directory to your Raspberry Pi."
