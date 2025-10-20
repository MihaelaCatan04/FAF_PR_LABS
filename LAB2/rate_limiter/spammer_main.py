
import time
from make_request import make_request

from concurrent.futures import ThreadPoolExecutor
def spammer_main(host, port, num_requests=50):
    print(f"SPAMMER TEST")
    print(f"Target: {host}:{port}")
    
    overall_start = time.time()
    
    results = []
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [
            executor.submit(make_request, i+1, host, port, '/')
            for i in range(num_requests)
        ]
        results = [f.result() for f in futures]
    
    overall_duration = time.time() - overall_start
    
    success_200 = sum(1 for r in results if r[1] == 200)
    rate_limited_429 = sum(1 for r in results if r[1] == 429)
    failed = sum(1 for r in results if r[1] not in [200, 429])
    
    print(f"RESULTS")
    print(f"Total requests: {num_requests}")
    print(f"Successful (200): {success_200}")
    print(f"Rate limited (429): {rate_limited_429}")
    print(f"Failed: {failed}")
    print(f"Total time: {overall_duration:.3f} seconds")
    
    if success_200 > 0:
        throughput = success_200 / overall_duration
        print(f"Throughput: {throughput:.1f} successful requests/second")
        
    return {
        'successful': success_200,
        'rate_limited': rate_limited_429,
        'failed': failed,
        'total_time': overall_duration,
    }

if __name__ == "__main__":
    spammer_main('localhost', 8080, num_requests=50)
