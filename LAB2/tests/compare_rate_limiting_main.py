import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))
from rate_limiter.run_test import run_test
import time

def compare_rate_limiting_main():
    host = "localhost"
    port = "8080"
    
    run_test(
        "SPAMMER (50 fast requests)",
        "rate_limiter/spammer_main.py",
        [host, port, "50"]
    )
    
    time.sleep(2)
    
    run_test(
        "WELL-BEHAVED (10 slow requests)",
        "rate_limiter/well_behaved_main.py",
        [host, port]
    )

if __name__ == '__main__':
    compare_rate_limiting_main()