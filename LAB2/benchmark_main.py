from benchmark.run_benchmark import run_benchmark

def benchmark_main():
    
    host = "localhost"
    port = 8080
    num_requests = 10

    stats = run_benchmark(host, port, num_requests)
    
    print(f"ANALYSIS")
    
    print(stats)

if __name__ == "__main__":
    benchmark_main()