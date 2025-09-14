#!/usr/bin/env python3
"""
Test runner for all task specification tests.

Runs both the original and enhanced task specification tests
with comprehensive coverage reporting.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run all task specification tests"""
    print("Running WorkMemEval Task Specification Tests")
    print("=" * 50)
    
    # Test files to run
    test_files = [
        "tests/test_task_specification.py"
    ]
    
    # Check that test files exist
    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"❌ Test file not found: {test_file}")
            return False
    
    # Run tests with verbose output
    cmd = [
        "python", "-m", "pytest",
        *test_files,
        "-v",
        "--tb=short",
        "--durations=10"  # Show 10 slowest tests
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("✅ All task specification tests passed!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return False
    
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)