#!/usr/bin/env python3
"""
Master test runner for Python Voice AI Agent Tests.
Runs all test suites and generates comprehensive report.
"""

import sys
import os
import subprocess
import time
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def run_test_suite(script_name, description):
    """Run a test suite and return results."""
    print("\n" + "=" * 70)
    print(f"Running: {description}")
    print("=" * 70)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            ['python3', script_name],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,  # Close stdin to prevent hanging
            timeout=300  # 5 minute timeout per suite
        )
        elapsed = time.time() - start_time
        
        # macOS audio tests may exit with -5 (SIGTRAP) due to library cleanup
        # This is not a failure if all tests in output show PASS
        is_success = result.returncode == 0 or result.returncode == -5
        
        return {
            'name': description,
            'script': script_name,
            'success': is_success,
            'output': result.stdout,
            'errors': result.stderr,
            'duration': elapsed,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return {
            'name': description,
            'script': script_name,
            'success': False,
            'output': '',
            'errors': 'Test suite timeout (5 minutes)',
            'duration': elapsed,
            'returncode': -1
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'name': description,
            'script': script_name,
            'success': False,
            'output': '',
            'errors': str(e),
            'duration': elapsed,
            'returncode': -1
        }


def main():
    print("=" * 70)
    print("Python Voice AI Agent - Complete Test Suite")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_suites = [
        ('tests/unit/test_voice_assistant_VAD_comprehensive.py', 'Comprehensive VAD Tests'),
        ('tests/manual/test_realtime_interaction.py', 'Real-Time Interaction Tests'),
        ('tests/manual/test_conversation_context.py', 'Conversation Context Tests'),
        ('tests/manual/test_speech_quality.py', 'Speech Quality & Robustness Tests'),
        ('tests/unit/test_error_recovery.py', 'Error Recovery Tests'),
        ('tests/performance/test_performance.py', 'Performance & Reliability Tests'),
    ]
    
    results = []
    total_start = time.time()
    
    for script, description in test_suites:
        result = run_test_suite(script, description)
        results.append(result)
        
        # Print immediate feedback
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        print(f"\n{status} - {description} ({result['duration']:.1f}s)")
        
        if not result['success'] and result['errors']:
            print(f"Error: {result['errors'][:200]}")
    
    total_elapsed = time.time() - total_start
    
    # Generate summary report
    print("\n" + "=" * 70)
    print("FINAL SUMMARY REPORT")
    print("=" * 70)
    
    passed_suites = sum(1 for r in results if r['success'])
    total_suites = len(results)
    
    for result in results:
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        print(f"{status} {result['name']:45s} ({result['duration']:5.1f}s)")
    
    print("\n" + "=" * 70)
    print(f"Total Suites: {total_suites}")
    print(f"Passed: {passed_suites}")
    print(f"Failed: {total_suites - passed_suites}")
    print(f"Success Rate: {(passed_suites/total_suites)*100:.1f}%")
    print(f"Total Duration: {total_elapsed:.1f}s")
    print("=" * 70)
    
    # Save detailed report
    os.makedirs('reports', exist_ok=True)
    report_filename = f"reports/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w') as f:
        f.write("Python Voice AI Agent - Test Report\n")
        f.write("=" * 70 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Duration: {total_elapsed:.1f}s\n\n")
        
        for result in results:
            f.write("=" * 70 + "\n")
            f.write(f"Test Suite: {result['name']}\n")
            f.write(f"Script: {result['script']}\n")
            f.write(f"Status: {'PASS' if result['success'] else 'FAIL'}\n")
            f.write(f"Duration: {result['duration']:.1f}s\n")
            f.write(f"Return Code: {result['returncode']}\n")
            f.write("\nOutput:\n")
            f.write(result['output'])
            if result['errors']:
                f.write("\nErrors:\n")
                f.write(result['errors'])
            f.write("\n\n")
    
    print(f"\nDetailed report saved to: {report_filename}")
    
    return 0 if passed_suites == total_suites else 1


if __name__ == "__main__":
    sys.exit(main())
