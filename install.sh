#!/usr/bin/env bash

set -e

APP_NAME="Local Code Agent"
MODEL_DEFAULT="qwen3:8b"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        Local Code Agent Installer        ║"
echo "╚══════════════════════════════════════════╝"
echo ""


# ============================================================
# Helpers
# ============================================================

info() {
    echo "  → $1"
}

success() {
    echo "  ✓ $1"
}

warning() {
    echo "  ! $1"
}

error() {
    echo "  ✗ $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}


# ============================================================
# Detect operating system
# ============================================================

OS="$(uname -s)"

case "$OS" in
    Darwin)
        PLATFORM="macOS"
        ;;
    Linux)
        PLATFORM="Linux"
        ;;
    *)
        error "Unsupported operating system: $OS"
        exit 1
        ;;
esac

info "Operating system: $PLATFORM"


# ============================================================
# Find Python
# ============================================================

PYTHON=""

for candidate in python3 python; do

    if command_exists "$candidate"; then

        VERSION="$("$candidate" -c \
            'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' \
            2>/dev/null || true)"

        MAJOR="${VERSION%%.*}"
        MINOR="${VERSION##*.}"

        if [[ "$MAJOR" == "3" ]] && [[ "$MINOR" -ge 10 ]]; then
            PYTHON="$candidate"
            break
        fi

    fi

done


if [[ -z "$PYTHON" ]]; then

    error "Python 3.10 or newer is required."

    echo ""

    if [[ "$PLATFORM" == "macOS" ]]; then
        echo "Install Python with:"
        echo ""
        echo "  brew install python"
    else
        echo "Install Python using your package manager."
    fi

    exit 1

fi

success "$("$PYTHON" --version 2>&1)"


# ============================================================
# Git
# ============================================================

if command_exists git; then

    success "Git"

else

    error "Git is required."

    if [[ "$PLATFORM" == "macOS" ]]; then
        echo ""
        echo "Run:"
        echo ""
        echo "  xcode-select --install"
    fi

    exit 1

fi


# ============================================================
# ripgrep
# ============================================================

if command_exists rg; then

    success "ripgrep"

else

    warning "ripgrep is not installed."

    if [[ "$PLATFORM" == "macOS" ]] && command_exists brew; then

        info "Installing ripgrep with Homebrew..."

        brew install ripgrep

    elif [[ "$PLATFORM" == "Linux" ]] && command_exists apt-get; then

        info "Installing ripgrep..."

        sudo apt-get update
        sudo apt-get install -y ripgrep

    else

        warning "Please install ripgrep manually."

    fi

fi


# ============================================================
# Python virtual environment
# ============================================================

echo ""

VENV_DIR="$HOME/.local-code-agent-venv"

info "Creating private Python environment..."

if [[ ! -d "$VENV_DIR" ]]; then

    "$PYTHON" -m venv "$VENV_DIR"

else

    info "Existing Python environment found."

fi

success "Python environment ready"


# ============================================================
# Install Python package
# ============================================================

info "Installing $APP_NAME..."

"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null

"$VENV_DIR/bin/python" -m pip install --upgrade . >/dev/null

success "Python package installed"


# ============================================================
# Install lca launcher
# ============================================================

#
# We deliberately use ~/.local/bin.
#
# This keeps the actual Python environment private.
#
# ~/.local/bin/lca
#       ↓
# ~/.local-code-agent-venv/bin/lca
#

BIN_DIR="$HOME/.local/bin"
LCA="$BIN_DIR/lca"

mkdir -p "$BIN_DIR"


cat > "$LCA" <<EOF
#!/usr/bin/env bash

exec "$VENV_DIR/bin/lca" "\$@"
EOF


chmod +x "$LCA"


if [[ ! -x "$LCA" ]]; then

    error "Could not create lca executable."

    exit 1

fi


success "lca executable installed"


# ============================================================
# Configure shell
# ============================================================

SHELL_NAME="$(basename "${SHELL:-}")"

case "$SHELL_NAME" in

    zsh)
        SHELL_CONFIG="$HOME/.zshrc"
        ;;

    bash)

        if [[ "$PLATFORM" == "macOS" ]]; then
            SHELL_CONFIG="$HOME/.bash_profile"
        else
            SHELL_CONFIG="$HOME/.bashrc"
        fi

        ;;

    *)

        SHELL_CONFIG=""

        ;;

esac


# ============================================================
# Add ~/.local/bin to PATH
# ============================================================

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'


if [[ -n "$SHELL_CONFIG" ]]; then

    touch "$SHELL_CONFIG"

    if ! grep -Fq 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_CONFIG"; then

        echo "" >> "$SHELL_CONFIG"
        echo "# Local Code Agent" >> "$SHELL_CONFIG"
        echo "$PATH_LINE" >> "$SHELL_CONFIG"

        success "Added ~/.local/bin to $SHELL_CONFIG"

    else

        success "~/.local/bin already configured in $SHELL_CONFIG"

    fi

else

    warning "Could not automatically configure shell PATH."

    echo ""
    echo "Add this to your shell configuration:"
    echo ""
    echo "  $PATH_LINE"
    echo ""

fi


# ============================================================
# IMPORTANT
#
# This only affects the installer process.
# A child shell script cannot modify its parent's environment.
#
# The .zshrc/.bashrc change above handles future terminals.
# ============================================================

export PATH="$BIN_DIR:$PATH"


# ============================================================
# Ollama
# ============================================================

echo ""
echo "Checking Ollama..."
echo ""


OLLAMA_URL=""
OLLAMA_FOUND=false


check_ollama() {

    local url="$1"

    "$PYTHON" - "$url" <<'PY'
import sys
import urllib.request

url = sys.argv[1].rstrip("/") + "/api/tags"

try:
    with urllib.request.urlopen(url, timeout=3) as response:

        if response.status == 200:
            sys.exit(0)

except Exception:
    pass

sys.exit(1)
PY

}


# ============================================================
# Try local Ollama
# ============================================================

if check_ollama "http://localhost:11434"; then

    OLLAMA_URL="http://localhost:11434"
    OLLAMA_FOUND=true

    success "Ollama found at $OLLAMA_URL"

fi


# ============================================================
# Ask for remote Ollama
# ============================================================

if [[ "$OLLAMA_FOUND" == false ]]; then

    warning "Ollama was not found at localhost:11434"

    echo ""
    echo "Do you have Ollama running on another machine?"
    echo ""
    echo "Example:"
    echo "  dd.local:11434"
    echo ""

    read -r -p "Ollama URL [skip]: " REMOTE_URL

    if [[ -n "$REMOTE_URL" ]]; then

        # Add http:// automatically.

        if [[ "$REMOTE_URL" != http://* ]] && \
           [[ "$REMOTE_URL" != https://* ]]; then

            REMOTE_URL="http://$REMOTE_URL"

        fi


        # Remove trailing slash.

        REMOTE_URL="${REMOTE_URL%/}"


        echo ""

        info "Checking $REMOTE_URL..."


        if check_ollama "$REMOTE_URL"; then

            OLLAMA_URL="$REMOTE_URL"
            OLLAMA_FOUND=true

            success "Connected to $OLLAMA_URL"

        else

            warning "Could not connect to $REMOTE_URL"

        fi

    fi

fi


# ============================================================
# No Ollama
# ============================================================

if [[ "$OLLAMA_FOUND" == false ]]; then

    echo ""

    warning "Ollama is not currently reachable."

    echo ""

    echo "Install Ollama from:"
    echo ""
    echo "  https://ollama.com"

    echo ""

    echo "Then install the model:"
    echo ""
    echo "  ollama pull $MODEL_DEFAULT"

    echo ""

    OLLAMA_URL="http://localhost:11434"

fi


# ============================================================
# Model
# ============================================================

MODEL="$MODEL_DEFAULT"


if [[ "$OLLAMA_FOUND" == true ]]; then

    echo ""

    info "Checking model $MODEL..."


    MODELS="$("$PYTHON" - "$OLLAMA_URL" <<'PY'
import sys
import json
import urllib.request

url = sys.argv[1].rstrip("/") + "/api/tags"

try:

    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.load(response)

    for model in data.get("models", []):

        name = model.get("name")

        if name:
            print(name)

except Exception:
    pass
PY
)"


    if echo "$MODELS" | grep -Fxq "$MODEL"; then

        success "Model $MODEL is available"

    else

        warning "Model $MODEL is not installed."

        echo ""

        read -r -p "Pull $MODEL now? [Y/n]: " PULL_MODEL

        PULL_MODEL="${PULL_MODEL:-Y}"


        if [[ "$PULL_MODEL" =~ ^[Yy]$ ]]; then

            if command_exists ollama; then

                echo ""

                info "Pulling $MODEL..."

                echo ""

                ollama pull "$MODEL"

                success "Model $MODEL installed"

            else

                warning "Ollama CLI is not installed on this computer."

                echo ""

                echo "If Ollama is remote, run this on that machine:"

                echo ""

                echo "  ollama pull $MODEL"

                echo ""

            fi

        fi

    fi

fi


# ============================================================
# Save configuration
# ============================================================

echo ""

info "Saving configuration..."


"$PYTHON" - "$OLLAMA_URL" "$MODEL" <<'PY'

import sys
import os
from pathlib import Path


url = sys.argv[1]
model = sys.argv[2]


override = os.getenv("LCA_CONFIG")


if override:

    path = Path(override).expanduser()

else:

    path = (
        Path.home()
        / ".config"
        / "local-code-agent"
        / "config.toml"
    )


path.parent.mkdir(
    parents=True,
    exist_ok=True,
)


path.write_text(
    f'ollama_url = "{url}"\n'
    f'model = "{model}"\n',
    encoding="utf-8",
)


print(path)

PY


success "Configuration saved"


# ============================================================
# Test the actual launcher
# ============================================================

echo ""

info "Testing lca..."


if "$LCA" --version >/dev/null 2>&1; then

    success "lca works"

else

    error "lca could not be executed."

    echo ""

    echo "Expected executable:"
    echo ""
    echo "  $LCA"

    echo ""

    exit 1

fi


# ============================================================
# Verify PATH
# ============================================================

if command_exists lca; then

    success "lca command is available"

else

    warning "lca is installed but the current shell cannot find it."

    echo ""

    echo "The installation itself is OK."

    echo ""

    echo "Run:"
    echo ""
    echo "  source ~/.zshrc"

    echo ""

    echo "Then:"
    echo ""
    echo "  lca doctor"

    echo ""

fi


# ============================================================
# Finished
# ============================================================

echo ""

echo "╔══════════════════════════════════════════╗"
echo "║          Installation complete!          ║"
echo "╚══════════════════════════════════════════╝"

echo ""

echo "IMPORTANT:"
echo ""
echo "If 'lca' is not found in this terminal, run:"
echo ""
echo "  source ~/.zshrc"

echo ""

echo "Then:"
echo ""
echo "  lca doctor"

echo ""

echo "From a project:"
echo ""
echo "  cd /path/to/your/project"
echo "  lca"

echo ""

echo "Configuration:"
echo ""
echo "  lca config"

echo ""

echo "Have fun. 🦴"

echo ""