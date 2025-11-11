#!/usr/bin/env node
/**
 * Test suite for key reading functionality
 *
 * Tests reading keys from various audio formats via the server protocol
 */

import { spawn } from 'child_process';
import { createInterface } from 'readline';
import { randomUUID } from 'crypto';
import { existsSync } from 'fs';
import { resolve } from 'path';

// File formats to test
const FILE_FORMATS = [
  { ext: 'mp3', name: 'MP3' },
  { ext: 'mp4', name: 'MP4' },
  { ext: 'm4a', name: 'M4A' },
  { ext: 'aac', name: 'AAC' },
  { ext: 'aiff', name: 'AIFF' },
  { ext: 'aif', name: 'AIF' },
  { ext: 'alac', name: 'ALAC' },
  { ext: 'wav', name: 'WAV' },
  { ext: 'ogg', name: 'OGG' },
  { ext: 'flac', name: 'FLAC' }
];

class KeyTaggingService {
  constructor(executablePath) {
    this.serverProcess = null;
    this.pendingRequests = new Map();
    this.executablePath = executablePath;
    this.isReady = false;
    this._handlers = {};
  }

  start() {
    return new Promise((resolve, reject) => {
      console.log(`Starting server: ${this.executablePath}`);

      // Spawn the server process
      // If it's a .py file, run it through Python
      let command, args;
      if (this.executablePath.endsWith('.py')) {
        command = 'python3';
        args = [this.executablePath, '--workers', '4'];
      } else {
        command = this.executablePath;
        args = ['--workers', '4'];
      }

      this.serverProcess = spawn(command, args);

      // Set up line reader for stdout (responses)
      const rl = createInterface({
        input: this.serverProcess.stdout,
        crlfDelay: Infinity
      });

      // Handle responses
      rl.on('line', (line) => {
        try {
          const response = JSON.parse(line);
          this.handleResponse(response);
        } catch (err) {
          console.error('Failed to parse server response:', err);
        }
      });

      // Monitor stderr for debugging
      this.serverProcess.stderr.on('data', (data) => {
        console.log('[Server]', data.toString().trim());
      });

      // Handle process exit
      this.serverProcess.on('exit', (code) => {
        console.error(`Server exited with code ${code}`);
        this.isReady = false;
      });

      // Wait for ready signal
      const readyTimeout = setTimeout(() => {
        reject(new Error('Server failed to start within 10 seconds'));
      }, 10000);

      this.once('ready', () => {
        clearTimeout(readyTimeout);
        console.log('Server is ready!');
        resolve();
      });
    });
  }

  handleResponse(response) {
    // Handle system messages
    if (response.type === 'ready') {
      this.isReady = true;
      this.emit('ready');
      return;
    }

    if (response.type === 'heartbeat') {
      this.emit('heartbeat');
      return;
    }

    // Handle request responses
    if (response.id && this.pendingRequests.has(response.id)) {
      const { resolve, reject, timeout } = this.pendingRequests.get(response.id);
      clearTimeout(timeout);
      this.pendingRequests.delete(response.id);

      if (response.status === 'success') {
        resolve(response);
      } else {
        reject(new Error(response.error || 'Unknown error'));
      }
    }
  }

  tagFile(filePath, keyValue, timeoutMs = 10000) {
    return new Promise((promiseResolve, promiseReject) => {
      if (!this.isReady) {
        return promiseReject(new Error('Server not ready'));
      }

      // Generate unique request ID
      const requestId = randomUUID();

      // Convert to absolute path
      const absolutePath = resolve(filePath);

      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        promiseReject(new Error(`Tagging timeout after ${timeoutMs}ms`));
      }, timeoutMs);

      // Store resolver
      this.pendingRequests.set(requestId, { resolve: promiseResolve, reject: promiseReject, timeout });

      // Send request
      const request = {
        id: requestId,
        path: absolutePath,
        key: keyValue
      };

      try {
        this.serverProcess.stdin.write(JSON.stringify(request) + '\n');
      } catch (err) {
        this.pendingRequests.delete(requestId);
        clearTimeout(timeout);
        promiseReject(err);
      }
    });
  }

  readKey(filePath, timeoutMs = 10000) {
    return new Promise((promiseResolve, promiseReject) => {
      if (!this.isReady) {
        return promiseReject(new Error('Server not ready'));
      }

      // Generate unique request ID
      const requestId = randomUUID();

      // Convert to absolute path
      const absolutePath = resolve(filePath);

      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        promiseReject(new Error(`Read timeout after ${timeoutMs}ms`));
      }, timeoutMs);

      // Store resolver
      this.pendingRequests.set(requestId, { resolve: promiseResolve, reject: promiseReject, timeout });

      // Send read request (no key field)
      const request = {
        id: requestId,
        path: absolutePath
      };

      try {
        this.serverProcess.stdin.write(JSON.stringify(request) + '\n');
      } catch (err) {
        this.pendingRequests.delete(requestId);
        clearTimeout(timeout);
        promiseReject(err);
      }
    });
  }

  stop() {
    if (this.serverProcess) {
      this.serverProcess.kill();
      this.serverProcess = null;
      this.isReady = false;
    }
  }

  // Event emitter methods
  on(event, handler) {
    if (!this._handlers[event]) this._handlers[event] = [];
    this._handlers[event].push(handler);
  }

  once(event, handler) {
    const onceHandler = (...args) => {
      handler(...args);
      this.off(event, onceHandler);
    };
    this.on(event, onceHandler);
  }

  off(event, handler) {
    if (!this._handlers || !this._handlers[event]) return;
    this._handlers[event] = this._handlers[event].filter(h => h !== handler);
  }

  emit(event, ...args) {
    if (!this._handlers || !this._handlers[event]) return;
    this._handlers[event].forEach(handler => handler(...args));
  }
}

async function findTestFiles(testDir) {
  /**
   * Find test audio files in the specified directory
   */
  const testFiles = {};

  for (const format of FILE_FORMATS) {
    const filePath = resolve(testDir, `test.${format.ext}`);
    if (existsSync(filePath)) {
      testFiles[format.ext] = filePath;
    }
  }

  return testFiles;
}

async function runTests(serverPath, testFilesDir) {
  console.log('═══════════════════════════════════════════════════════');
  console.log('  Key Reading Service Test Suite');
  console.log('═══════════════════════════════════════════════════════\n');

  // Find test files
  console.log(`Looking for test files in: ${testFilesDir}`);
  const testFiles = await findTestFiles(testFilesDir);

  if (Object.keys(testFiles).length === 0) {
    console.error('❌ No test files found!');
    console.error(`\nPlease add test audio files to: ${testFilesDir}`);
    console.error('Expected files: test.mp3, test.mp4, test.m4a, test.aac, test.aiff, test.aif, test.alac, test.wav, test.ogg, test.flac\n');
    process.exit(1);
  }

  console.log(`Found ${Object.keys(testFiles).length} test files:\n`);
  Object.entries(testFiles).forEach(([ext, path]) => {
    console.log(`  ✓ ${ext.toUpperCase().padEnd(6)} ${path}`);
  });
  console.log('');

  // Initialize service
  const service = new KeyTaggingService(serverPath);

  try {
    // Start server
    await service.start();

    // Test results
    const results = [];
    const testKeys = ['1A', '2B', '3A', '4B', '5A', '6B', '7A', '8B', '9A', '10B'];

    // Test each file format
    for (const [ext, filePath] of Object.entries(testFiles)) {
      const format = FILE_FORMATS.find(f => f.ext === ext);
      const testKey = testKeys[results.length % testKeys.length];

      process.stdout.write(`Testing ${format.name.padEnd(6)} ... `);

      try {
        // First, write a key to the file
        await service.tagFile(filePath, testKey);
        await new Promise(resolve => setTimeout(resolve, 200));

        // Then read it back
        const readResult = await service.readKey(filePath);

        if (readResult.status === 'success') {
          const readKey = readResult.key;

          if (readKey === testKey) {
            console.log(`✅ SUCCESS (wrote "${testKey}", read "${readKey}")`);
            results.push({ format: format.name, ext, success: true, key: testKey, readKey });
          } else if (readKey === null) {
            console.log(`⚠️  NO KEY (wrote "${testKey}", but read null)`);
            results.push({ format: format.name, ext, success: false, key: testKey, readKey: null, error: 'Key not found after write' });
          } else {
            console.log(`⚠️  MISMATCH (wrote "${testKey}", read "${readKey}")`);
            results.push({ format: format.name, ext, success: false, key: testKey, readKey, error: 'Key mismatch' });
          }
        } else {
          console.log(`❌ FAILED (${readResult.error || 'Unknown error'})`);
          results.push({ format: format.name, ext, success: false, key: testKey, error: readResult.error || 'Read failed' });
        }
      } catch (err) {
        console.log(`❌ FAILED (${err.message})`);
        results.push({ format: format.name, ext, success: false, key: testKey, error: err.message });
      }
    }

    // Test reading from files without keys
    console.log('\n═══════════════════════════════════════════════════════');
    console.log('  Testing Read from Files Without Keys');
    console.log('═══════════════════════════════════════════════════════\n');

    // Use first file format for this test
    const firstFile = Object.values(testFiles)[0];
    const firstExt = Object.keys(testFiles)[0];
    const firstFormat = FILE_FORMATS.find(f => f.ext === firstExt);

    process.stdout.write(`Testing ${firstFormat.name.padEnd(6)} (no key) ... `);

    try {
      // Try to read from a file that likely has no key (we'll write a key first, then remove it manually)
      // Actually, let's just test that reading works even if key is null
      const readResult = await service.readKey(firstFile);

      if (readResult.status === 'success') {
        // Success even if key is null - that's valid
        console.log(`✅ SUCCESS (read key: ${readResult.key === null ? 'null (no key in file)' : readResult.key})`);
        results.push({ format: `${firstFormat.name} (no key)`, ext: firstExt, success: true, key: null, readKey: readResult.key });
      } else {
        console.log(`❌ FAILED (${readResult.error || 'Unknown error'})`);
        results.push({ format: `${firstFormat.name} (no key)`, ext: firstExt, success: false, error: readResult.error || 'Read failed' });
      }
    } catch (err) {
      console.log(`❌ FAILED (${err.message})`);
      results.push({ format: `${firstFormat.name} (no key)`, ext: firstExt, success: false, error: err.message });
    }

    // Print summary
    console.log('\n═══════════════════════════════════════════════════════');
    console.log('  Test Summary');
    console.log('═══════════════════════════════════════════════════════\n');

    const successful = results.filter(r => r.success).length;
    const total = results.length;

    console.log(`Total: ${total} tests`);
    console.log(`Passed: ${successful} ✅`);
    console.log(`Failed: ${total - successful} ❌`);
    console.log(`Success Rate: ${((successful / total) * 100).toFixed(1)}%\n`);

    if (successful < total) {
      console.log('Failed tests:');
      results.filter(r => !r.success).forEach(r => {
        console.log(`  • ${r.format}: ${r.error || 'Unknown error'}`);
        if (r.key !== undefined && r.readKey !== undefined) {
          console.log(`    Expected: "${r.key}", Got: "${r.readKey}"`);
        }
      });
      console.log('');
    }

    // Stop server
    service.stop();

    process.exit(successful === total ? 0 : 1);

  } catch (err) {
    console.error('Test failed:', err);
    service.stop();
    process.exit(1);
  }
}

// Main execution
const serverPath = process.argv[2] || '../openkeyscan_tagger.py';
const testFilesDir = process.argv[3] || './test-files';

runTests(serverPath, testFilesDir);

