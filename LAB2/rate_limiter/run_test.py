import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))
import sys

import subprocess


def run_test(test_name, script_name, args):
    print(f"Running: {test_name}")

    project_root = os.path.abspath(os.path.join(__file__, '..', '..'))
    script_path = script_name
    if not os.path.isabs(script_path):
        candidate = os.path.join(project_root, script_name)
        if os.path.exists(candidate):
            script_path = candidate
        else:
            script_path = os.path.abspath(script_name)

    if not os.path.exists(script_path):
        print(f"Error: script not found: {script_name} (tried {script_path})")
        return

    cmd = [sys.executable, script_path] + args
    subprocess.run(cmd)