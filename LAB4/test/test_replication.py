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

def do_write(key, value):
        start = time.time()
        try:
            r = requests.post(
                f"{LEADER_URL}/write",
                json={"key": key, "value": value},
                timeout=10,
            )
            success = (r.status_code == 200)
        except Exception:
            success = False
        end = time.time()
        return success, end - start

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
    for idx, url in enumerate(FOLLOWER_URLS, 1):
        resp = requests.get(f"{url}/read?key=test_key", timeout=5)
        assert resp.status_code == 200, f"Follower {idx} missing data"
        assert resp.json().get("value") == "test_value"
        print(f"Follower {idx} has correct data")

# Test 2: Concurrent writes
def test_concurrent_writes(num_writes=10):
    print("Test 2: Concurrent Writes")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(write_data, f"concurrent_key_{i}", f"value_{i}")
            for i in range(num_writes)
        ]
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
    writes_total = 100
    max_workers = 10  # "10 at a time"
    lab4_dir = str(pathlib.Path(__file__).resolve().parent.parent)

    for quorum in write_quorums:
        print("=" * 60)
        print(f"Testing WRITE_QUORUM={quorum}")

        # Restart docker-compose with new quorum
        env = os.environ.copy()
        env["WRITE_QUORUM"] = str(quorum)
        try:
            print("Restarting docker-compose with new WRITE_QUORUM...")
            subprocess.run(["docker-compose", "down"], check=True, cwd=lab4_dir, env=env)
            subprocess.run(["docker-compose", "up", "--build", "-d"], check=True, cwd=lab4_dir, env=env)
        except Exception as e:
            print(f"Failed to restart cluster: {e}")
            continue

        if not wait_for_services(timeout=60):
            print(f"Cluster not healthy for quorum={quorum}, skipping.")
            continue

        # 10 distinct keys, 100 writes total
        keys = [f"perf_key_{quorum}_{k}" for k in range(10)]
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(writes_total):
                key = keys[i % len(keys)]  
                value = f"perf_value_{i}"
                futures.append(executor.submit(do_write, key, value))

            for fut in as_completed(futures):
                success, latency = fut.result()
                if success:
                    latency_results[quorum].append(latency)

        # Wait for all background replications to complete
        # This ensures eventual consistency before checking
        print("Waiting for all background replications to complete...")
        try:
            requests.get(f"{LEADER_URL}/wait_for_replication", timeout=30)
        except Exception as e:
            print(f"Warning: failed to wait for replications: {e}")
            time.sleep(5)  # Fallback to sleep

        # Consistency check: leader vs each follower, for the keys used
        try:
            leader_all = requests.get(f"{LEADER_URL}/get_all", timeout=5).json().get("data", {})
        except Exception:
            leader_all = {}

        matching_followers = 0
        mismatches = []
        for url in FOLLOWER_URLS:
            try:
                fdata = requests.get(f"{url}/get_all", timeout=5).json().get("data", {})
            except Exception:
                fdata = {}

            all_match = True
            for k in keys:
                if leader_all.get(k) != fdata.get(k):
                    all_match = False
                    break

            if all_match:
                matching_followers += 1
            else:
                mismatches.append(url)

        avg = mean(latency_results[quorum]) if latency_results[quorum] else float("inf")
        print(f"WRITE_QUORUM={quorum}: "
              f"{len(latency_results[quorum])}/{writes_total} successful writes, "
              f"avg latency={avg:.4f}s")
        print(f"Followers matching leader on tested keys: "
              f"{matching_followers}/{len(FOLLOWER_URLS)}; mismatches={mismatches}")

    # Plot quorum vs latency
    avg_latencies = {
        q: (mean(latency_results[q]) if latency_results[q] else float("inf"))
        for q in write_quorums
    }

    print("Average latencies by WRITE_QUORUM:")
    for q, avg in avg_latencies.items():
        print(f"  quorum={q}: {avg:.4f} s")

    plt.figure()
    plt.plot(list(avg_latencies.keys()), list(avg_latencies.values()), marker="o")
    plt.title("Write Quorum vs Average Write Latency")
    plt.xlabel("Write Quorum (followers)")
    plt.ylabel("Average Latency (seconds)")
    plt.xticks(write_quorums)
    plt.grid(True)
    plt.savefig("write_quorum_vs_latency.png")
    print("Saved plot as write_quorum_vs_latency.png")

if __name__ == "__main__":
    ok = wait_for_services(timeout=60)
    if not ok:
        print("Cluster not healthy at start, attempting docker-compose up...")
        lab4_dir = str(pathlib.Path(__file__).resolve().parent.parent)
        env = os.environ.copy()
        try:
            subprocess.run(["docker-compose", "up", "--build", "-d"], check=True, cwd=lab4_dir, env=env)
        except Exception as e:
            print(f"Failed to start cluster automatically: {e}")
            raise SystemExit(1)

        ok = wait_for_services(timeout=90)
        if not ok:
            print("Services did not become healthy. Exiting.")
            raise SystemExit(1)

    try:
        test_basic_write_read()
        test_concurrent_writes(num_writes=10)
        test_performance()
        print("All tests finished.")
    except AssertionError as e:
        print(f"Test assertion failed: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during tests: {e}")
        raise