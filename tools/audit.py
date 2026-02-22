print("AUDIT START")

import os

if not os.path.exists("engine_main.py"):
    print("ERROR: engine_main.py missing")
    exit(1)

print("AUDIT PASS")