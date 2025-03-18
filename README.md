# Automate Systems License Plate Recognition (AMSLPR)

![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview
AMSLPR is a production-ready Raspberry Pi-based license plate recognition system designed for barrier control and parking management. The system automatically detects and recognizes license plates, controls entry/exit barriers, and manages authorized vehicles with enterprise-grade security, reliability, and performance features.

## Features
- Fast, accurate license plate detection and recognition
- Direct barrier control integration
- Authorized vehicle database management
- Parking duration tracking and reporting
- Web-based administration interface
- Offline operation capability
- Comprehensive statistics and analytics dashboard
- PDF report generation (daily, weekly, monthly)
- Unauthorized access notifications (email, SMS, webhook)
- ONVIF IP camera integration for flexible deployment
- SSL/TLS support for secure communications
- Rate limiting and security headers for web interface
- System monitoring and error handling
- Production-ready deployment with Nginx
- High availability and redundancy options

## Production-Ready Features

### Security
- SSL/TLS encryption for all communications
- Role-based access control with secure authentication
- API token-based authentication
- Rate limiting to prevent abuse
- Security headers to prevent common web vulnerabilities
- Input validation and sanitization
- Secure password storage with PBKDF2-SHA256

### Reliability
- Comprehensive error handling and recovery
- Automatic service restart on failure
- Database integrity checks and automatic recovery
- Graceful degradation during partial system failures
- Regular automated backups

### Performance
- Optimized recognition pipeline for Raspberry Pi
- Database query optimization
- Asset minification and caching
- Efficient resource usage monitoring

### Monitoring
- Real-time system resource monitoring
- Performance metrics tracking
- Error logging and notification
- Health checks for all system components

### Deployment
- Systemd service integration
- Nginx reverse proxy configuration
- Comprehensive deployment documentation
- Installation scripts and utilities

## Hardware Requirements
- Raspberry Pi 4 (4GB RAM recommended)
- Camera module, USB camera, or ONVIF-compatible IP cameras
- Weather-resistant enclosure
- GPIO connection to barrier system
- Network connectivity (wired recommended)

## Installation
See [installation guide](docs/installation.md) for detailed setup instructions.

For production deployment, see our [production deployment guide](docs/production_deployment.md).

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/AMSLPR.git
cd AMSLPR

# Run the installation script
./install.sh

# Start the service
sudo systemctl start amslpr
```

## Documentation

Comprehensive documentation is available in the [docs](docs/) directory:

- [User Manual](docs/user_manual.md)
- [API Reference](docs/api.md)
- [Production Deployment Guide](docs/production_deployment.md)
- [Security Hardening Guide](docs/security_hardening.md)
- [Performance Tuning Guide](docs/performance_tuning.md)
- [High Availability Guide](docs/high_availability.md)

See the [documentation index](docs/index.md) for a complete list of available documentation.

## Production Readiness

AMSLPR has undergone a comprehensive [production readiness assessment](docs/production_readiness_assessment.md) and meets or exceeds production-grade standards in all key areas:

| Category | Status | Score |
|----------|--------|-------|
| Security | ✅ Production Ready | 9/10 |
| Performance | ✅ Production Ready | 8/10 |
| Reliability | ✅ Production Ready | 8/10 |
| Scalability | ✅ Production Ready | 7/10 |
| Maintainability | ✅ Production Ready | 9/10 |
| Documentation | ✅ Production Ready | 10/10 |
| **Overall** | **✅ Production Ready** | **8.5/10** |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue on the GitHub repository or contact us at support@example.com.

## Contributing

Contributions are welcome! Please see our [contributing guide](docs/contributing.md) for details.

## Project Structure

```
AMSLPR/
├── config/             # Configuration files and examples
├── data/               # Data storage (images, database)
├── docs/               # Documentation
├── reports/            # Generated reports
├── scripts/            # Utility scripts
├── src/                # Source code
│   ├── barrier/        # Barrier control interface
│   ├── config/         # Configuration management
│   ├── database/       # Database management
│   ├── recognition/    # License plate recognition
│   ├── utils/          # Utility modules
│   └── web/            # Web interface
└── tests/              # Test suite
    ├── integration/    # Integration tests
    └── unit/           # Unit tests
```

## Acknowledgements

- OpenALPR for license plate recognition algorithms
- Flask for the web framework
- OpenCV for image processing
- Bootstrap for the web interface
- ONVIF for IP camera integration
