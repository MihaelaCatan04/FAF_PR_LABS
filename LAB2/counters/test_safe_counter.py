import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))
from counters.safe_counter import RequestCounterSafe
from concurrent.futures import ThreadPoolExecutor
def test_safe_counter():
    print(f"SAFE COUNTER (WITH LOCK)")
    
    counter = RequestCounterSafe('counts_demo_safe.json')
    counter.reset()
    
    def increment_100_times():
        for _ in range(100):
            counter.increment('/test.txt')
    
    print(f"Starting 5 threads...")
    print(f"Each thread will increment 100 times...")
    print(f"Expected final count: 5 × 100 = 500\n")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(increment_100_times) for _ in range(5)]
        for f in futures:
            f.result()
    
    actual_count = counter.get_count('/test.txt')
    lost = 500 - actual_count
    
    print(f"Results:")
    print(f"Expected: 500")
    print(f"Actual: {actual_count}")
    print(f"Lost increments: {lost}")
    
    if actual_count == 500:
        print(f"No data loss!")
    else:
        print(f"Unexpected: Lost {lost} increments")