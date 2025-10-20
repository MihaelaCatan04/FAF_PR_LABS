import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))
from counters.naive_counter import RequestCounterNaive
from concurrent.futures import ThreadPoolExecutor

def test_naive_counter():
    print(f"NAIVE COUNTER")    
    counter = RequestCounterNaive('counts_demo_naive.json')
    counter.reset()
    
    def increment_100_times():
        for _ in range(100):
            counter.increment('/test.txt')
    
    print(f"Starting 5 threads...")
    print(f"Each thread will increment 100 times...")
    print(f"Expected final count: 5 × 100 = 500")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(increment_100_times) for _ in range(5)]
        for f in futures:
            f.result()
    
    actual_count = counter.get_count('/test.txt')
    lost = 500 - actual_count
    
    print(f"Results:")
    print(f"Expected: 500")
    print(f"Actual: {actual_count}")
    print(f"Lost increments: {lost} ({lost/500*100:.1f}% loss)")
    
    if lost > 0:
        print(f"RACE CONDITION DETECTED!")
    else:
        print(f"No race condition (got lucky, or too few iterations)")

