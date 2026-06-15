#!/usr/bin/env python3
import json
import sys

print(json.dumps({"scanned": 1, "indexed": 0, "duplicates": 0, "errors": 1, "details": []}, ensure_ascii=False))
sys.exit(1)
