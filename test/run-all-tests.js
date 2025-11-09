#!/usr/bin/env node
/**
 * Comprehensive Test Runner
 *
 * Runs all test suites:
 * 1. test-tagger.js - Write operations and dual-field verification
 * 2. test_read_function.py - Read function comprehensive tests
 * 3. test_lexicon_compatibility.py - Cross-compatibility tests
 */

import { spawn } from 'child_process';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Parse command line arguments
const serverPath = process.argv[2] || '../openkeyscan_tagger.py';
const testFilesDir = process.argv[3] || './test-files';

console.log('═══════════════════════════════════════════════════════');
console.log('  OpenKeyScan Tagger - Complete Test Suite');
console.log('═══════════════════════════════════════════════════════');
console.log(`Server: ${serverPath}`);
console.log(`Test files: ${testFilesDir}`);
console.log('═══════════════════════════════════════════════════════\n');

let allTestsPassed = true;
const testResults = [];

/**
 * Run a test command and capture results
 */
function runTest(command, args, testName) {
  return new Promise((resolve) => {
    console.log(`\n${'─'.repeat(60)}`);
    console.log(`Starting: ${testName}`);
    console.log(`${'─'.repeat(60)}\n`);

    const startTime = Date.now();
    const child = spawn(command, args, {
      stdio: 'inherit',
      shell: true
    });

    child.on('close', (code) => {
      const duration = Date.now() - startTime;
      const passed = code === 0;

      testResults.push({
        name: testName,
        passed,
        duration,
        code
      });

      if (!passed) {
        allTestsPassed = false;
      }

      resolve(passed);
    });

    child.on('error', (err) => {
      console.error(`\n❌ Failed to start test: ${err.message}\n`);
      testResults.push({
        name: testName,
        passed: false,
        duration: 0,
        error: err.message
      });
      allTestsPassed = false;
      resolve(false);
    });
  });
}

/**
 * Print summary of all test results
 */
function printSummary() {
  console.log('\n' + '═'.repeat(60));
  console.log('  Complete Test Suite Summary');
  console.log('═'.repeat(60) + '\n');

  testResults.forEach((result, index) => {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    const duration = (result.duration / 1000).toFixed(2);
    console.log(`${index + 1}. ${status} - ${result.name} (${duration}s)`);
    if (result.error) {
      console.log(`   Error: ${result.error}`);
    }
  });

  const passedCount = testResults.filter(r => r.passed).length;
  const totalCount = testResults.length;
  const totalDuration = testResults.reduce((sum, r) => sum + r.duration, 0);

  console.log('\n' + '─'.repeat(60));
  console.log(`Results: ${passedCount}/${totalCount} test suites passed`);
  console.log(`Total time: ${(totalDuration / 1000).toFixed(2)}s`);
  console.log('─'.repeat(60) + '\n');

  if (allTestsPassed) {
    console.log('🎉 All tests passed! 🎉\n');
  } else {
    console.log('❌ Some tests failed. Please review the output above.\n');
  }
}

/**
 * Main test execution
 */
async function runAllTests() {
  try {
    // Test 1: JavaScript write operations and dual-field verification
    await runTest(
      'node',
      [resolve(__dirname, 'test-tagger.js'), serverPath, testFilesDir],
      'Write Operations & Dual-Field Verification (JS)'
    );

    // Test 2: Python read function comprehensive tests
    await runTest(
      'python3',
      [resolve(__dirname, 'test_read_function.py'), testFilesDir],
      'Read Function Comprehensive Tests (Python)'
    );

    // Test 3: Python lexicon-tagger compatibility tests
    await runTest(
      'python3',
      [resolve(__dirname, 'test_lexicon_compatibility.py'), testFilesDir],
      'lexicon-tagger Cross-Compatibility Tests (Python)'
    );

    // Print summary
    printSummary();

    // Exit with appropriate code
    process.exit(allTestsPassed ? 0 : 1);

  } catch (err) {
    console.error('\n❌ Test runner error:', err);
    process.exit(1);
  }
}

// Run all tests
runAllTests();
