# Lab 2: Concurrent HTTP Server

**Course:** Network Programming  
**Student:** Mihaela Catan  
**Group:** FAF-231

---

## Introduction

This lab extends the HTTP file server from Lab 1 by adding multithreading capabilities and concurrent request handling features. The enhanced server includes:

- **Multithreading**: Handle multiple client connections concurrently using a thread pool
- **Request Counter**: Track the number of requests made to each file/directory
- **Race Condition Demonstration**: Implement both naive (unsafe) and safe (thread-synchronized) counters
- **Rate Limiting**: Implement IP-based rate limiting (5 requests/second) with thread-safe mechanisms
- **Benchmarking Tools**: Scripts to measure and compare single-threaded vs multithreaded performance

This report documents the implementation of these features, the testing methodology, and the results demonstrating the benefits of multithreading and proper synchronization.

---

## Architecture Overview

### Key Components

**Server Architecture** (`start_server.py`):
- Uses `ThreadPoolExecutor` with configurable worker threads (default: 10)
- Each client connection is handled in a separate thread
- Accepts connections on main thread and submits work to thread pool

**Request Handling** (`handle_client.py`, `handle_request.py`):
- Per-request processing includes rate limiting checks
- Request counting for file access statistics
- Optional artificial delay for benchmarking (simulates processing time)

**Counters** (`counters/`):
- `RequestCounterNaive`: Demonstrates race conditions with no synchronization
- `RequestCounterSafe`: Thread-safe implementation using `threading.RLock()`
- Both persist counts to JSON files

**Rate Limiter** (`rate_limiter/rate_limiter.py`):
- Tracks request timestamps per IP address
- Sliding window algorithm (1-second window)
- Thread-safe using `threading.Lock()`
- Returns HTTP 429 (Too Many Requests) when limit exceeded

**Benchmarking** (`benchmark/`, `tests/`):
- Concurrent request testing
- Performance comparison tools
- Rate limiting validation scripts

---

## Multithreading Implementation

### Thread Pool Executor

The server uses Python's `concurrent.futures.ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=num_threads) as executor:
    while True:
        client_socket, client_address = server_socket.accept()
        executor.submit(
            handle_client,
            client_socket,
            client_address,
            directory,
            delay_requests,
            delay_time
        )
```

**Benefits**:
- Reuses threads instead of creating new ones for each request
- Limits concurrent threads to prevent resource exhaustion
- Automatic cleanup and graceful shutdown

### Request Handler

Each thread executes `handle_client()`:
- Reads request data from socket
- Processes request through `handle_request()`
- Applies rate limiting
- Updates request counters
- Sends response back to client

---

## Benchmarking: Single-threaded vs Multithreaded

### Test Setup

**Test Parameters**:
- 10 concurrent requests
- Artificial 1-second delay per request (simulates I/O or processing)
- Request target: `/` (root directory)

**Implementation** (`benchmark/run_benchmark.py`):
```python
with ThreadPoolExecutor(max_workers=num_requests) as executor:
    futures = [
        executor.submit(make_request, i+1, host, port, '/')
        for i in range(num_requests)
    ]
    results = [f.result() for f in futures]
```

### Expected Results

**Single-threaded (LAB1)**:
- Handles one request at a time
- With 10 requests × 1s delay = ~10 seconds total
- Sequential processing
<img width="584" height="299" alt="image" src="https://github.com/user-attachments/assets/8df2fbd9-f577-494c-9492-fa0718a1251e" />

**Multithreaded (LAB2)**:
- Handles 10 requests concurrently
- With 10 threads processing simultaneously = ~1 second total
- Parallel processing
<img width="587" height="302" alt="image" src="https://github.com/user-attachments/assets/21eb663b-0256-46b5-963c-32a59ae6684e" />


### Running the Benchmark

```bash
# Start the multithreaded server
python main.py ./my_website 8080

# In another terminal, run the benchmark
cd tests
python benchmark_main.py
```



### Performance Analysis

The multithreaded server demonstrates **~10x speedup** for concurrent requests compared to sequential handling. This improvement scales with the number of concurrent requests up to the thread pool limit.

---

## Request Counter Feature

### Purpose

Track how many times each file or directory has been requested and display this information in directory listings.

### Implementation

#### Naive Counter (Race Condition Demonstration)

**File**: `counters/naive_counter.py`

**Key Issue**: No synchronization between threads

```python
def increment(self, file_path):
    # Step 1: READ current value
    if file_path not in self.counts:
        self.counts[file_path] = 0
    current = self.counts[file_path]
    
    # Step 2: CALCULATE new value
    time.sleep(0.0001)  # Artificial delay forces race condition
    
    # Step 3: WRITE new value
    self.counts[file_path] = current + 1
    self._save_counts()
```

**Race Condition Scenario**:
1. Thread A reads count = 10
2. Thread B reads count = 10 (before A writes)
3. Thread A writes count = 11
4. Thread B writes count = 11 (overwrites A's update!)
5. Result: Two increments but count only increased by 1

**Demonstration** (`counters/test_naive_counter.py`):
- 5 threads each increment 100 times
- Expected final count: 500
- Actual result: **Significantly less than 500** due to lost updates

```bash
cd tests
python counter_main.py
```
<img width="234" height="119" alt="image" src="https://github.com/user-attachments/assets/84a95387-f5cb-4316-83da-1a30b73ef720" />

#### Safe Counter (Synchronized)

**File**: `counters/safe_counter.py`

**Solution**: Use `threading.RLock()` to synchronize access

```python
def increment(self, file_path):
    with self.lock:  # Acquire lock - only one thread enters
        if file_path not in self.counts:
            self.counts[file_path] = 0
        current = self.counts[file_path]
        
        time.sleep(0.0001)  # Same delay, but thread-safe!
        
        self.counts[file_path] = current + 1
        self._save_counts()
    # Lock released - next thread can enter
```

**Key Points**:
- `with self.lock:` ensures mutual exclusion
- Only one thread can execute the critical section at a time
- Other threads wait until lock is released
- No lost updates!

**Demonstration** (`counters/test_safe_counter.py`):

<img width="236" height="132" alt="image" src="https://github.com/user-attachments/assets/006caf05-4f38-41b5-879f-9dcb1500c79b" />


### Display in Directory Listing

The request counts are displayed next to each file and directory in the listing:

```html
<li class="file">
    <span class="name"><a href="/index.html">index.html</a></span>
    <span class="count">42 requests</span>
</li>
```

<img width="348" height="280" alt="image" src="https://github.com/user-attachments/assets/2b1df1cf-a8bc-402a-a772-5482e5035ded" />

---

## Rate Limiting Implementation

### Purpose

Prevent abuse by limiting each IP address to 5 requests per second using a thread-safe sliding window algorithm.

### Implementation

**File**: `rate_limiter/rate_limiter.py`

**Algorithm**:
```python
class RateLimiter:
    def __init__(self, max_requests_per_second=5):
        self.max_requests = max_requests_per_second
        self.request_times = defaultdict(list)  # IP -> [timestamps]
        self.lock = threading.Lock()
    
    def is_allowed(self, client_ip):
        with self.lock:
            now = time.time()
            
            # Remove timestamps older than 1 second
            times = [t for t in self.request_times[client_ip] 
                     if now - t < 1.0]
            
            # Check if limit exceeded
            if len(times) >= self.max_requests:
                return False
            
            # Allow request and record timestamp
            times.append(now)
            self.request_times[client_ip] = times
            return True
```

**Key Features**:
- Sliding window: Only counts requests in last 1 second
- Thread-safe: Uses lock to protect shared data structure
- Per-IP tracking: Each client has independent rate limit
- Automatic cleanup: Old timestamps removed on each check

### HTTP 429 Response

When rate limit is exceeded, the server returns:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: text/html

<!DOCTYPE html>
<html>
<head><title>429 Too Many Requests</title></head>
<body>
    <h1>Too Many Requests</h1>
    <p>You are sending requests too quickly!</p>
    <p>Rate Limit: Maximum 5 requests per second per IP.</p>
</body>
</html>
```

<img width="582" height="382" alt="image" src="https://github.com/user-attachments/assets/dfd7926f-ec16-4bfc-b5a2-84f2a0ada1f4" />
<img width="286" height="28" alt="image" src="https://github.com/user-attachments/assets/4719c8f2-c4b0-4238-b6ce-1087e0811aac" />


### Testing Rate Limiting

#### Spammer Test

**File**: `rate_limiter/spammer_main.py`

Sends 50 requests as fast as possible (concurrent):

<img width="265" height="135" alt="image" src="https://github.com/user-attachments/assets/079e4084-ce09-41f7-9a03-bc96f33aeb61" />


**Expected Behavior**:
- First ~5 requests succeed (200 OK)
- Remaining requests get rate limited (429 Too Many Requests)
- Low throughput of successful requests (~5 req/s maximum)

#### Well-Behaved Client Test

**File**: `rate_limiter/well_behaved_main.py`

Sends 10 requests with 1-second delay between each:

<img width="295" height="392" alt="image" src="https://github.com/user-attachments/assets/0d15722a-8753-4222-8284-5f0a57145cf1" />


**Expected Behavior**:
- All requests succeed (200 OK)
- No rate limiting (429)
- Stays under the limit

#### Comparison Test

**File**: `tests/compare_rate_limiting_main.py`

Runs both tests sequentially to compare throughput:

```bash
cd tests
python compare_rate_limiting_main.py
```

**Analysis**:
- **Spammer**: Gets rate limited, ~5 successful req/s (limited by rate limiter)
- **Well-Behaved**: No rate limiting, ~1 successful req/s (limited by delays)
- **Conclusion**: Rate limiter successfully throttles aggressive clients while allowing compliant clients full access

### Throughput Monitoring

**File**: `record_and_print.py`

Tracks per-IP statistics and prints throughput every 10 requests:

```python
def record_and_print(ip, success):
    with stats_lock:
        # Update counters
        stat['handled'] += 1
        if success:
            stat['success'] += 1
        
        # Print every 10 requests
        if stat['handled'] % 10 == 0:
            elapsed = now - stat['start']
            succ_per_sec = stat['success'] / elapsed
            print(f"THROUGHPUT [{ip}]: {stat['success']} successful "
                  f"in {elapsed:.2f}s -> {succ_per_sec:.2f} req/s")
```

<img width="422" height="18" alt="image" src="https://github.com/user-attachments/assets/b660d88b-15b6-496b-be8e-6a54b0f1647d" />

---

## Connecting to the Server from the outside

<img width="538" height="630" alt="image" src="https://github.com/user-attachments/assets/cf37cbfb-2335-4b36-bb3e-e7ed0ff3215a" />
<img width="445" height="18" alt="image" src="https://github.com/user-attachments/assets/b9aeabf0-a6fc-47db-b865-fea6be62aeea" />
<img width="909" height="62" alt="image" src="https://github.com/user-attachments/assets/d1666ac2-cc15-4c66-9b19-88ff10669f16" />


## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . .

EXPOSE 8080

ENTRYPOINT ["python", "main.py"]
CMD ["./my_website", "8080"]
```

### docker-compose.yaml

```yaml
version: "3.8"

services:
  web:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./my_website:/app/my_website
      - ./request_counts_server.json:/app/request_counts_server.json
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    entrypoint: ["tail", "-f", "/dev/null"]
    tty: true
    stdin_open: true

  client:
    build: .
    entrypoint: ["tail", "-f", "/dev/null"]
    depends_on:
      - web
    volumes:
      - ./downloads:/app/downloads
    tty: true
    stdin_open: true
```

**Key Changes from Lab 1**:
- Volume mount for `request_counts_server.json` to persist counter data
- Same container structure for easy testing

---

## How to Run

### Local Execution

**Start Multithreaded Server**:
```bash
cd LAB2
python main.py ./my_website 8080
```

The server starts with:
- 10 worker threads
- 1-second artificial delay per request (for benchmarking)
- Thread-safe request counter
- Rate limiting enabled (5 req/s per IP)

**Run Benchmark Tests**:
```bash
# Test multithreaded performance
cd tests
python benchmark_main.py

# Test counter race conditions
python counter_main.py

# Test rate limiting
python compare_rate_limiting_main.py
```

### Docker Execution

**Build and Start**:
```bash
docker compose build
docker compose up -d
```

**Run Server**:
```bash
docker compose exec web sh
python /app/main.py /app/my_website 8080
```

**Run Tests** (in separate terminal):
```bash
docker compose exec web sh
cd tests
python benchmark_main.py
python counter_main.py
python compare_rate_limiting_main.py
```

---

## Project Structure

```
LAB2/
├── main.py                          # Server entry point
├── start_server.py                  # Thread pool server implementation
├── handle_client.py                 # Per-thread request handler
├── handle_request.py                # HTTP request processing + rate limiting
├── record_and_print.py              # Throughput monitoring
├── request_counts_server.json       # Persisted request counts
│
├── counters/                        # Request counter implementations
│   ├── naive_counter.py            # Unsafe (race conditions)
│   ├── safe_counter.py             # Thread-safe (with locks)
│   ├── test_naive_counter.py       # Demonstrate race condition
│   └── test_safe_counter.py        # Demonstrate correctness
│
├── rate_limiter/                    # Rate limiting system
│   ├── rate_limiter.py             # Core rate limiter class
│   ├── make_request.py             # HTTP request utility
│   ├── spammer_main.py             # Aggressive client test
│   ├── well_behaved_main.py        # Compliant client test
│   └── run_test.py                 # Test runner utility
│
├── benchmark/                       # Performance testing
│   └── run_benchmark.py            # Concurrent request benchmark
│
├── tests/                           # Integration tests
│   ├── benchmark_main.py           # Run performance tests
│   ├── counter_main.py             # Run counter tests
│   ├── compare_rate_limiting_main.py # Compare rate limiting
│   ├── counts_demo_naive.json      # Naive counter test data
│   └── counts_demo_safe.json       # Safe counter test data
│
├── my_website/                      # Served content
│   ├── index.html
│   ├── cat.png
│   ├── Tutorial.pdf
│   └── [subdirectories...]
│
├── downloads/                       # Client download directory
├── Dockerfile
└── docker-compose.yaml
```

---

## Conclusion

This lab successfully demonstrates the implementation of a multithreaded HTTP server with advanced concurrency features:

1. **Multithreading**: Thread pool architecture provides 10x performance improvement for concurrent requests
2. **Race Conditions**: Demonstrated the problem with naive implementation and solved it with proper synchronization
3. **Rate Limiting**: Thread-safe rate limiter effectively throttles aggressive clients while allowing compliant access
4. **Request Tracking**: Thread-safe counter tracks file access statistics displayed in directory listings

The implementation showcases critical concepts in concurrent programming:
- Thread pools for resource management
- Locks and synchronization primitives for data safety
- Sliding window algorithms for rate limiting
- Performance benchmarking and testing methodologies

All features are fully functional, tested, and documented with working examples.

