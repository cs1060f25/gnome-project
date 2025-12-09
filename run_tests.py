#!/usr/bin/env python3
"""
Gnome Test Suite Runner

Run all tests with:
    python run_tests.py

For full test suite (including Flask API tests), activate venv first:
    source venv/bin/activate
    pip install -r requirements.txt
    python run_tests.py

This script runs all unit tests and integration tests for the Gnome application.
"""
import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_all_tests():
    """Discover and run all tests in the tests directory."""
    print("=" * 70)
    print("GNOME TEST SUITE")
    print("=" * 70)
    print()
    
    # Discover all tests in the tests directory
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print()
        print("✅ ALL TESTS PASSED")
    else:
        print()
        print("❌ SOME TESTS FAILED")
        
        if result.failures:
            print()
            print("Failed Tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print()
            print("Error Tests:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    print("=" * 70)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_all_tests())

