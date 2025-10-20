
import time

from make_request import make_request
def run_well_behaved_main(host, port, num_requests=10, delay_per_request=1.0):
    print(f"WELL-BEHAVED CLIENT TEST")
    print(f"Target: {host}:{port}")
    
    overall_start = time.time()
    results = []
    
    for i in range(num_requests):
        print(f"Request {i+1}/{num_requests}... ")
        
        result = make_request(i+1, host, port, '/')
        if isinstance(result, tuple) and len(result) >= 2:
            _, status = result[0], result[1]
        else:
            status = result

        results.append(status)

        if status == 200:
            print(f"Success")
        elif status == 429:
            print(f"Rate limited")
        else:
            print(f"Failed ({status})")
        
        if i < num_requests - 1:
            time.sleep(delay_per_request)
    
    overall_duration = time.time() - overall_start
    
    success = sum(1 for r in results if r == 200)
    rate_limited = sum(1 for r in results if r == 429)
    failed = sum(1 for r in results if r not in [200, 429])
    
    print(f"RESULTS")
    print(f"Total requests: {num_requests}")
    print(f"Successful (200): {success}")
    print(f"Rate limited (429): {rate_limited}")
    print(f"Failed: {failed}")
    print(f"Total time: {overall_duration:.3f} seconds")
    
    if success > 0:
        throughput = success / overall_duration
        print(f"Throughput: {throughput:.1f} successful requests/second")
    
    return {
        'successful': success,
        'rate_limited': rate_limited,
        'failed': failed,
        'total_time': overall_duration,
    }

if __name__ == "__main__":
    run_well_behaved_main('localhost', 8080, num_requests=10, delay_per_request=1.0)