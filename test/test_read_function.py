#!/usr/bin/env python3
"""
Comprehensive test suite for read_key_from_file function

Tests:
1. Reading from 'initialkey' field (standard)
2. Reading from 'KEY' field (legacy/backward compatibility)
3. Field priority when both exist
4. All supported audio formats
5. Edge cases (no key, corrupted files, etc.)
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path to import openkeyscan_tagger
sys.path.insert(0, str(Path(__file__).parent.parent))

from openkeyscan_tagger import read_key_from_file, write_key_to_file

# Import mutagen for manual tag manipulation in tests
from mutagen.id3 import ID3, TKEY, ID3NoHeaderError
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.aiff import AIFF
from mutagen.wave import WAVE


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add_pass(self, test_name, message=""):
        self.passed += 1
        self.tests.append({'name': test_name, 'status': 'PASS', 'message': message})
        print(f"✅ PASS: {test_name}")
        if message:
            print(f"   {message}")

    def add_fail(self, test_name, message=""):
        self.failed += 1
        self.tests.append({'name': test_name, 'status': 'FAIL', 'message': message})
        print(f"❌ FAIL: {test_name}")
        if message:
            print(f"   {message}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Total: {total} tests")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed / total * 100) if total > 0 else 0:.1f}%\n")

        if self.failed > 0:
            print("Failed tests:")
            for test in self.tests:
                if test['status'] == 'FAIL':
                    print(f"  • {test['name']}: {test['message']}")
            print()

        return self.failed == 0


def copy_test_file(test_files_dir, ext):
    """Copy a test file to a temporary location for manipulation."""
    src = Path(test_files_dir) / f"test.{ext}"
    if not src.exists():
        return None

    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=f".{ext}")
    os.close(fd)
    shutil.copy(src, temp_path)
    return Path(temp_path)


def test_read_after_write(results, test_files_dir):
    """Test reading keys after writing them (round-trip test)."""
    print("\n" + "=" * 60)
    print("Round-Trip Tests (Write → Read)")
    print("=" * 60 + "\n")

    test_key = "5A"
    formats = ['mp3', 'mp4', 'm4a', 'aac', 'flac', 'ogg', 'aiff', 'aif', 'wav']

    for ext in formats:
        temp_file = copy_test_file(test_files_dir, ext)
        if not temp_file:
            print(f"⚠️  SKIP: {ext.upper()} (test file not found)")
            continue

        try:
            # Write key
            success, error, fmt = write_key_to_file(temp_file, test_key)
            if not success:
                results.add_fail(f"Round-trip {ext.upper()}", f"Write failed: {error}")
                continue

            # Read key back
            success, key_value, fmt, error = read_key_from_file(temp_file)
            if not success:
                results.add_fail(f"Round-trip {ext.upper()}", f"Read failed: {error}")
            elif key_value != test_key:
                results.add_fail(f"Round-trip {ext.upper()}",
                                f"Expected '{test_key}', got '{key_value}'")
            else:
                results.add_pass(f"Round-trip {ext.upper()}",
                               f"Wrote '{test_key}', read '{key_value}'")

        finally:
            if temp_file.exists():
                temp_file.unlink()


def test_read_from_initialkey_only(results, test_files_dir):
    """Test reading from 'initialkey' field when only that field is set."""
    print("\n" + "=" * 60)
    print("Read from 'initialkey' Only (Standard Field)")
    print("=" * 60 + "\n")

    test_key = "9A"

    # Test FLAC
    temp_file = copy_test_file(test_files_dir, 'flac')
    if temp_file:
        try:
            audio = FLAC(temp_file)
            # Set only initialkey, remove KEY if present
            audio['initialkey'] = test_key
            if 'KEY' in audio:
                del audio['KEY']
            audio.save()

            # Read back
            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass("FLAC initialkey-only read", f"Read '{key_value}' from initialkey")
            else:
                results.add_fail("FLAC initialkey-only read",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test OGG
    temp_file = copy_test_file(test_files_dir, 'ogg')
    if temp_file:
        try:
            audio = OggVorbis(temp_file)
            audio['initialkey'] = test_key
            if 'KEY' in audio:
                del audio['KEY']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass("OGG initialkey-only read", f"Read '{key_value}' from initialkey")
            else:
                results.add_fail("OGG initialkey-only read",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test MP4/M4A
    for ext in ['mp4', 'm4a']:
        temp_file = copy_test_file(test_files_dir, ext)
        if not temp_file:
            continue
        try:
            audio = MP4(temp_file)
            audio['----:com.apple.iTunes:initialkey'] = test_key.encode('utf-8')
            if '----:com.apple.iTunes:KEY' in audio:
                del audio['----:com.apple.iTunes:KEY']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass(f"{ext.upper()} initialkey-only read",
                               f"Read '{key_value}' from initialkey")
            else:
                results.add_fail(f"{ext.upper()} initialkey-only read",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()


def test_read_from_KEY_only(results, test_files_dir):
    """Test reading from 'KEY' field when only that field is set (legacy compatibility)."""
    print("\n" + "=" * 60)
    print("Read from 'KEY' Only (Legacy Compatibility)")
    print("=" * 60 + "\n")

    test_key = "3B"

    # Test FLAC
    temp_file = copy_test_file(test_files_dir, 'flac')
    if temp_file:
        try:
            audio = FLAC(temp_file)
            audio['KEY'] = test_key
            if 'initialkey' in audio:
                del audio['initialkey']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass("FLAC KEY-only read", f"Read '{key_value}' from KEY (legacy)")
            else:
                results.add_fail("FLAC KEY-only read",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test OGG
    temp_file = copy_test_file(test_files_dir, 'ogg')
    if temp_file:
        try:
            audio = OggVorbis(temp_file)
            audio['KEY'] = test_key
            if 'initialkey' in audio:
                del audio['initialkey']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass("OGG KEY-only read", f"Read '{key_value}' from KEY (legacy)")
            else:
                results.add_fail("OGG KEY-only read",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test MP4/M4A
    for ext in ['mp4', 'm4a']:
        temp_file = copy_test_file(test_files_dir, ext)
        if not temp_file:
            continue
        try:
            audio = MP4(temp_file)
            audio['----:com.apple.iTunes:KEY'] = test_key.encode('utf-8')
            if '----:com.apple.iTunes:initialkey' in audio:
                del audio['----:com.apple.iTunes:initialkey']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass(f"{ext.upper()} KEY-only read",
                               f"Read '{key_value}' from KEY (legacy)")
            else:
                results.add_fail(f"{ext.upper()} KEY-only read",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()


def test_field_priority(results, test_files_dir):
    """Test that 'initialkey' is preferred over 'KEY' when both are present."""
    print("\n" + "=" * 60)
    print("Field Priority Tests (initialkey > KEY)")
    print("=" * 60 + "\n")

    initialkey_value = "7A"
    KEY_value = "8B"  # Different value to test priority

    # Test FLAC
    temp_file = copy_test_file(test_files_dir, 'flac')
    if temp_file:
        try:
            audio = FLAC(temp_file)
            audio['initialkey'] = initialkey_value
            audio['KEY'] = KEY_value
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == initialkey_value:
                results.add_pass("FLAC field priority",
                               f"Correctly preferred initialkey '{initialkey_value}' over KEY '{KEY_value}'")
            else:
                results.add_fail("FLAC field priority",
                               f"Expected '{initialkey_value}' (initialkey), got '{key_value}'")
        finally:
            temp_file.unlink()

    # Test OGG
    temp_file = copy_test_file(test_files_dir, 'ogg')
    if temp_file:
        try:
            audio = OggVorbis(temp_file)
            audio['initialkey'] = initialkey_value
            audio['KEY'] = KEY_value
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == initialkey_value:
                results.add_pass("OGG field priority",
                               f"Correctly preferred initialkey '{initialkey_value}' over KEY '{KEY_value}'")
            else:
                results.add_fail("OGG field priority",
                               f"Expected '{initialkey_value}' (initialkey), got '{key_value}'")
        finally:
            temp_file.unlink()

    # Test MP4
    temp_file = copy_test_file(test_files_dir, 'mp4')
    if temp_file:
        try:
            audio = MP4(temp_file)
            audio['----:com.apple.iTunes:initialkey'] = initialkey_value.encode('utf-8')
            audio['----:com.apple.iTunes:KEY'] = KEY_value.encode('utf-8')
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == initialkey_value:
                results.add_pass("MP4 field priority",
                               f"Correctly preferred initialkey '{initialkey_value}' over KEY '{KEY_value}'")
            else:
                results.add_fail("MP4 field priority",
                               f"Expected '{initialkey_value}' (initialkey), got '{key_value}'")
        finally:
            temp_file.unlink()


def test_read_no_key(results, test_files_dir):
    """Test reading from files with no key field set."""
    print("\n" + "=" * 60)
    print("Read from Files with No Key")
    print("=" * 60 + "\n")

    formats = ['mp3', 'flac', 'ogg', 'mp4']

    for ext in formats:
        temp_file = copy_test_file(test_files_dir, ext)
        if not temp_file:
            continue

        try:
            # Remove all key fields
            if ext == 'mp3':
                try:
                    audio = ID3(temp_file)
                    audio.delall('TKEY')
                    audio.save()
                except ID3NoHeaderError:
                    pass
            elif ext == 'flac':
                audio = FLAC(temp_file)
                if 'KEY' in audio:
                    del audio['KEY']
                if 'initialkey' in audio:
                    del audio['initialkey']
                audio.save()
            elif ext == 'ogg':
                audio = OggVorbis(temp_file)
                if 'KEY' in audio:
                    del audio['KEY']
                if 'initialkey' in audio:
                    del audio['initialkey']
                audio.save()
            elif ext == 'mp4':
                audio = MP4(temp_file)
                if '----:com.apple.iTunes:KEY' in audio:
                    del audio['----:com.apple.iTunes:KEY']
                if '----:com.apple.iTunes:initialkey' in audio:
                    del audio['----:com.apple.iTunes:initialkey']
                audio.save()

            # Read back - should return None
            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value is None:
                results.add_pass(f"{ext.upper()} no-key read", "Correctly returned None")
            else:
                results.add_fail(f"{ext.upper()} no-key read",
                               f"Expected None, got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()


def test_various_key_formats(results, test_files_dir):
    """Test reading various key format strings."""
    print("\n" + "=" * 60)
    print("Various Key Format Tests")
    print("=" * 60 + "\n")

    test_keys = [
        "1A", "12B",  # Camelot notation
        "1m", "12d",  # OpenKey notation
        "C major", "D minor",  # Plain text
        "Gmaj", "Am",  # Abbreviated
        "Custom Key 123"  # Custom format
    ]

    temp_file = copy_test_file(test_files_dir, 'flac')
    if not temp_file:
        print("⚠️  SKIP: FLAC test file not found")
        return

    for test_key in test_keys:
        try:
            # Write and read
            success, error, fmt = write_key_to_file(temp_file, test_key)
            if not success:
                results.add_fail(f"Key format '{test_key}'", f"Write failed: {error}")
                continue

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass(f"Key format '{test_key}'", f"Successfully round-tripped")
            else:
                results.add_fail(f"Key format '{test_key}'",
                               f"Expected '{test_key}', got '{key_value}'")
        except Exception as e:
            results.add_fail(f"Key format '{test_key}'", f"Exception: {str(e)}")

    if temp_file.exists():
        temp_file.unlink()


def test_case_insensitive_field_names(results, test_files_dir):
    """Test that field name lookups are case-insensitive.

    Note: Mutagen automatically normalizes Vorbis comment keys to lowercase,
    so we can only test case variations that mutagen preserves (like MP4 tags).
    The case-insensitive lookup is still useful for compatibility with tools
    that might read Vorbis tags differently.
    """
    print("\n" + "=" * 60)
    print("Case-Insensitive Field Name Tests")
    print("=" * 60 + "\n")

    test_key = "10A"

    # Test MP4 with uppercase iTunes tag
    temp_file = copy_test_file(test_files_dir, 'mp4')
    if temp_file:
        try:
            audio = MP4(temp_file)
            # MP4 tags preserve case, unlike Vorbis comments
            audio['----:com.apple.iTunes:INITIALKEY'] = test_key.encode('utf-8')
            if '----:com.apple.iTunes:initialkey' in audio:
                del audio['----:com.apple.iTunes:initialkey']
            if '----:com.apple.iTunes:KEY' in audio:
                del audio['----:com.apple.iTunes:KEY']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass("MP4 uppercase iTunes:INITIALKEY",
                               f"Read '{key_value}' from uppercase iTunes tag")
            else:
                results.add_fail("MP4 uppercase iTunes:INITIALKEY",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test MP4 with mixed-case iTunes tag
    temp_file = copy_test_file(test_files_dir, 'mp4')
    if temp_file:
        try:
            audio = MP4(temp_file)
            audio['----:com.apple.iTunes:InitialKey'] = test_key.encode('utf-8')
            if '----:com.apple.iTunes:initialkey' in audio:
                del audio['----:com.apple.iTunes:initialkey']
            if '----:com.apple.iTunes:INITIALKEY' in audio:
                del audio['----:com.apple.iTunes:INITIALKEY']
            if '----:com.apple.iTunes:KEY' in audio:
                del audio['----:com.apple.iTunes:KEY']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass("MP4 mixed-case iTunes:InitialKey",
                               f"Read '{key_value}' from mixed-case iTunes tag")
            else:
                results.add_fail("MP4 mixed-case iTunes:InitialKey",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test MP4 with uppercase KEY tag (legacy)
    temp_file = copy_test_file(test_files_dir, 'mp4')
    if temp_file:
        try:
            audio = MP4(temp_file)
            audio['----:com.apple.iTunes:KEY'] = test_key.encode('utf-8')
            if '----:com.apple.iTunes:key' in audio:
                del audio['----:com.apple.iTunes:key']
            if '----:com.apple.iTunes:initialkey' in audio:
                del audio['----:com.apple.iTunes:initialkey']
            if '----:com.apple.iTunes:INITIALKEY' in audio:
                del audio['----:com.apple.iTunes:INITIALKEY']
            audio.save()

            success, key_value, fmt, error = read_key_from_file(temp_file)
            if success and key_value == test_key:
                results.add_pass("MP4 uppercase iTunes:KEY (legacy)",
                               f"Read '{key_value}' from uppercase KEY tag")
            else:
                results.add_fail("MP4 uppercase iTunes:KEY (legacy)",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()


def main():
    """Run all tests."""
    print("═" * 60)
    print("  Read Function Comprehensive Test Suite")
    print("═" * 60)

    test_files_dir = sys.argv[1] if len(sys.argv) > 1 else './test-files'
    test_files_dir = Path(test_files_dir)

    if not test_files_dir.exists():
        print(f"\n❌ Test files directory not found: {test_files_dir}")
        print("Please create test files first.\n")
        sys.exit(1)

    print(f"\nTest files directory: {test_files_dir}\n")

    results = TestResults()

    # Run all test suites
    test_read_after_write(results, test_files_dir)
    test_read_from_initialkey_only(results, test_files_dir)
    test_read_from_KEY_only(results, test_files_dir)
    test_field_priority(results, test_files_dir)
    test_read_no_key(results, test_files_dir)
    test_various_key_formats(results, test_files_dir)
    test_case_insensitive_field_names(results, test_files_dir)

    # Print summary
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
