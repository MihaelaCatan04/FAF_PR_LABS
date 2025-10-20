
import sys

import subprocess
def run_test(test_name, script_name, args):
    print(f"Running: {test_name}")
    
    cmd = [sys.executable, script_name] + args
    subprocess.run(cmd)