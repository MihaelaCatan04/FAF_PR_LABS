import time
from concurrent.futures import ThreadPoolExecutor
from make_request import make_request

def run_benchmark(host, port, num_requests=10):

    print(f"BENCHMARK TEST")
    print(f"Target: {host}:{port}")
    print(f"Making {num_requests} CONCURRENT requests...")
    
    overall_start = time.time()
    
    results = []
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [
            executor.submit(make_request, i+1, host, port, '/')
            for i in range(num_requests)
        ]
        
        results = [f.result() for f in futures]
    
    overall_end = time.time()
    overall_duration = overall_end - overall_start
    
    successful = [r for r in results if r[2]]
    failed = len(results) - len(successful)
    individual_times = [r[1] for r in successful]
    
    if successful:
        avg_time = sum(individual_times) / len(successful)
        min_time = min(individual_times)
        max_time = max(individual_times)
    else:
        avg_time = min_time = max_time = 0
    
    print(f"RESULTS")
    print(f"Total time for {num_requests} requests: {overall_duration:.3f} seconds")
    print(f"Successful: {len(successful)}/{num_requests}")
    print(f"Failed: {failed}")
    print(f"Min response time: {min_time:.3f}s")
    print(f"Max response time: {max_time:.3f}s")
    print(f"Average response time: {avg_time:.3f}s")
    
    return {
        'total_time': overall_duration,
        'num_requests': num_requests,
        'successful': len(successful),
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
    }