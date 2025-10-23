#!/bin/bash
# GitLab Template Manager - Start UI Script
# Launches the web interface and optionally opens a browser

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine installation directory
if [ -d "/opt/template-manager" ]; then
    INSTALL_DIR="/opt/template-manager"
elif [ -f "$(dirname "$0")/../app.py" ]; then
    # Running from source directory
    INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
else
    echo -e "${RED}[ERROR]${NC} Could not find template manager installation"
    exit 1
fi

# Load configuration
if [ -f "$INSTALL_DIR/.env" ]; then
    export $(grep -v '^#' "$INSTALL_DIR/.env" | xargs)
else
    echo -e "${YELLOW}[WARNING]${NC} Configuration file not found at $INSTALL_DIR/.env"
    echo "Using default configuration..."
fi

# Set defaults
FLASK_PORT=${FLASK_PORT:-8080}
FLASK_HOST=${FLASK_HOST:-0.0.0.0}
SERVER_ROLE=${SERVER_ROLE:-train}

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if port is available
check_port() {
    if netstat -tuln 2>/dev/null | grep -q ":$FLASK_PORT "; then
        print_error "Port $FLASK_PORT is already in use"
        echo "Please stop the existing process or change FLASK_PORT in $INSTALL_DIR/.env"
        exit 1
    fi
}

# Check Python
check_python() {
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python not found. Please install Python 3"
        exit 1
    fi
}

# Open browser
open_browser() {
    local url="http://localhost:$FLASK_PORT"

    # Wait a moment for the server to start
    sleep 2

    # Try to open browser
    if command -v xdg-open &> /dev/null; then
        xdg-open "$url" &> /dev/null &
    elif command -v gnome-open &> /dev/null; then
        gnome-open "$url" &> /dev/null &
    elif command -v firefox &> /dev/null; then
        firefox "$url" &> /dev/null &
    else
        echo ""
        echo "Please open your browser and navigate to: $url"
    fi
}

# Main function
main() {
    echo ""
    echo "======================================"
    echo "  GitLab Template Manager"
    echo "======================================"
    echo ""
    print_info "Server Role: $SERVER_ROLE"
    print_info "Installation: $INSTALL_DIR"
    print_info "Starting web interface on http://localhost:$FLASK_PORT"
    echo ""

    # Checks
    check_python
    check_port

    # Change to installation directory
    cd "$INSTALL_DIR"

    # Ask about opening browser
    if [ -t 0 ]; then
        read -t 5 -p "Open browser automatically? (y/n) [default: y]: " OPEN_BROWSER || OPEN_BROWSER="y"
        echo ""
    else
        OPEN_BROWSER="y"
    fi

    # Start the application
    print_success "Starting Template Manager..."
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo "======================================"
    echo ""

    # Open browser in background if requested
    if [ "$OPEN_BROWSER" = "y" ] || [ "$OPEN_BROWSER" = "Y" ] || [ -z "$OPEN_BROWSER" ]; then
        open_browser &
    fi

    # Activate virtual environment if it exists
    if [ -d "$INSTALL_DIR/venv" ]; then
        print_info "Activating virtual environment..."
        source "$INSTALL_DIR/venv/bin/activate"
    fi

    # Start Flask application
    if command -v python3 &> /dev/null; then
        python3 app.py
    else
        python app.py
    fi
}

# Trap Ctrl+C
trap 'echo ""; print_info "Shutting down..."; exit 0' INT TERM

# Run main
main
