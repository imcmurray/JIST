# GitLab Template Manager

A multi-environment template management system for RHEL 7 servers using GitLab as the source control backend. Manage HTML templates across three environments (Train, Test, Live) with an easy-to-use web interface.

## Features

### Train Server Capabilities
- **Commit & Push**: Commit local template changes and push to GitLab train branch
- **Promote Changes**: Merge train branch to test or live branches in GitLab
- **View Differences**: Compare train branch against test and live branches
- **Sync Status Dashboard**: See which branches are aligned at a glance
- **Git Status**: View uncommitted changes in real-time

### Test/Live Server Capabilities
- **Check for Updates**: Compare local repository with GitLab branch
- **Preview Changes**: View pending changes before pulling
- **Pull Updates**: Safely pull latest changes from GitLab
- **Automatic Backups**: Create backups before pulling changes
- **Version Information**: Display current commit hash and details

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Train     │     │    Test     │     │    Live     │
│   Server    │────▶│   Server    │────▶│   Server    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                  ┌────────▼────────┐
                  │  GitLab Repo    │
                  │  ┌────────────┐ │
                  │  │   train    │ │
                  │  │   test     │ │
                  │  │   live     │ │
                  │  └────────────┘ │
                  └─────────────────┘
```

## Requirements

- **Operating System**: RHEL 7 or compatible (CentOS 7, etc.)
- **Python**: Python 3.6 or later (recommended) or Python 2.7
- **Git**: Git 1.8 or later
- **Network**: Access to GitLab instance
- **GitLab**: Personal Access Token with API access

## Installation

### 1. Obtain GitLab Personal Access Token

1. Log in to your GitLab instance
2. Go to **Settings** → **Access Tokens**
3. Create a new token with the following scopes:
   - `api` - Full API access
   - `read_repository` - Read repository
   - `write_repository` - Write repository
4. Save the token securely - you'll need it during installation

### 2. Get GitLab Project ID

1. Navigate to your GitLab project
2. The Project ID is displayed under the project name
3. Or find it in **Settings** → **General**

### 3. Run Installation Script

```bash
# Clone or copy the template-manager directory to your server

# Run the setup script as root
sudo bash template-manager/scripts/setup.sh
```

The installation script will:
- Install system dependencies (git, python3)
- Create installation directory (`/opt/template-manager`)
- Install Python dependencies
- Create configuration file
- Set up backup directory
- Create log file
- Optionally initialize git repository
- Create command-line shortcut

### 4. Configure Each Server

During installation, you'll be prompted for:

- **Server Role**: `train`, `test`, or `live`
- **GitLab URL**: Your GitLab instance URL (default: https://gitlab.com)
- **GitLab Token**: Your Personal Access Token
- **GitLab Project ID**: Your project's ID number
- **Repository Path**: Local path to templates (default: `/var/www/html/templates`)

### Example Configuration

**Train Server:**
```
Server role: train
GitLab URL: https://gitlab.example.com
GitLab Token: glpat-xxxxxxxxxxxxxxxxxxxx
GitLab Project ID: 12345
Repository path: /var/www/html/templates
```

**Test Server:**
```
Server role: test
GitLab URL: https://gitlab.example.com
GitLab Token: glpat-yyyyyyyyyyyyyyyyyyyy
GitLab Project ID: 12345
Repository path: /var/www/html/templates
```

**Live Server:**
```
Server role: live
GitLab URL: https://gitlab.example.com
GitLab Token: glpat-zzzzzzzzzzzzzzzzzzzz
GitLab Project ID: 12345
Repository path: /var/www/html/templates
```

## Installation for Airgapped/Offline Servers

If your RHEL 7 servers are airgapped (no internet access), follow these steps to install the Template Manager using pre-downloaded packages.

### Step 1: Download Dependencies (Internet-Connected Machine)

On a machine with internet access (can be your workstation, not necessarily RHEL 7):

```bash
# Navigate to the template-manager directory
cd template-manager

# Run the offline package downloader
bash scripts/download_offline_packages.sh
```

This script will:
- Download all Python dependencies and their sub-dependencies
- Save them to an `offline-packages/` directory
- Optionally create a compressed archive for easy transfer
- Display transfer instructions

Expected output:
```
Downloading Python dependencies...
Downloading packages to offline-packages/
Successfully downloaded Flask-2.0.3-py3-none-any.whl
Successfully downloaded GitPython-3.1.27-py3-none-any.whl
...
Archive created: template-manager-offline-20241022_143022.tar.gz
Archive size: 15M
```

### Step 2: Transfer to Airgapped Server

Transfer the packages to your airgapped RHEL 7 server using one of these methods:

**Method 1: Using Archive File (Recommended)**
```bash
# SCP transfer
scp template-manager-offline-20241022_143022.tar.gz user@rhel-server:/tmp/

# Or USB drive, physical media, etc.
```

**Method 2: Transfer Entire Directory**
```bash
# Rsync
rsync -av template-manager/ user@rhel-server:/tmp/template-manager/

# Or copy to USB drive
cp -r template-manager/ /media/usb/
```

### Step 3: Extract on Airgapped Server (If Using Archive)

```bash
# SSH to your airgapped server
ssh user@rhel-server

# Extract the archive
cd /tmp
tar -xzf template-manager-offline-20241022_143022.tar.gz
```

### Step 4: Install System Dependencies (If Needed)

If git or python3 are not installed, install them from RHEL installation media:

```bash
# Mount RHEL 7 installation DVD
sudo mount /dev/cdrom /mnt

# Create local repository
sudo cat > /etc/yum.repos.d/local.repo <<EOF
[local]
name=RHEL Local
baseurl=file:///mnt
enabled=1
gpgcheck=0
EOF

# Install git and python3
sudo yum install git python3 --disablerepo=* --enablerepo=local

# Unmount DVD
sudo umount /mnt
```

### Step 5: Run Offline Installation

```bash
# Navigate to the template-manager directory
cd /tmp/template-manager  # or wherever you extracted it

# Run the offline installation script as root
sudo bash scripts/setup_offline.sh
```

The offline installation script will:
- Detect Python and git installations
- Locate the offline-packages directory
- Verify package contents
- Install all dependencies from local packages (no internet required)
- Create configuration file
- Set up directories and permissions
- Create command-line shortcut

### Step 6: Configure

Follow the same configuration prompts as the online installation:

```
Server role: train
GitLab URL: https://gitlab.example.com
GitLab Token: glpat-xxxxxxxxxxxxxxxxxxxx
GitLab Project ID: 12345
Repository path: /var/www/html/templates
```

### Offline Installation Notes

1. **Python Version Compatibility**:
   - Download packages on a machine with same Python version as target server
   - Check version: `python3 --version`

2. **Architecture Compatibility**:
   - Some packages are platform-specific
   - Download on same OS/architecture when possible (RHEL 7 x86_64)

3. **Package Updates**:
   - To update packages, re-run `download_offline_packages.sh`
   - Transfer new packages to servers

4. **Verification**:
   - After installation, check logs: `/var/log/template-manager.log`
   - Test startup: `template-manager`

5. **Multiple Servers**:
   - Download packages once
   - Transfer same package set to all servers
   - Saves bandwidth and time

### Troubleshooting Offline Installation

**Problem**: "pip not found"

**Solution**:
```bash
# Install pip from RHEL DVD
sudo yum install python3-pip --disablerepo=* --enablerepo=local
```

**Problem**: "Package installation failed"

**Solution**:
- Verify all .whl files are in offline-packages/
- Check package compatibility with Python version
- Review /tmp/pip-install.log for details

**Problem**: "Cannot find offline-packages directory"

**Solution**:
```bash
# Manually specify the path when prompted
# Or ensure offline-packages/ is in the same directory as scripts/
ls -la offline-packages/  # Verify it exists
```

## Usage

### Starting the Web UI

```bash
# From anywhere (after installation)
template-manager

# Or run directly
/opt/template-manager/scripts/start_ui.sh
```

The web interface will start on `http://localhost:8080` (configurable).

### Train Server Workflow

1. **Make changes** to templates in `/var/www/html/templates`
2. **Launch web UI**: `template-manager`
3. **View changes**: See modified and untracked files
4. **Commit changes**: Enter commit message and commit
5. **Push to GitLab**: Push to train branch
6. **Promote to Test**: Click "Promote to Test" to merge train → test
7. **Promote to Live**: Click "Promote to Live" to merge train → live (use with caution!)

### Test/Live Server Workflow

1. **Launch web UI**: `template-manager`
2. **Check for updates**: Click "Check for Updates"
3. **Preview changes**: Click "Preview Changes" to see what will be updated
4. **Pull changes**: Click "Pull Changes" to apply updates
5. **Backup**: Automatic backup created before pulling (if enabled)

## Configuration

Configuration is stored in `/opt/template-manager/.env`

### Key Settings

```bash
# Server identification
SERVER_ROLE=train          # train, test, or live

# Web interface
FLASK_PORT=8080            # Port for web UI
FLASK_HOST=0.0.0.0         # Listen on all interfaces

# GitLab connection
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your-token-here
GITLAB_PROJECT_ID=12345

# Repository
REPO_PATH=/var/www/html/templates

# Branch names (default)
TRAIN_BRANCH=train
TEST_BRANCH=test
LIVE_BRANCH=live

# Backups
BACKUP_ENABLED=True
BACKUP_DIR=/var/backups/templates

# Logging
LOG_FILE=/var/log/template-manager.log
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
```

### Editing Configuration

```bash
sudo nano /opt/template-manager/.env

# Restart the application after changes
```

## Security Considerations

1. **GitLab Token Storage**
   - Tokens are stored in `/opt/template-manager/.env`
   - File has restricted permissions (600)
   - Never commit `.env` to version control

2. **Network Access**
   - Web UI binds to `0.0.0.0` by default
   - Consider using firewall rules to restrict access
   - Or change `FLASK_HOST` to `127.0.0.1` for localhost only

3. **Branch Protection**
   - Consider protecting the `live` branch in GitLab
   - Require approvals for merges to live
   - Train branch promotion requires explicit confirmation

4. **Separate Tokens**
   - Use different GitLab tokens for each server
   - Train server: needs write access
   - Test/Live servers: only need read access

## File Structure

```
/opt/template-manager/
├── app.py                      # Main Flask application
├── config.py                   # Configuration module
├── requirements.txt            # Python dependencies
├── .env                        # Configuration file (created during setup)
├── lib/
│   ├── __init__.py
│   ├── git_ops.py             # Local git operations
│   ├── gitlab_ops.py          # GitLab API operations
│   └── sync_checker.py        # Branch comparison logic
├── templates/                  # HTML templates for web UI
│   ├── base.html
│   ├── train.html             # Train server interface
│   ├── deploy.html            # Test/Live server interface
│   └── error.html
├── static/
│   └── style.css              # CSS stylesheet
├── scripts/
│   ├── setup.sh               # Online installation script
│   ├── setup_offline.sh       # Offline/airgapped installation script
│   ├── download_offline_packages.sh  # Download dependencies for offline install
│   └── start_ui.sh            # Launch script
└── README.md                   # This file
```

## Troubleshooting

### GitLab Connection Errors

**Problem**: "GitLab authentication failed"

**Solutions**:
- Verify GitLab token is correct in `.env`
- Check token has required scopes (api, read_repository, write_repository)
- Ensure GitLab URL is correct
- Test network connectivity to GitLab

```bash
# Test GitLab connection
curl -H "PRIVATE-TOKEN: your-token" https://gitlab.com/api/v4/user
```

### Repository Not Found

**Problem**: "Failed to open repository"

**Solutions**:
- Verify `REPO_PATH` exists and contains a git repository
- Check git is initialized: `ls -la /var/www/html/templates/.git`
- Initialize if needed: `cd /var/www/html/templates && git init`
- Verify remote is configured: `git remote -v`

### Port Already in Use

**Problem**: "Port 8080 is already in use"

**Solutions**:
- Check what's using the port: `netstat -tuln | grep 8080`
- Change `FLASK_PORT` in `/opt/template-manager/.env`
- Stop conflicting service
- Kill existing template-manager process

### Permission Errors

**Problem**: "Permission denied" errors

**Solutions**:
- Verify repository directory permissions
- Check log file is writable: `ls -l /var/log/template-manager.log`
- Ensure backup directory exists: `ls -ld /var/backups/templates`
- Run installation script as root

```bash
# Fix common permission issues
sudo chmod 755 /var/www/html/templates
sudo chmod 644 /var/log/template-manager.log
sudo chmod 755 /var/backups/templates
```

### Python Dependency Errors

**Problem**: ImportError or module not found

**Solutions**:
- Reinstall dependencies:
  ```bash
  cd /opt/template-manager
  sudo pip3 install -r requirements.txt
  ```
- Verify Python version: `python3 --version` (need 3.6+)
- Check pip is installed: `pip3 --version`

## API Endpoints

The application exposes several REST API endpoints:

### Status Endpoints
- `GET /` - Main dashboard
- `GET /status` - Full system status (JSON)
- `GET /health` - Health check (JSON)
- `GET /local-status` - Local repository status (JSON)
- `GET /sync-status` - Branch synchronization status (JSON)

### Git Operations
- `GET /diff` - Get diff of local changes (JSON)
- `POST /commit` - Commit changes (JSON)
- `POST /push` - Push to remote (JSON)
- `POST /pull` - Pull from remote (JSON)

### GitLab Operations (Train Server)
- `POST /promote` - Promote to test or live (JSON)
- `GET /compare` - Compare branches (JSON)
- `GET /branch-info/<branch>` - Get branch information (JSON)

### Examples

```bash
# Get status
curl http://localhost:8080/status

# Commit changes
curl -X POST http://localhost:8080/commit \
  -H "Content-Type: application/json" \
  -d '{"message": "Update templates"}'

# Promote to test
curl -X POST http://localhost:8080/promote \
  -H "Content-Type: application/json" \
  -d '{"target": "test"}'
```

## Logs

Application logs are written to `/var/log/template-manager.log`

```bash
# View logs
sudo tail -f /var/log/template-manager.log

# Search for errors
sudo grep ERROR /var/log/template-manager.log

# View recent activity
sudo tail -100 /var/log/template-manager.log
```

## Backups

Backups are automatically created before pulling changes (if `BACKUP_ENABLED=True`).

Backup location: `/var/backups/templates/template_backup_YYYYMMDD_HHMMSS/`

```bash
# List backups
ls -lh /var/backups/templates/

# Restore from backup
sudo cp -r /var/backups/templates/template_backup_20241022_143000/* /var/www/html/templates/
```

## Uninstallation

```bash
# Remove installation
sudo rm -rf /opt/template-manager

# Remove command shortcut
sudo rm /usr/local/bin/template-manager

# Remove logs (optional)
sudo rm /var/log/template-manager.log

# Remove backups (optional)
sudo rm -rf /var/backups/templates
```

## Support

For issues, questions, or feature requests:

1. Check the Troubleshooting section above
2. Review logs: `/var/log/template-manager.log`
3. Verify configuration: `/opt/template-manager/.env`

## License

Copyright (c) 2024. All rights reserved.

## Version

Version 1.0.0
