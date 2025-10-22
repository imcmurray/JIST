#!/bin/bash
# GitLab Template Manager - Offline Dependency Downloader
# Run this script on an internet-connected machine to download all dependencies
# Then transfer the packages/ directory to your airgapped server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PACKAGES_DIR="offline-packages"
PYTHON_CMD=""

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
        print_error "Python not found. Please install Python 3.6 or later"
        exit 1
    fi
}

# Check pip is installed
check_pip() {
    print_info "Checking pip installation..."

    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        print_error "pip not found. Please install pip first"
        echo "Install with: $PYTHON_CMD -m ensurepip --upgrade"
        exit 1
    fi

    print_success "pip is installed"
}

# Upgrade pip
upgrade_pip() {
    print_info "Upgrading pip to latest version..."
    $PYTHON_CMD -m pip install --upgrade pip
    print_success "pip upgraded"
}

# Download dependencies
download_dependencies() {
    print_info "Downloading Python dependencies..."

    # Create packages directory
    mkdir -p "$PACKAGES_DIR"

    # Determine source directory (where this script is located)
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

    if [ ! -f "$SOURCE_DIR/requirements.txt" ]; then
        print_error "requirements.txt not found at $SOURCE_DIR/requirements.txt"
        exit 1
    fi

    # Download all packages with dependencies
    print_info "Downloading packages to $PACKAGES_DIR/"
    $PYTHON_CMD -m pip download \
        --dest "$PACKAGES_DIR" \
        --requirement "$SOURCE_DIR/requirements.txt"

    print_success "All dependencies downloaded to $PACKAGES_DIR/"
}

# Create package archive
create_archive() {
    print_info "Creating archive for transfer..."

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ARCHIVE_NAME="template-manager-offline-${TIMESTAMP}.tar.gz"

    # Create archive with packages and requirements.txt
    tar -czf "$ARCHIVE_NAME" "$PACKAGES_DIR" ../requirements.txt 2>/dev/null || \
        tar -czf "$ARCHIVE_NAME" "$PACKAGES_DIR"

    print_success "Archive created: $ARCHIVE_NAME"

    # Get archive size
    ARCHIVE_SIZE=$(du -h "$ARCHIVE_NAME" | cut -f1)
    print_info "Archive size: $ARCHIVE_SIZE"
}

# Print instructions
print_instructions() {
    echo ""
    echo "======================================"
    print_success "Download completed successfully!"
    echo "======================================"
    echo ""
    echo "Transfer instructions:"
    echo ""
    echo "1. Transfer files to your airgapped server:"
    if [ -f "$ARCHIVE_NAME" ]; then
        echo "   - Archive file: $ARCHIVE_NAME"
        echo "   - Or directory: $PACKAGES_DIR/"
    else
        echo "   - Directory: $PACKAGES_DIR/"
    fi
    echo ""
    echo "2. On the airgapped server, extract if using archive:"
    echo "   tar -xzf $ARCHIVE_NAME"
    echo ""
    echo "3. Run the offline installation script:"
    echo "   sudo bash scripts/setup_offline.sh"
    echo ""
    echo "File transfer methods:"
    echo "  - USB drive"
    echo "  - SCP: scp $ARCHIVE_NAME user@server:/tmp/"
    echo "  - Rsync: rsync -av $PACKAGES_DIR user@server:/tmp/"
    echo "  - Physical media transfer"
    echo ""
}

# Main function
main() {
    echo ""
    echo "======================================"
    echo "  GitLab Template Manager"
    echo "  Offline Dependency Downloader"
    echo "======================================"
    echo ""

    detect_python
    check_pip
    upgrade_pip
    download_dependencies

    # Ask about creating archive
    read -p "Create archive for easy transfer? (y/n) [default: y]: " CREATE_ARCHIVE
    CREATE_ARCHIVE=${CREATE_ARCHIVE:-y}

    if [ "$CREATE_ARCHIVE" = "y" ] || [ "$CREATE_ARCHIVE" = "Y" ]; then
        create_archive
    fi

    print_instructions
}

# Run main
main
