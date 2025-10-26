#!/usr/bin/env python3
"""
Pre-commitフックのセットアップスクリプト
"""

import subprocess
import sys


def setup_pre_commit():
    """Pre-commitフックをセットアップ"""
    try:
        # pre-commitをインストール
        print("Installing pre-commit hooks...")
        subprocess.run(["uv", "run", "pre-commit", "install"], check=True)
        print("✅ Pre-commit hooks installed successfully!")

        # 初回実行でフックをテスト
        print("Running pre-commit on all files...")
        result = subprocess.run(["uv", "run", "pre-commit", "run", "--all-files"],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ All pre-commit checks passed!")
        else:
            print("⚠️  Some pre-commit checks failed, but hooks are installed.")
            print("Output:", result.stdout)
            print("Errors:", result.stderr)

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up pre-commit: {e}")
        return False
    except FileNotFoundError:
        print("❌ uv or pre-commit not found. Please install uv first.")
        return False


if __name__ == "__main__":
    success = setup_pre_commit()
    sys.exit(0 if success else 1)
