#!/usr/bin/env python3
"""
Cross-Compatibility Test Suite for lexicon-tagger

Tests that openkeyscan-tagger can read files written in lexicon-tagger format,
and that lexicon-tagger format files are correctly handled.

This ensures full compatibility between the two tools.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openkeyscan_tagger import read_key_from_file, write_key_to_file

# Import mutagen for simulating lexicon-tagger writes
from mutagen.id3 import ID3, TKEY, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4FreeForm
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis


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
    """Copy a test file to a temporary location."""
    src = Path(test_files_dir) / f"test.{ext}"
    if not src.exists():
        return None

    fd, temp_path = tempfile.mkstemp(suffix=f".{ext}")
    os.close(fd)
    shutil.copy(src, temp_path)
    return Path(temp_path)


def simulate_lexicon_tagger_write_mp3(file_path, key_value):
    """Simulate how lexicon-tagger writes MP3 files (TKEY frame)."""
    try:
        audio = ID3(file_path)
    except ID3NoHeaderError:
        audio = ID3()

    audio.delall('TKEY')
    audio.add(TKEY(encoding=3, text=key_value))
    audio.save(file_path, v2_version=4)


def simulate_lexicon_tagger_write_flac(file_path, key_value):
    """Simulate how lexicon-tagger writes FLAC files (initialkey field)."""
    audio = FLAC(file_path)
    audio['initialkey'] = key_value
    # lexicon-tagger does NOT write 'KEY' field, only 'initialkey'
    if 'KEY' in audio:
        del audio['KEY']
    audio.save()


def simulate_lexicon_tagger_write_ogg(file_path, key_value):
    """Simulate how lexicon-tagger writes OGG files (initialkey field)."""
    audio = OggVorbis(file_path)
    audio['initialkey'] = key_value
    # lexicon-tagger does NOT write 'KEY' field, only 'initialkey'
    if 'KEY' in audio:
        del audio['KEY']
    audio.save()


def simulate_lexicon_tagger_write_mp4(file_path, key_value):
    """Simulate how lexicon-tagger writes MP4 files (initialkey freeform tag)."""
    audio = MP4(file_path)
    # lexicon-tagger uses lowercase 'initialkey', not 'KEY'
    audio['----:com.apple.iTunes:initialkey'] = MP4FreeForm(bytes(key_value, "utf-8"))
    # Remove 'KEY' field if present
    if '----:com.apple.iTunes:KEY' in audio:
        del audio['----:com.apple.iTunes:KEY']
    audio.save()


def test_read_lexicon_format_files(results, test_files_dir):
    """Test reading files written in lexicon-tagger format."""
    print("\n" + "=" * 60)
    print("Read Files Written in lexicon-tagger Format")
    print("=" * 60 + "\n")

    test_key = "11A"

    # Test MP3 (TKEY - same format)
    temp_file = copy_test_file(test_files_dir, 'mp3')
    if temp_file:
        try:
            simulate_lexicon_tagger_write_mp3(temp_file, test_key)
            success, key_value, fmt, error = read_key_from_file(temp_file)

            if success and key_value == test_key:
                results.add_pass("Read lexicon-tagger MP3",
                               f"Successfully read TKEY '{key_value}'")
            else:
                results.add_fail("Read lexicon-tagger MP3",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test FLAC (initialkey only)
    temp_file = copy_test_file(test_files_dir, 'flac')
    if temp_file:
        try:
            simulate_lexicon_tagger_write_flac(temp_file, test_key)
            success, key_value, fmt, error = read_key_from_file(temp_file)

            if success and key_value == test_key:
                results.add_pass("Read lexicon-tagger FLAC",
                               f"Successfully read initialkey '{key_value}'")
            else:
                results.add_fail("Read lexicon-tagger FLAC",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test OGG (initialkey only)
    temp_file = copy_test_file(test_files_dir, 'ogg')
    if temp_file:
        try:
            simulate_lexicon_tagger_write_ogg(temp_file, test_key)
            success, key_value, fmt, error = read_key_from_file(temp_file)

            if success and key_value == test_key:
                results.add_pass("Read lexicon-tagger OGG",
                               f"Successfully read initialkey '{key_value}'")
            else:
                results.add_fail("Read lexicon-tagger OGG",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test MP4 (initialkey freeform tag)
    temp_file = copy_test_file(test_files_dir, 'mp4')
    if temp_file:
        try:
            simulate_lexicon_tagger_write_mp4(temp_file, test_key)
            success, key_value, fmt, error = read_key_from_file(temp_file)

            if success and key_value == test_key:
                results.add_pass("Read lexicon-tagger MP4",
                               f"Successfully read initialkey '{key_value}'")
            else:
                results.add_fail("Read lexicon-tagger MP4",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()

    # Test M4A (initialkey freeform tag)
    temp_file = copy_test_file(test_files_dir, 'm4a')
    if temp_file:
        try:
            simulate_lexicon_tagger_write_mp4(temp_file, test_key)
            success, key_value, fmt, error = read_key_from_file(temp_file)

            if success and key_value == test_key:
                results.add_pass("Read lexicon-tagger M4A",
                               f"Successfully read initialkey '{key_value}'")
            else:
                results.add_fail("Read lexicon-tagger M4A",
                               f"Expected '{test_key}', got '{key_value}' (error: {error})")
        finally:
            temp_file.unlink()


def verify_lexicon_can_read_format(file_path, expected_key):
    """
    Verify that a file written by openkeyscan-tagger has fields that lexicon-tagger can read.

    Since we can't actually run lexicon-tagger, we simulate by checking for the presence
    of the 'initialkey' field that lexicon-tagger expects.
    """
    file_ext = file_path.suffix.lower()

    if file_ext == '.mp3':
        # lexicon-tagger reads TKEY (same as openkeyscan-tagger)
        try:
            audio = ID3(file_path)
            if 'TKEY' in audio:
                key = str(audio['TKEY'].text[0]) if audio['TKEY'].text else None
                return key == expected_key
        except:
            return False

    elif file_ext == '.flac':
        # lexicon-tagger reads 'initialkey'
        audio = FLAC(file_path)
        if 'initialkey' in audio:
            key = audio['initialkey'][0] if audio['initialkey'] else None
            return key == expected_key
        return False

    elif file_ext == '.ogg':
        # lexicon-tagger reads 'initialkey'
        audio = OggVorbis(file_path)
        if 'initialkey' in audio:
            key = audio['initialkey'][0] if audio['initialkey'] else None
            return key == expected_key
        return False

    elif file_ext in ['.mp4', '.m4a']:
        # lexicon-tagger reads '----:com.apple.iTunes:initialkey'
        audio = MP4(file_path)
        if '----:com.apple.iTunes:initialkey' in audio:
            key_bytes = audio['----:com.apple.iTunes:initialkey'][0]
            key = key_bytes.decode('utf-8') if isinstance(key_bytes, bytes) else str(key_bytes)
            return key == expected_key
        return False

    return False


def test_write_compatible_with_lexicon(results, test_files_dir):
    """Test that files written by openkeyscan-tagger can be read by lexicon-tagger."""
    print("\n" + "=" * 60)
    print("Verify openkeyscan-tagger Writes Are lexicon-tagger Compatible")
    print("=" * 60 + "\n")

    test_key = "4B"

    formats = [
        ('mp3', 'MP3'),
        ('flac', 'FLAC'),
        ('ogg', 'OGG'),
        ('mp4', 'MP4'),
        ('m4a', 'M4A')
    ]

    for ext, name in formats:
        temp_file = copy_test_file(test_files_dir, ext)
        if not temp_file:
            print(f"⚠️  SKIP: {name} (test file not found)")
            continue

        try:
            # Write using openkeyscan-tagger
            success, error, fmt = write_key_to_file(temp_file, test_key)
            if not success:
                results.add_fail(f"Write {name} for lexicon",
                               f"Write failed: {error}")
                continue

            # Verify lexicon-tagger can read it (by checking for initialkey field)
            can_read = verify_lexicon_can_read_format(temp_file, test_key)

            if can_read:
                results.add_pass(f"Write {name} for lexicon",
                               f"File has 'initialkey' field readable by lexicon-tagger")
            else:
                results.add_fail(f"Write {name} for lexicon",
                               "Missing 'initialkey' field for lexicon-tagger compatibility")

        finally:
            temp_file.unlink()


def test_bidirectional_compatibility(results, test_files_dir):
    """Test bidirectional compatibility: lexicon-tagger → openkeyscan-tagger → lexicon-tagger."""
    print("\n" + "=" * 60)
    print("Bidirectional Compatibility Tests")
    print("=" * 60 + "\n")

    test_key_1 = "6A"
    test_key_2 = "9B"

    formats = [
        ('flac', 'FLAC', simulate_lexicon_tagger_write_flac),
        ('ogg', 'OGG', simulate_lexicon_tagger_write_ogg),
        ('mp4', 'MP4', simulate_lexicon_tagger_write_mp4)
    ]

    for ext, name, lexicon_write_func in formats:
        temp_file = copy_test_file(test_files_dir, ext)
        if not temp_file:
            continue

        try:
            # Step 1: Write using lexicon-tagger format
            lexicon_write_func(temp_file, test_key_1)

            # Step 2: Read using openkeyscan-tagger
            success, read_key_1, fmt, error = read_key_from_file(temp_file)
            if not success or read_key_1 != test_key_1:
                results.add_fail(f"Bidirectional {name}",
                               f"Failed to read lexicon format: expected '{test_key_1}', got '{read_key_1}'")
                continue

            # Step 3: Write a different key using openkeyscan-tagger
            success, error, fmt = write_key_to_file(temp_file, test_key_2)
            if not success:
                results.add_fail(f"Bidirectional {name}",
                               f"Failed to write with openkeyscan: {error}")
                continue

            # Step 4: Verify lexicon-tagger can read the new value
            can_read = verify_lexicon_can_read_format(temp_file, test_key_2)

            if can_read:
                results.add_pass(f"Bidirectional {name}",
                               f"lexicon→openkeyscan→lexicon: '{test_key_1}' → '{test_key_2}' ✓")
            else:
                results.add_fail(f"Bidirectional {name}",
                               "lexicon-tagger cannot read file after openkeyscan write")

        finally:
            temp_file.unlink()


def main():
    """Run all compatibility tests."""
    print("═" * 60)
    print("  lexicon-tagger Cross-Compatibility Test Suite")
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
    test_read_lexicon_format_files(results, test_files_dir)
    test_write_compatible_with_lexicon(results, test_files_dir)
    test_bidirectional_compatibility(results, test_files_dir)

    # Print summary
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
