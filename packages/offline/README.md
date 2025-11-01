# VisiGate Offline Installation Package

## Installation Instructions

1. Copy the entire 'packages' directory to your Raspberry Pi
2. Install the packages using pip:

`ash
pip install --no-index --find-links=./packages/offline/pip -r requirements.txt
`

## Recent Changes

- Added CSRF token protection in camera form
- Added event loop initialization with nest-asyncio for async operations
- Added nest-asyncio package dependency

## Troubleshooting

If you encounter an internal server error when accessing the /cameras page, ensure that:
1. The nest-asyncio package is installed
2. Redis is running (for session management)
3. The CSRF protection is properly configured
