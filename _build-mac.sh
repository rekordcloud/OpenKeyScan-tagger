#!/bin/bash

# Build script for OpenKeyScan Tagger
# Builds the standalone executable using PyInstaller

set -e  # Exit on error

# Parse architecture argument
if [ -z "$1" ]; then
    echo "Error: Architecture argument required (arm64 or x64)"
    echo "Usage: $0 <arm64|x64>"
    exit 1
fi

TARGET_ARCH="$1"
if [ "$TARGET_ARCH" != "arm64" ] && [ "$TARGET_ARCH" != "x64" ]; then
    echo "Error: Invalid architecture '$TARGET_ARCH'"
    echo "Must be 'arm64' or 'x64'"
    exit 1
fi

# Save original architecture for directory naming (arm64 or x64)
ARCH_DIR="$TARGET_ARCH"

# Convert x64 to x86_64 for PyInstaller
if [ "$TARGET_ARCH" = "x64" ]; then
    PYINSTALLER_ARCH="x86_64"
else
    PYINSTALLER_ARCH="arm64"
fi

echo "======================================================================"
echo "Building OpenKeyScan Tagger Standalone Application"
echo "Architecture: $TARGET_ARCH"
echo "======================================================================"
echo ""

# Check if pipenv is available
if ! command -v pipenv &> /dev/null; then
    echo "Error: pipenv not found"
    echo "Install it with: pip install pipenv"
    exit 1
fi

# Check if pyinstaller is installed in the pipenv environment
if ! pipenv run python -c "import PyInstaller" &> /dev/null; then
    echo "Error: pyinstaller not found in pipenv environment"
    echo "Install it with: pipenv install --dev"
    exit 1
fi

# Clean previous build artifacts (optional, PyInstaller will handle this)
if [ -d "build" ]; then
    echo "Cleaning build/ directory..."
    rm -rf build
fi

echo "Starting PyInstaller build..."
echo ""

# Export target architecture for spec file to read
# PyInstaller will validate that current terminal arch matches this target
export TARGET_ARCH="$PYINSTALLER_ARCH"

# Run PyInstaller with --noconfirm to skip prompts
pipenv run pyinstaller --noconfirm openkeyscan_tagger.spec

echo ""
echo "======================================================================"
echo "Post-build: Cleanup"
echo "======================================================================"
echo ""

# Remove unused OpenSSL libraries
echo "Removing unused OpenSSL libraries..."
rm -f dist/openkeyscan-tagger/_internal/libssl.3.dylib
rm -f dist/openkeyscan-tagger/_internal/libcrypto.3.dylib
echo "✓ Removed OpenSSL libraries"
echo ""

echo "======================================================================"
echo "Build Complete!"
echo "======================================================================"
echo ""
echo "Output:"
echo "  Executable: dist/openkeyscan-tagger/openkeyscan-tagger"
echo ""

# Copy to distribution directory and clean up Python.framework
DEST_DIR="$HOME/workspace/openkeyscan/openkeyscan-app/build/lib/mac/$ARCH_DIR"

echo "Installing to distribution directory..."
echo "  Architecture: $ARCH_DIR"
echo "  Destination:  $DEST_DIR"
echo ""

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Copy the build folder to distribution directory first
echo "Copying build to distribution directory..."
rm -rf "$DEST_DIR/openkeyscan-tagger"
cp -r dist/openkeyscan-tagger "$DEST_DIR/"
echo "✓ Copied to: $DEST_DIR/openkeyscan-tagger"
echo ""

# Delete Python.framework from the distribution copy (causes signing issues, not needed)
echo "Removing Python.framework from distribution..."
if [ -d "$DEST_DIR/openkeyscan-tagger/_internal/Python.framework" ]; then
    rm -rf "$DEST_DIR/openkeyscan-tagger/_internal/Python.framework"
    echo "✓ Removed Python.framework"
else
    echo "  (Python.framework not found, skipping)"
fi

echo ""
echo "======================================================================"
echo "Installation Complete!"
echo "======================================================================"
echo ""
echo "Test the build:"
echo "  ./dist/openkeyscan-tagger/openkeyscan-tagger"
echo ""
echo "Distribution location:"
echo "  $DEST_DIR/openkeyscan-tagger/"
echo ""
