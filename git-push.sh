#!/bin/bash

# Git Push Script for VisionGate Deployment
# This script will add, commit, and push all deployment files

set -e

echo "=== VisionGate Git Push Script ==="
echo "Preparing to push deployment files to repository..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository. Please run 'git init' first."
    exit 1
fi

# Add all new and modified files
echo "Adding files to git..."
git add docker-compose.vps.yml
git add config/config.json
git add deploy.sh
git add backup.sh
git add VPS_DEPLOYMENT_GUIDE.md
git add DEPLOYMENT_README.md

# Check if files were added
if git diff --cached --quiet; then
    echo "✅ Files added successfully"
else
    echo "ℹ️  No changes to commit"
    exit 0
fi

# Commit the changes
echo "Committing changes..."
git commit -m "Add VPS deployment configuration

- Add docker-compose.vps.yml for VPS deployment
- Add production config.json for CloudPanel setup
- Add deploy.sh and backup.sh scripts
- Add comprehensive VPS deployment guide
- Disable Hailo TPU for VPS environment
- Configure SSL for CloudPanel integration"

# Push to remote repository
echo "Pushing to remote repository..."
git push origin main

echo ""
echo "✅ Successfully pushed deployment files to repository!"
echo ""
echo "Next steps:"
echo "1. SSH into your VPS: ssh visiongate@your-vps-ip"
echo "2. Pull latest changes: git pull"
echo "3. Run deployment script: ./deploy.sh"
echo ""
echo "Your VisionGate application will be deployed to your VPS!"