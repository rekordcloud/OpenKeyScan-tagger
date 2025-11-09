# OpenKeyScan Tagger

A high-performance Python service for writing musical key metadata to audio files. Communicates via stdin/stdout JSON protocol for seamless integration with Electron applications.

## Features

- **Multiple Format Support**: MP3, MP4, M4A, AAC, AIFF, AIF, ALAC, WAV, OGG, FLAC
- **Flexible Key Formats**: Accepts Camelot notation (9A), OpenKey notation (2m), or plain text (E minor)
- **Dual-Field Compatibility**: Writes both standard and legacy field names for maximum compatibility
- **lexicon-tagger Compatible**: Full bidirectional compatibility with lexicon-tagger
- **Read & Write Operations**: Can both read and write key metadata
- **High Performance**: Multi-threaded concurrent processing
- **Simple Protocol**: Line-delimited JSON (NDJSON) over stdin/stdout
- **Standalone Executable**: Packaged with PyInstaller for easy distribution

## Documentation

- **[INTERFACING.md](INTERFACING.md)** - Complete Electron integration guide with code examples
- **[README.md](README.md)** - This file (quick start and reference)

## Quick Start

### Installation

1. Install Python dependencies:
```bash
pipenv install
pipenv install --dev  # For PyInstaller
```

2. Install test dependencies:
```bash
cd test
npm install
```

### Development Usage

Run the server directly with Python:
```bash
pipenv run python openkeyscan_tagger.py
```

Or with custom worker count:
```bash
pipenv run python openkeyscan_tagger.py --workers 8
```

### Building Executable

Build standalone executable with PyInstaller:
```bash
pipenv run pyinstaller openkeyscan_tagger.spec
```

This creates:
- `dist/openkeyscan-tagger/` - Executable folder
- `dist/openkeyscan-tagger.zip` - Compressed distribution

### Testing

Run the complete test suite:
```bash
cd test
npm test -- ../openkeyscan_tagger.py ./test-files
```

Or test the built executable:
```bash
npm test -- ../dist/openkeyscan-tagger/openkeyscan-tagger ./test-files
```

The test suite includes:
- **test-tagger.js**: Write operations and dual-field verification
- **test_read_function.py**: Read function comprehensive tests
- **test_lexicon_compatibility.py**: Cross-compatibility with lexicon-tagger

## Protocol Specification

### Communication Method
- **Input**: Send JSON requests to stdin (one per line)
- **Output**: Receive JSON responses from stdout (one per line)
- **Logging**: Debug info sent to stderr

### Message Types

#### 1. Request (Client → Server)
```json
{
  "id": "unique-uuid-1234",
  "path": "/absolute/path/to/song.mp3",
  "key": "9A"
}
```

**Fields:**
- `id` (string, required): Unique identifier to match responses
- `path` (string, required): Absolute file path (no `~` expansion)
- `key` (string, required): Key value to write (any format)

#### 2. Success Response (Server → Client)
```json
{
  "id": "unique-uuid-1234",
  "status": "success",
  "key": "9A",
  "filename": "song.mp3",
  "format": "mp3"
}
```

#### 3. Error Response (Server → Client)
```json
{
  "id": "unique-uuid-1234",
  "status": "error",
  "error": "File not found",
  "filename": "song.mp3"
}
```

#### 4. System Messages (Server → Client)
```json
{"type": "ready"}      // Sent once on startup
{"type": "heartbeat"}  // Sent every 30 seconds
```

## Tag Format Implementation

The service writes keys to the appropriate metadata field(s) for each format:

| Format | Tag Type | Fields Written | Read Priority |
|--------|----------|----------------|---------------|
| MP3 | ID3v2.4 | `TKEY` frame | `TKEY` |
| MP4/M4A | iTunes freeform | `initialkey` + `KEY` | `initialkey` > `KEY` |
| AAC | ID3v2.4 | `TKEY` frame | `TKEY` |
| FLAC | Vorbis Comments | `initialkey` + `KEY` | `initialkey` > `KEY` |
| OGG | Vorbis Comments | `initialkey` + `KEY` | `initialkey` > `KEY` |
| AIFF/AIF | ID3 | `TKEY` frame | `TKEY` |
| ALAC | iTunes freeform | `initialkey` + `KEY` | `initialkey` > `KEY` |
| WAV | ID3 | `TKEY` frame | `TKEY` |

### Compatibility Features

**Dual-Field Write**: For FLAC, OGG, MP4, M4A, and ALAC formats, the service writes to **both** the standard field name (`initialkey`) and the legacy field name (`KEY`). This ensures:
- ✅ Full compatibility with lexicon-tagger (reads `initialkey`)
- ✅ Backward compatibility with files using `KEY` field
- ✅ Follows Vorbis Comment and iTunes freeform tag standards

**Read Function**: The `read_key_from_file()` function can read existing keys from audio files:
- Checks `initialkey` field first (standard)
- Falls back to `KEY` field (legacy)
- **Case-insensitive** field matching (works with `initialkey`, `INITIALKEY`, `InitialKey`, etc.)
- Works with files from any DJ tool

## Electron Integration

For complete integration instructions with full code examples, see **[INTERFACING.md](INTERFACING.md)**.

### Quick Example

```javascript
const tagService = new KeyTaggingService('./dist/openkeyscan-tagger/openkeyscan-tagger');
await tagService.start();

// Tag a single file
const result = await tagService.tagFile('/path/to/song.mp3', '9A');
console.log(`Tagged ${result.filename} with key ${result.key}`);

// Tag multiple files concurrently
const results = await tagService.tagMultiple([
  { path: '/path/to/song1.mp3', key: '9A' },
  { path: '/path/to/song2.flac', key: 'E minor' },
  { path: '/path/to/song3.m4a', key: '2m' }
]);

tagService.stop();
```

**See [INTERFACING.md](INTERFACING.md) for:**
- Complete `KeyTaggingService` class implementation
- Error handling and timeout management
- IPC integration examples
- Auto-restart logic
- Integration with key detection
- Performance tuning

## Command Line Arguments

```bash
openkeyscan-tagger [OPTIONS]

Options:
  -w, --workers N    Number of worker threads (default: 4)
  -h, --help        Show help message
```

## Performance

- **Throughput**: ~200-500 files/minute (depends on file size and disk speed)
- **Concurrency**: Configurable worker threads (default: 4)
- **Memory**: ~50-100MB baseline
- **Startup**: Instant (no model loading required)

## Testing

The test suite verifies that:
1. Keys can be written to all supported formats
2. Written keys can be read back correctly with dual-field support
3. Read function works with both `initialkey` and `KEY` fields
4. Field priority is correct (initialkey preferred over KEY)
5. Cross-compatibility with lexicon-tagger format
6. Round-trip integrity (write → read → verify)
7. Various key formats (Camelot, OpenKey, plain text)

### Test Files

Place test audio files in `test/test-files/`:
```
test-files/
├── test.mp3
├── test.mp4
├── test.m4a
├── test.aac
├── test.aiff
├── test.aif
├── test.alac
├── test.wav
├── test.ogg
└── test.flac
```

## Troubleshooting

### Server doesn't start
- Check executable path exists
- Check executable permissions: `chmod +x openkeyscan-tagger`
- Monitor stderr for error messages

### "File not found" errors
- Verify absolute paths (not relative or `~`)
- Check file actually exists and is readable

### Keys not written correctly
- Check file format is supported
- Verify file is not read-only
- Check file system permissions

### Timeout errors
- Increase timeout for large files
- Check server process is still running
- Reduce worker count if memory constrained

## License

MIT

## Architecture

This project follows the same architecture as the MusicalKeyCNN key detection server:
- Long-running Python process
- stdin/stdout JSON protocol
- Multi-threaded processing
- PyInstaller packaging
- Symlink dereferencing for distribution
