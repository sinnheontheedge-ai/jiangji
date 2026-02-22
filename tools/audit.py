import os
import subprocess

print("AUDIT START")

files = []
for root, dirs, fs in os.walk("."):
    for f in fs:
        if f.endswith(".py"):
            files.append(os.path.join(root, f))

print("PY FILES:", len(files))

if len(files) < 3:
    print("PROJECT TOO SMALL -> REQUEST FIX")
    exit(1)

print("AUDIT PASS")
