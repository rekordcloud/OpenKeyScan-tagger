#!/bin/bash

# Build script for OpenKeyScan Tagger
# Builds the standalone executable using PyInstaller

set -e  # Exit on error

echo "======================================================================"
echo "Building OpenKeyScan Tagger Standalone Application"
echo "======================================================================"
echo ""

# Check if pyinstaller is available
if ! command -v pyinstaller &> /dev/null; then
    echo "Error: pyinstaller not found"
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

# Run PyInstaller with --noconfirm to skip prompts
pyinstaller --noconfirm openkeyscan_tagger.spec

echo ""
echo "======================================================================"
echo "Build Complete!"
echo "======================================================================"
echo ""
echo "Output:"
echo "  Executable: dist/openkeyscan-tagger/openkeyscan-tagger"
echo "  Archive:    dist/openkeyscan-tagger.zip"
echo ""
echo "Test the build:"
echo "  ./dist/openkeyscan-tagger/openkeyscan-tagger"
echo ""
echo "Or extract and distribute the zip file:"
echo "  dist/openkeyscan-tagger.zip"
echo ""

# Detect architecture and convert to Node.js format
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    ARCH="x64"
fi
DEST_DIR="$HOME/openkeyscan/build/lib/mac/$ARCH"

echo "======================================================================"
echo "Moving build to library directory"
echo "======================================================================"
echo ""
echo "Architecture: $ARCH"
echo "Destination:  $DEST_DIR"
echo ""

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Move the zip file to the destination, replacing any existing file
cp -f dist/openkeyscan-tagger.zip "$DEST_DIR/"

echo "Build successfully moved to:"
echo "  $DEST_DIR/openkeyscan-tagger.zip"
echo ""
