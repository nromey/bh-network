#!/usr/bin/env python3
"""Display a redacted summary of OPENAI_API_KEY for verification."""
import os

def main() -> int:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY is not set.")
        return 0

    preview = f"{key[:4]}…{key[-4:]}" if len(key) >= 8 else key
    print(f"OPENAI_API_KEY length: {len(key)}")
    print(f"OPENAI_API_KEY preview: {preview}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
