#!/bin/bash
# GitLab Template Manager - Offline Installation Script
# This script sets up the Template Manager on an airgapped RHEL 7 server
# using pre-downloaded Python packages

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/template-manager"
PYTHON_CMD=""
PACKAGES_DIR=""

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Detect Python version
detect_python() {
    print_info "Detecting Python installation..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_CMD="python3"
        print_success "Found Python 3: $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        PYTHON_CMD="python"
        print_warning "Using Python 2: $PYTHON_VERSION (Python 3 recommended)"
    else
        print_error "Python not found. Please install Python manually from RHEL installation media"
        echo ""
        echo "For RHEL 7, you can install from DVD:"
        echo "  1. Mount RHEL 7 DVD"
        echo "  2. yum install python3 --disablerepo=* --enablerepo=media"
        exit 1
    fi
}

# Check for git
check_git() {
    print_info "Checking for git..."

    if ! command -v git &> /dev/null; then
        print_error "git not found. Please install git manually from RHEL installation media"
        echo ""
        echo "For RHEL 7, you can install from DVD:"
        echo "  1. Mount RHEL 7 DVD"
        echo "  2. yum install git --disablerepo=* --enablerepo=media"
        exit 1
    fi

    print_success "git is installed"
}

# Locate packages directory
locate_packages() {
    print_info "Locating offline packages..."

    # Determine source directory (where this script is located)
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

    # Check common locations for packages
    POSSIBLE_LOCATIONS=(
        "$SOURCE_DIR/offline-packages"
        "$SCRIPT_DIR/offline-packages"
        "$(pwd)/offline-packages"
        "/tmp/offline-packages"
        "$SOURCE_DIR/../offline-packages"
    )

    for location in "${POSSIBLE_LOCATIONS[@]}"; do
        if [ -d "$location" ]; then
            PACKAGES_DIR="$location"
            print_success "Found packages at: $PACKAGES_DIR"
            return 0
        fi
    done

    # If not found, ask user
    print_warning "Could not locate offline-packages directory automatically"
    echo ""
    read -p "Enter path to offline-packages directory: " PACKAGES_DIR

    if [ ! -d "$PACKAGES_DIR" ]; then
        print_error "Directory not found: $PACKAGES_DIR"
        echo ""
        echo "Please ensure you have transferred the offline-packages directory to this server"
        echo "Run download_offline_packages.sh on an internet-connected machine first"
        exit 1
    fi

    print_success "Using packages from: $PACKAGES_DIR"
}

# Verify packages
verify_packages() {
    print_info "Verifying package contents..."

    # Count .whl and .tar.gz files
    PACKAGE_COUNT=$(find "$PACKAGES_DIR" -type f \( -name "*.whl" -o -name "*.tar.gz" \) | wc -l)

    if [ "$PACKAGE_COUNT" -eq 0 ]; then
        print_error "No Python packages found in $PACKAGES_DIR"
        echo "Expected to find .whl or .tar.gz files"
        exit 1
    fi

    print_success "Found $PACKAGE_COUNT package(s)"
}

# Create installation directory
create_install_dir() {
    print_info "Creating installation directory: $INSTALL_DIR"

    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory already exists. Backing up to ${INSTALL_DIR}.bak.$(date +%s)"
        mv "$INSTALL_DIR" "${INSTALL_DIR}.bak.$(date +%s)"
    fi

    mkdir -p "$INSTALL_DIR"
    print_success "Installation directory created"
}

# Copy application files
copy_files() {
    print_info "Copying application files..."

    # Determine source directory (where this script is located)
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

    # Copy all files except packages directory
    rsync -av --exclude='offline-packages' --exclude='*.tar.gz' "$SOURCE_DIR"/ "$INSTALL_DIR/" 2>/dev/null || \
        cp -r "$SOURCE_DIR"/* "$INSTALL_DIR/"

    # Set ownership
    chown -R root:root "$INSTALL_DIR"

    print_success "Application files copied"
}

# Create virtual environment
create_virtualenv() {
    print_info "Creating Python virtual environment..."

    cd "$INSTALL_DIR"

    # Create virtual environment
    $PYTHON_CMD -m venv venv

    if [ ! -d "venv" ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi

    print_success "Virtual environment created at $INSTALL_DIR/venv"
}

# Install Python dependencies offline
install_python_deps_offline() {
    print_info "Installing Python dependencies from offline packages in virtual environment..."

    cd "$INSTALL_DIR"

    # Activate virtual environment
    source venv/bin/activate

    # Check if pip is available in venv
    if ! pip --version &> /dev/null; then
        print_warning "pip not found in venv, attempting to bootstrap pip..."

        # Try to install pip from packages if available
        PIP_PACKAGE=$(find "$PACKAGES_DIR" -name "pip-*.whl" -o -name "pip-*.tar.gz" | head -n 1)
        if [ -n "$PIP_PACKAGE" ]; then
            python "$PIP_PACKAGE/setup.py" install 2>/dev/null || \
                print_error "Could not install pip. Please install pip manually"
        else
            print_error "pip not found and no pip package in offline packages"
            echo "Please install pip manually or include it in offline packages"
            deactivate
            exit 1
        fi
    fi

    # Install all packages from the offline directory
    print_info "Installing packages from $PACKAGES_DIR"

    # Method 1: Try installing with pip using --no-index and --find-links
    pip install \
        --no-index \
        --find-links="$PACKAGES_DIR" \
        --requirement requirements.txt \
        2>&1 | tee /tmp/pip-install.log

    # Check if installation was successful
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_success "Python dependencies installed successfully in virtual environment"
    else
        print_warning "Some packages may have failed to install. Check /tmp/pip-install.log"

        # Try alternative method: install each wheel directly
        print_info "Attempting alternative installation method..."
        for package in "$PACKAGES_DIR"/*.whl; do
            if [ -f "$package" ]; then
                print_info "Installing $(basename "$package")..."
                pip install --no-index --no-deps "$package" || \
                    print_warning "Could not install $(basename "$package")"
            fi
        done
    fi

    # Deactivate venv
    deactivate
}

# Create configuration file
create_config() {
    print_info "Creating configuration file..."

    # Prompt for configuration
    echo ""
    echo "===== Configuration Setup ====="
    echo ""

    read -p "Server role (train/test/live): " SERVER_ROLE
    read -p "GitLab URL [https://gitlab.com]: " GITLAB_URL
    GITLAB_URL=${GITLAB_URL:-https://gitlab.com}
    read -p "GitLab Personal Access Token: " GITLAB_TOKEN
    read -p "GitLab Project ID: " GITLAB_PROJECT_ID
    read -p "Repository path [/var/www/html/templates]: " REPO_PATH
    REPO_PATH=${REPO_PATH:-/var/www/html/templates}

    # Create .env file
    cat > "$INSTALL_DIR/.env" <<EOF
# GitLab Template Manager Configuration
# Generated on $(date)

# Server Settings
SERVER_ROLE=${SERVER_ROLE}
FLASK_PORT=8080
FLASK_HOST=0.0.0.0
DEBUG=False

# GitLab Settings
GITLAB_URL=${GITLAB_URL}
GITLAB_TOKEN=${GITLAB_TOKEN}
GITLAB_PROJECT_ID=${GITLAB_PROJECT_ID}

# Repository Settings
REPO_PATH=${REPO_PATH}

# Branch Names
TRAIN_BRANCH=train
TEST_BRANCH=test
LIVE_BRANCH=live

# Auto-termination (seconds, 0 to disable)
AUTO_TERMINATE_TIMEOUT=3600

# Backup Settings
BACKUP_ENABLED=True
BACKUP_DIR=/var/backups/templates

# Logging
LOG_FILE=/var/log/template-manager.log
LOG_LEVEL=INFO

# Flask Secret Key
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "change-this-secret-key-$(date +%s)")
EOF

    chmod 600 "$INSTALL_DIR/.env"
    print_success "Configuration file created at $INSTALL_DIR/.env"
}

# Create backup directory
create_backup_dir() {
    print_info "Creating backup directory..."
    mkdir -p /var/backups/templates
    chmod 755 /var/backups/templates
    print_success "Backup directory created"
}

# Create log file
create_log_file() {
    print_info "Creating log file..."
    touch /var/log/template-manager.log
    chmod 644 /var/log/template-manager.log
    print_success "Log file created"
}

# Initialize or configure git repository
init_git_repo() {
    echo ""
    print_info "Checking git repository configuration..."

    # Get repository path from config
    REPO_PATH=$(grep "REPO_PATH=" "$INSTALL_DIR/.env" | cut -d '=' -f2)

    if [ ! -d "$REPO_PATH" ]; then
        print_warning "Repository path does not exist. Creating it..."
        mkdir -p "$REPO_PATH"
    fi

    # Check if git repository already exists
    if [ -d "$REPO_PATH/.git" ]; then
        echo ""
        print_warning "Existing git repository detected in $REPO_PATH"
        echo ""

        # Run the git repository checker if available
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -f "$SCRIPT_DIR/check_git_repository.sh" ]; then
            bash "$SCRIPT_DIR/check_git_repository.sh" "$REPO_PATH"
            CHECK_RESULT=$?
        else
            CHECK_RESULT=0
        fi

        echo ""
        echo "How would you like Template Manager to work with this repository?"
        echo ""
        echo "1) Template Manager manages GitLab sync (RECOMMENDED)"
        echo "   - Use this if: Design app maintains git for history/audit only"
        echo "   - Use this if: No other tool pushes to GitLab"
        echo "   - Template Manager will: commit, push to GitLab, promote branches"
        echo "   - Design app can: edit files, view git history"
        echo "   - Both share the same .git repository harmoniously"
        echo ""
        echo "2) External automation manages GitLab sync (Template Manager read-only)"
        echo "   - Use this if: Ansible/Jenkins/CI-CD commits AND pushes to GitLab"
        echo "   - Use this if: External automation detected (see warnings above)"
        echo "   - Template Manager will: ONLY use GitLab API (promote, compare)"
        echo "   - Template Manager will NOT: commit, push, or pull locally"
        echo "   - Prevents conflicts with external automation tools"
        echo ""
        echo "3) Skip git configuration for now"
        echo ""
        echo "NOTE: If you have a template design/editing application that maintains"
        echo "      git history but does NOT push to GitLab, choose Option 1."
        echo ""

        read -p "Select option [1-3] (default: 1): " GIT_OPTION
        GIT_OPTION=${GIT_OPTION:-1}

        case $GIT_OPTION in
            1)
                print_info "Configuring Template Manager to manage GitLab synchronization..."
                # Update configuration
                sed -i 's/MANAGE_LOCAL_GIT=.*/MANAGE_LOCAL_GIT=True/' "$INSTALL_DIR/.env"
                sed -i 's/USE_EXISTING_REMOTE=.*/USE_EXISTING_REMOTE=True/' "$INSTALL_DIR/.env"
                print_success "Configuration complete:"
                echo "  - Template Manager will commit changes and push to GitLab"
                echo "  - Design apps can view git history and audit trail"
                echo "  - Both share the existing .git repository"
                echo "  - Template Manager handles all GitLab operations"
                ;;
            2)
                print_info "Configuring Template Manager for read-only mode..."
                # Update configuration
                sed -i 's/MANAGE_LOCAL_GIT=.*/MANAGE_LOCAL_GIT=False/' "$INSTALL_DIR/.env"
                sed -i 's/USE_EXISTING_REMOTE=.*/USE_EXISTING_REMOTE=True/' "$INSTALL_DIR/.env"
                print_success "Configuration complete:"
                echo "  - Template Manager will ONLY use GitLab API"
                echo "  - External automation handles commits and pushes"
                echo "  - Template Manager can promote branches via GitLab"
                echo "  - No conflicts with external tools"
                ;;
            3)
                print_info "Skipping git configuration (can configure later in .env)"
                ;;
            *)
                print_warning "Invalid option, skipping git configuration"
                ;;
        esac

    else
        # No existing repository
        echo ""
        read -p "Would you like to initialize a new git repository? (y/n): " INIT_GIT

        if [ "$INIT_GIT" = "y" ] || [ "$INIT_GIT" = "Y" ]; then
            print_info "Initializing new git repository..."

            cd "$REPO_PATH"
            git init
            git config user.email "template-manager@localhost"
            git config user.name "Template Manager"

            # Get GitLab URL and project details
            GITLAB_URL=$(grep "GITLAB_URL=" "$INSTALL_DIR/.env" | cut -d '=' -f2)
            GITLAB_PROJECT_ID=$(grep "GITLAB_PROJECT_ID=" "$INSTALL_DIR/.env" | cut -d '=' -f2)
            GITLAB_TOKEN=$(grep "GITLAB_TOKEN=" "$INSTALL_DIR/.env" | cut -d '=' -f2)

            # Construct remote URL with token
            REMOTE_URL=$(echo "$GITLAB_URL" | sed "s|https://|https://oauth2:${GITLAB_TOKEN}@|")/project/${GITLAB_PROJECT_ID}.git

            git remote add origin "$REMOTE_URL" 2>/dev/null || git remote set-url origin "$REMOTE_URL"

            # Set configuration for new repository
            sed -i 's/MANAGE_LOCAL_GIT=.*/MANAGE_LOCAL_GIT=True/' "$INSTALL_DIR/.env"
            sed -i 's/USE_EXISTING_REMOTE=.*/USE_EXISTING_REMOTE=False/' "$INSTALL_DIR/.env"

            print_success "Git repository initialized and configured"
        else
            print_info "Skipping git repository initialization"
        fi
    fi
}

# Create start script link
create_start_script() {
    print_info "Creating start script..."

    chmod +x "$INSTALL_DIR/scripts/start_ui.sh"

    # Create symlink in /usr/local/bin
    ln -sf "$INSTALL_DIR/scripts/start_ui.sh" /usr/local/bin/template-manager

    print_success "Start script created. You can now run 'template-manager' from anywhere"
}

# Print completion message
print_completion() {
    echo ""
    echo "======================================"
    print_success "Offline installation completed!"
    echo "======================================"
    echo ""
    echo "Next steps:"
    echo "  1. Review configuration: $INSTALL_DIR/.env"
    echo "  2. Start the template manager: template-manager"
    echo "  3. Or run directly: $INSTALL_DIR/scripts/start_ui.sh"
    echo ""
    echo "Documentation: $INSTALL_DIR/README.md"
    echo ""
    echo "Note: This is an airgapped installation."
    echo "All dependencies were installed from offline packages."
    echo ""
}

# Main installation process
main() {
    echo ""
    echo "======================================"
    echo "  GitLab Template Manager"
    echo "  Offline Installation"
    echo "======================================"
    echo ""

    check_root
    detect_python
    check_git
    locate_packages
    verify_packages
    create_install_dir
    copy_files
    create_virtualenv
    install_python_deps_offline
    create_config
    create_backup_dir
    create_log_file
    init_git_repo
    create_start_script
    print_completion
}

# Run main installation
main
