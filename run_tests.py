#!/usr/bin/env python3
"""
Test runner for InstantMBTA project.
Run this script from the project root to execute all tests.
"""

import unittest
import sys
import os

# Add the python directory to the path so tests can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def run_tests():
    """Discover and run all tests in the tests directory."""
    # Set testing environment variable for configuration
    os.environ['TESTING'] = 'true'
    
    # Discover tests in the tests directory
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code) 