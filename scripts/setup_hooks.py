#!/usr/bin/env python3
"""
Pre-pushフックのセットアップスクリプト
"""

import subprocess
import sys


def setup_pre_push():
    """Pre-pushフックをセットアップ"""
    try:
        # pre-pushフックをインストール
        print("Installing pre-push hooks...")
        subprocess.run(["uv", "run", "pre-commit", "install", "--hook-type", "pre-push"], check=True)
        print("✅ Pre-push hooks installed successfully!")

        # 初回実行でフックをテスト
        print("Running pre-push hooks on all files...")
        result = subprocess.run(["uv", "run", "pre-commit", "run", "--all-files", "--hook-stage", "pre-push"],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ All pre-push checks passed!")
        else:
            print("⚠️  Some pre-push checks failed, but hooks are installed.")
            print("Output:", result.stdout)
            print("Errors:", result.stderr)

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up pre-push hooks: {e}")
        return False
    except FileNotFoundError:
        print("❌ uv or pre-commit not found. Please install uv first.")
        return False


if __name__ == "__main__":
    success = setup_pre_push()
    sys.exit(0 if success else 1)
