#!/bin/bash
# Ara Voice Assistant - Setup Script
# Detects platform and installs dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)
            if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
                echo "raspberrypi"
            else
                echo "linux"
            fi
            ;;
        *)          echo "unknown" ;;
    esac
}

# Detect architecture
detect_arch() {
    case "$(uname -m)" in
        x86_64)     echo "x86_64" ;;
        arm64|aarch64)  echo "arm64" ;;
        armv7l)     echo "armv7" ;;
        *)          echo "unknown" ;;
    esac
}

# Check Python version
check_python() {
    if command -v python3.11 &> /dev/null; then
        PYTHON="python3.11"
    elif command -v python3 &> /dev/null; then
        PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [[ $(echo "$PY_VERSION >= 3.11" | bc -l) -eq 1 ]]; then
            PYTHON="python3"
        else
            error "Python 3.11+ required, found $PY_VERSION"
        fi
    else
        error "Python 3 not found. Please install Python 3.11+"
    fi
    info "Using Python: $($PYTHON --version)"
}

# Install system dependencies for macOS
install_macos_deps() {
    info "Installing macOS dependencies..."

    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        warn "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    # Install dependencies
    brew install portaudio ffmpeg python@3.11 || true

    success "macOS dependencies installed"
}

# Install system dependencies for Linux
install_linux_deps() {
    info "Installing Linux dependencies..."

    sudo apt-get update
    sudo apt-get install -y \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        portaudio19-dev \
        ffmpeg \
        libasound2-dev \
        libportaudio2

    success "Linux dependencies installed"
}

# Install system dependencies for Raspberry Pi
install_pi_deps() {
    info "Installing Raspberry Pi dependencies..."

    sudo apt-get update
    sudo apt-get install -y \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        portaudio19-dev \
        ffmpeg \
        libasound2-dev \
        libportaudio2 \
        alsa-utils

    # Set CPU governor to performance (optional)
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
        warn "Consider setting CPU governor to 'performance' for better latency:"
        warn "  echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
    fi

    success "Raspberry Pi dependencies installed"
}

# Setup Python virtual environment
setup_venv() {
    info "Setting up Python virtual environment..."

    if [ ! -d "venv" ]; then
        $PYTHON -m venv venv
        info "Created virtual environment"
    else
        info "Virtual environment already exists"
    fi

    # Activate venv
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip wheel setuptools

    success "Virtual environment ready"
}

# Install Python dependencies
install_python_deps() {
    info "Installing Python dependencies..."

    source venv/bin/activate

    # Install package in development mode with dev dependencies
    pip install -e ".[dev]"

    success "Python dependencies installed"
}

# Install Ollama
install_ollama() {
    info "Checking Ollama installation..."

    if command -v ollama &> /dev/null; then
        info "Ollama already installed: $(ollama --version)"
    else
        info "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        success "Ollama installed"
    fi

    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        warn "Ollama not running. Start with: ollama serve"
    fi
}

# Main setup flow
main() {
    echo "========================================"
    echo "  Ara Voice Assistant - Setup Script"
    echo "========================================"
    echo

    OS=$(detect_os)
    ARCH=$(detect_arch)

    info "Detected OS: $OS"
    info "Detected Architecture: $ARCH"
    echo

    # Install system dependencies based on OS
    case $OS in
        macos)
            install_macos_deps
            ;;
        linux)
            install_linux_deps
            ;;
        raspberrypi)
            install_pi_deps
            ;;
        *)
            error "Unsupported OS: $OS"
            ;;
    esac

    # Check Python
    check_python

    # Setup virtual environment
    setup_venv

    # Install Python dependencies
    install_python_deps

    # Install Ollama
    install_ollama

    echo
    echo "========================================"
    success "Setup complete!"
    echo "========================================"
    echo
    info "Next steps:"
    echo "  1. Activate venv:  source venv/bin/activate"
    echo "  2. Download models: ./scripts/download_models.sh"
    echo "  3. Start Ollama:    ollama serve"
    echo "  4. Pull LLM model:  ollama pull llama3.2:3b"
    echo "  5. Run Ara:         python -m ara --config config/dev.yaml"
    echo
}

# Run main
main "$@"
