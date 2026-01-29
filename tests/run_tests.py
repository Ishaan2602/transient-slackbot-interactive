#!/usr/bin/env python3
"""
Simple test runner for obscos project
"""
import os
import sys

def run_test(test_name):
    print(f"\n{'='*50}")
    print(f"Running {test_name}")
    print('='*50)
    
    try:
        result = os.system(f"python {test_name}.py")
        if result == 0:
            print(f"{test_name} PASSED")
            return True
        else:
            print(f"{test_name} FAILED")
            return False
    except Exception as e:
        print(f"{test_name} ERROR: {e}")
        return False

def main():
    print("OBSCOS Project Test Runner")
    print("="*50)
    
    tests = [
        "test_askap_setup",
        "test_voting_system"
    ]
    
    results = {}
    for test in tests:
        results[test] = run_test(test)
    
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test:<20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())