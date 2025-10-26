#!/usr/bin/env python3
"""
テスト実行スクリプト
"""

import sys
import pytest


def run_all_tests():
    """全てのテストを実行"""
    return pytest.main([
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ])


def run_api_tests():
    """APIテストのみを実行"""
    return pytest.main([
        "tests/test_api.py",
        "-v",
        "--tb=short",
        "--color=yes"
    ])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        sys.exit(run_api_tests())
    else:
        sys.exit(run_all_tests())
