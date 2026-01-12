#!/bin/bash
# Ara Voice Assistant - Model Download Script
# Downloads required models for offline operation

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

# Default settings
MODELS_DIR="models"
WHISPER_MODEL="base.en"
PIPER_VOICE="en_US-lessac-medium"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --whisper)
            WHISPER_MODEL="$2"
            shift 2
            ;;
        --piper-voice)
            PIPER_VOICE="$2"
            shift 2
            ;;
        --models-dir)
            MODELS_DIR="$2"
            shift 2
            ;;
        --all)
            DOWNLOAD_ALL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --whisper MODEL      Whisper model to download (default: base.en)"
            echo "                       Options: tiny.en, base.en, small.en, medium.en"
            echo "  --piper-voice VOICE  Piper voice to download (default: en_US-lessac-medium)"
            echo "  --models-dir DIR     Directory to store models (default: models)"
            echo "  --all                Download all recommended models"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Create models directory structure
setup_dirs() {
    info "Setting up models directory..."
    mkdir -p "$MODELS_DIR/whisper"
    mkdir -p "$MODELS_DIR/piper"
    success "Directories created"
}

# Download Whisper model for faster-whisper (CTranslate2 format)
download_whisper() {
    local model=$1
    local target_dir="$MODELS_DIR/whisper"

    info "Downloading Whisper model: $model..."

    # faster-whisper uses Hugging Face models in CTranslate2 format
    local hf_repo="Systran/faster-whisper-${model}"
    local model_dir="$target_dir/faster-whisper-${model}"

    if [ -d "$model_dir" ] && [ -f "$model_dir/model.bin" ]; then
        info "Whisper model $model already exists, skipping..."
        return 0
    fi

    # Check if huggingface-cli is available
    if command -v huggingface-cli &> /dev/null; then
        huggingface-cli download "$hf_repo" --local-dir "$model_dir" --local-dir-use-symlinks False
    else
        # Alternative: Use Python to download
        info "Using Python to download model..."
        python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='$hf_repo',
    local_dir='$model_dir',
    local_dir_use_symlinks=False
)
" || {
            warn "Failed to download from Hugging Face. Please install huggingface_hub:"
            warn "  pip install huggingface_hub"
            warn "Or download manually from: https://huggingface.co/$hf_repo"
            return 1
        }
    fi

    success "Whisper model $model downloaded to $model_dir"
}

# Download Piper TTS voice
download_piper_voice() {
    local voice=$1
    local target_dir="$MODELS_DIR/piper"

    info "Downloading Piper voice: $voice..."

    # Piper voices are hosted on Hugging Face
    local voice_file="${voice}.onnx"
    local config_file="${voice}.onnx.json"
    local voice_path="$target_dir/$voice_file"
    local config_path="$target_dir/$config_file"

    if [ -f "$voice_path" ] && [ -f "$config_path" ]; then
        info "Piper voice $voice already exists, skipping..."
        return 0
    fi

    # Piper voices are organized by language
    # Format: {lang}_{region}-{name}-{quality}
    # e.g., en_US-lessac-medium
    local lang_region="${voice%%-*}"  # en_US
    local lang="${lang_region%%_*}"   # en

    local base_url="https://huggingface.co/rhasspy/piper-voices/resolve/main/${lang}/${lang_region}/${voice#*-}/"

    # Download model file
    info "Downloading $voice_file..."
    curl -L -# -o "$voice_path" "${base_url}${voice_file}" || {
        warn "Failed to download Piper voice model"
        warn "Manual download: ${base_url}${voice_file}"
        return 1
    }

    # Download config file
    info "Downloading $config_file..."
    curl -L -# -o "$config_path" "${base_url}${config_file}" || {
        warn "Failed to download Piper voice config"
        warn "Manual download: ${base_url}${config_file}"
        return 1
    }

    success "Piper voice $voice downloaded to $target_dir"
}

# Download Ollama LLM model
download_ollama_model() {
    local model=$1

    info "Checking Ollama model: $model..."

    if ! command -v ollama &> /dev/null; then
        warn "Ollama not installed. Install with: curl -fsSL https://ollama.com/install.sh | sh"
        return 1
    fi

    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
        warn "Ollama not running. Start with: ollama serve"
        warn "Then run: ollama pull $model"
        return 1
    fi

    # Check if model exists
    if ollama list | grep -q "$model"; then
        info "Ollama model $model already available"
        return 0
    fi

    info "Pulling Ollama model: $model..."
    ollama pull "$model"

    success "Ollama model $model ready"
}

# Verify downloads
verify_models() {
    info "Verifying model downloads..."

    local all_good=true

    # Check Whisper
    if [ -d "$MODELS_DIR/whisper/faster-whisper-${WHISPER_MODEL}" ]; then
        success "Whisper model: $WHISPER_MODEL ✓"
    else
        warn "Whisper model: $WHISPER_MODEL not found"
        all_good=false
    fi

    # Check Piper
    if [ -f "$MODELS_DIR/piper/${PIPER_VOICE}.onnx" ]; then
        success "Piper voice: $PIPER_VOICE ✓"
    else
        warn "Piper voice: $PIPER_VOICE not found"
        all_good=false
    fi

    # Check Ollama
    if command -v ollama &> /dev/null; then
        if ollama list 2>/dev/null | grep -q "llama3.2:3b"; then
            success "Ollama model: llama3.2:3b ✓"
        else
            warn "Ollama model: llama3.2:3b not pulled"
            all_good=false
        fi
    else
        warn "Ollama not installed"
        all_good=false
    fi

    if [ "$all_good" = true ]; then
        success "All models verified!"
    else
        warn "Some models missing - check messages above"
    fi
}

# Main download flow
main() {
    echo "========================================"
    echo "  Ara Voice Assistant - Model Download"
    echo "========================================"
    echo

    info "Whisper model: $WHISPER_MODEL"
    info "Piper voice: $PIPER_VOICE"
    info "Models directory: $MODELS_DIR"
    echo

    # Setup directories
    setup_dirs

    # Download Whisper model
    download_whisper "$WHISPER_MODEL" || true

    # Download additional Whisper models if --all
    if [ "$DOWNLOAD_ALL" = true ]; then
        info "Downloading additional Whisper models..."
        download_whisper "tiny.en" || true
        download_whisper "small.en" || true
    fi

    # Download Piper voice
    download_piper_voice "$PIPER_VOICE" || true

    # Download additional Piper voices if --all
    if [ "$DOWNLOAD_ALL" = true ]; then
        info "Downloading additional Piper voices..."
        download_piper_voice "en_US-amy-medium" || true
        download_piper_voice "en_GB-alan-medium" || true
    fi

    # Download Ollama model
    download_ollama_model "llama3.2:3b" || true

    echo
    echo "========================================"
    verify_models
    echo "========================================"
    echo
    info "Next steps:"
    echo "  1. Start Ollama:     ollama serve"
    echo "  2. Run Ara:          python -m ara --config config/dev.yaml"
    echo
}

# Run main
main "$@"
