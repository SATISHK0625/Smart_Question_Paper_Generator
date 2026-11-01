import sys
import os
import pytest

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

def main():
    print("Running pytest on backend/tests...")
    code = pytest.main([
        "-v",
        "backend/tests/test_template_preservation.py",
        "backend/tests/test_visual_regression.py",
        "backend/tests/test_parser.py",
        "backend/tests/test_analyzer.py"
    ])
    print(f"Pytest exit code: {code}")
    sys.exit(code)

if __name__ == "__main__":
    main()
