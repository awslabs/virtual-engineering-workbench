#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$HOME/.local/bin"
BIN_NAME="vew"

echo "Building vew (release)..."
cargo build --release

echo "Installing to $INSTALL_DIR/$BIN_NAME..."
mkdir -p "$INSTALL_DIR"
cp "target/release/$BIN_NAME" "$INSTALL_DIR/$BIN_NAME"
chmod +x "$INSTALL_DIR/$BIN_NAME"

if echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    echo "✓ $INSTALL_DIR is already in your PATH."
else
    echo ""
    echo "⚠ $INSTALL_DIR is not in your PATH."
    echo "  Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo ""
    echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
    echo ""
fi

echo "Done. Run 'vew --help' to get started."
