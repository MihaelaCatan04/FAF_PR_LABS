import requests
import time
import concurrent.futures
from concurrent.futures import as_completed
import matplotlib.pyplot as plt
from statistics import mean
import os
import subprocess
import pathlib

# Configuration
LEADER_URL = "http://localhost:5000"
FOLLOWER_URLS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003",
    "http://localhost:5004",
    "http://localhost:5005"
]

def write_data(key, value):
        response = requests.post(
            f"{LEADER_URL}/write",
            json={"key": key, "value": value}
        )
        return response.status_code == 200

# Wait for all services to be healthy
def wait_for_services(timeout=30):
    print("Waiting for services to be healthy...")
    start_time = time.time()
    sleep_interval = 1.0
    while time.time() - start_time < timeout:
        try:
            # Check leader health
            leader_ok = False
            try:
                leader_resp = requests.get(f"{LEADER_URL}/health", timeout=2)
                leader_ok = (leader_resp.status_code == 200)
            except requests.RequestException:
                leader_ok = False

            # Check followers health
            all_followers_ok = True
            for follower_url in FOLLOWER_URLS:
                try:
                    resp = requests.get(f"{follower_url}/health", timeout=2)
                    if resp.status_code != 200:
                        all_followers_ok = False
                        break
                except requests.RequestException:
                    all_followers_ok = False
                    break

            if leader_ok and all_followers_ok:
                print("All services are healthy.")
                return True

        except Exception:
            # ignore and retry until timeout
            pass

        time.sleep(sleep_interval)

    print("Timeout waiting for services to be healthy.")
    return False

# Test 1: Basic write and read functionality
def test_basic_write_read():
    print("Test 1: Basic Write and Read Functionality")
    
    # Write to leader
    response = requests.post(
        f"{LEADER_URL}/write",
        json={"key": "test_key", "value": "test_value"}
    )

    assert response.status_code == 200, "Write to leader failed"
    data = response.json()
    print(f"Write response: {data}")
    assert data['status'] == 'success'
    print("Write successful")

    # Read from leader
    response = requests.get(f"{LEADER_URL}/read?key=test_key")
    assert response.status_code == 200, "Read from leader failed"
    data = response.json()
    assert data['value'] == 'test_value'
    print("Read from leader successful")

    # Give replication some time to complete
    time.sleep(2)

    # Verify data on followers
    for i, follower_url in enumerate(FOLLOWER_URLS, 1):
        response = requests.get(f"{follower_url}/read?key=test_key")
        if response.status_code == 200:
            data = response.json()
            assert data['value'] == 'test_value'
            print(f"Follower {i} has correct data")
        else:
            print(f"Follower {i} doesn't have the data yet")

# Test 2: Concurrent writes
def test_concurrent_writes(num_writes=10):
    print("Test 2: Concurrent Writes")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(num_writes):
            future = executor.submit(write_data, f"concurrent_key_{i}", f"value_{i}")
            futures.append(future)
        
        results = [f.result() for f in futures]
    
    successful = sum(results)
    print(f"{successful}/{num_writes} concurrent writes successful")
    assert successful >= 8, "Too many concurrent writes failed"

# Test 3: Performance measurement
# Performance Analysis:
#     1. Test write quorum (1-5) vs average latency
#     2. Check data consistency after all writes
def test_performance(num_writes=20):
    print("Test 3: Performance Measurement")
    write_quorums = [1, 2, 3, 4, 5]
    latency_results = {q: [] for q in write_quorums}

    # We'll perform 100 writes per quorum in batches of 10 concurrent writers
    writes_total = 100
    max_workers = 10

    def do_write(key, value):
        start = time.time()
        try:
            r = requests.post(f"{LEADER_URL}/write", json={"key": key, "value": value}, timeout=10)
            success = (r.status_code == 200)
        except Exception:
            success = False
        end = time.time()
        return success, end - start

    for quorum in write_quorums:
        print(f"Testing with write quorum: {quorum}")

        # Recreate the full cluster (followers + leader) with the desired WRITE_QUORUM
        # Use `docker-compose down` then `docker-compose up --build -d` to ensure a clean cluster
        lab4_dir = str(pathlib.Path(__file__).resolve().parent.parent)
        env = os.environ.copy()
        env['WRITE_QUORUM'] = str(quorum)
        try:
            print(f"Recreating full cluster with WRITE_QUORUM={quorum} (down/up)...")
            subprocess.run(["docker-compose", "down"], check=True, cwd=lab4_dir, env=env)
            subprocess.run(["docker-compose", "up", "--build", "-d"], check=True, cwd=lab4_dir, env=env)
        except Exception as e:
            print(f"Failed to recreate cluster with quorum {quorum}: {e}")
            continue

        # Wait for all services to be healthy after restart
        ok = wait_for_services(timeout=60)
        if not ok:
            print(f"Services did not become healthy after recreating cluster for quorum {quorum}")
            continue

        # Prepare keys (10 distinct keys) and submit writes_total writes across them
        keys = [f"perf_key_{quorum}_{k}" for k in range(10)]
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(writes_total):
                key = keys[i % len(keys)]
                future = executor.submit(do_write, key, f"perf_value_{i}")
                futures.append(future)

            for fut in as_completed(futures):
                success, latency = fut.result()
                if success:
                    latency_results[quorum].append(latency)

        # Consistency check: compare leader data to followers for the keys used
        try:
            leader_all = requests.get(f"{LEADER_URL}/get_all", timeout=5).json().get('data', {})
        except Exception:
            leader_all = {}

        matching_followers = 0
        mismatches = []
        for follower_url in FOLLOWER_URLS:
            try:
                fdata = requests.get(f"{follower_url}/get_all", timeout=5).json().get('data', {})
            except Exception:
                fdata = {}

            # Check that for all keys used in this run the follower has same value as leader
            all_match = True
            for k in keys:
                leader_val = leader_all.get(k)
                follower_val = fdata.get(k)
                if leader_val != follower_val:
                    all_match = False
                    break

            if all_match:
                matching_followers += 1
            else:
                mismatches.append(follower_url)

        avg = mean(latency_results[quorum]) if latency_results[quorum] else float('inf')
        print(f"Quorum {quorum}: {len(latency_results[quorum])}/{writes_total} successful writes, avg latency {avg:.4f}s")
        print(f"Followers matching leader for keys: {matching_followers}/{len(FOLLOWER_URLS)}; mismatches: {mismatches}")

    # Calculate average latencies for plotting
    avg_latencies = {q: mean(latency_results[q]) if latency_results[q] else float('inf') for q in write_quorums}
    print("Average Latencies by Write Quorum:")
    for q, avg in avg_latencies.items():
        print(f"Quorum {q}: {avg:.4f} seconds")

    # Plot results
    plt.figure()
    plt.plot(list(avg_latencies.keys()), list(avg_latencies.values()), marker='o')
    plt.title('Write Quorum vs Average Latency')
    plt.xlabel('Write Quorum')
    plt.ylabel('Average Latency (seconds)')
    plt.xticks(write_quorums)
    plt.grid()
    plt.savefig('write_quorum_vs_latency.png')
    print("Performance plot saved as 'write_quorum_vs_latency.png'")


if __name__ == '__main__':
    # Wait for the leader and followers to be healthy before running tests
    ok = wait_for_services(timeout=60)
    if not ok:
        # Try to start the cluster automatically (useful when the cluster is down)
        print("Services not healthy. Attempting to start cluster with docker-compose up --build -d ...")
        lab4_dir = str(pathlib.Path(__file__).resolve().parent.parent)
        env = os.environ.copy()
        # Respect any WRITE_QUORUM env if already set, otherwise default left to compose file
        try:
            subprocess.run(["docker-compose", "up", "--build", "-d"], check=True, cwd=lab4_dir, env=env)
        except Exception as e:
            print(f"Failed to start cluster automatically: {e}")
            print("Services did not become healthy in time. Exiting.")
            raise SystemExit(1)

        # Wait again with a slightly larger timeout
        ok = wait_for_services(timeout=90)
        if not ok:
            print("Services did not become healthy after automatic start. Exiting.")
            raise SystemExit(1)

    try:
        print("Running basic write/read test...")
        test_basic_write_read()

        print("Running concurrent writes test...")
        test_concurrent_writes(num_writes=10)

        print("Running performance measurement (this may take a while)...")
        test_performance()

        print("All tests finished.")
    except AssertionError as e:
        print(f"A test assertion failed: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during tests: {e}")
        raise
