import time
import asyncio
import httpx
import requests
import matplotlib.pyplot as plt
from statistics import mean
import os
import subprocess
import pathlib
import concurrent.futures

# Configuration
LEADER_URL = "http://localhost:5000"
FOLLOWER_URLS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003",
    "http://localhost:5004",
    "http://localhost:5005",
]


def wait_for_services(timeout=60):
    print("Waiting for services to be healthy...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            leader_ok = False
            try:
                r = requests.get(f"{LEADER_URL}/health", timeout=2)
                leader_ok = r.status_code == 200
            except Exception:
                leader_ok = False

            all_followers_ok = True
            for u in FOLLOWER_URLS:
                try:
                    r = requests.get(f"{u}/health", timeout=2)
                    if r.status_code != 200:
                        all_followers_ok = False
                        break
                except Exception:
                    all_followers_ok = False
                    break

            if leader_ok and all_followers_ok:
                print("All services healthy")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("Timed out waiting for services")
    return False


async def do_write_async(client: httpx.AsyncClient, key, value, timeout=10):
    start = time.time()
    try:
        r = await client.post(f"{LEADER_URL}/write", json={"key": key, "value": value}, timeout=timeout)
        success = r.status_code == 200
    except Exception:
        success = False
    end = time.time()
    return success, end - start


# Test 1: Basic write and read functionality
async def test_basic_write_read():
    print("\n" + "="*60)
    print("Test 1: Basic Write and Read Functionality")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # Write to leader
        response = await client.post(
            f"{LEADER_URL}/write",
            json={"key": "test_key", "value": "test_value"},
            timeout=10
        )
        
        assert response.status_code == 200, "Write to leader failed"
        data = response.json()
        print(f"Write response: {data}")
        assert data['status'] == 'success'
        print("Write successful")
        
        # Read from leader
        response = await client.get(f"{LEADER_URL}/read?key=test_key", timeout=5)
        assert response.status_code == 200, "Read from leader failed"
        data = response.json()
        assert data['value'] == 'test_value'
        print("Read from leader successful")
        
        # Give replication some time to complete
        print("Waiting for replication to complete...")
        await asyncio.sleep(2)
        
        # Verify data on followers concurrently
        async def check_follower(idx, url):
            try:
                resp = await client.get(f"{url}/read?key=test_key", timeout=5)
                if resp.status_code == 200 and resp.json().get("value") == "test_value":
                    print(f"Follower {idx} has correct data")
                    return True
                else:
                    print(f"Follower {idx} missing or incorrect data")
                    return False
            except Exception as e:
                print(f"Follower {idx} error: {e}")
                return False
        
        tasks = [check_follower(idx, url) for idx, url in enumerate(FOLLOWER_URLS, 1)]
        results = await asyncio.gather(*tasks)
        followers_ok = sum(results)
        
        print(f"Followers with correct data: {followers_ok}/{len(FOLLOWER_URLS)}")
        assert followers_ok >= 3, "Too few followers have replicated data"


# Test 2: Concurrent writes using asyncio
async def test_concurrent_writes(num_writes=20):
    print("\n" + "="*60)
    print(f"Test 2: Concurrent Writes ({num_writes} writes)")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        async def do_write(i):
            try:
                response = await client.post(
                    f"{LEADER_URL}/write",
                    json={"key": f"concurrent_key_{i}", "value": f"value_{i}"},
                    timeout=10
                )
                return response.status_code == 200
            except Exception:
                return False
        
        tasks = [do_write(i) for i in range(num_writes)]
        results = await asyncio.gather(*tasks)
        
        successful = sum(results)
        print(f"Concurrent writes: {successful}/{num_writes} successful")
        assert successful >= num_writes * 0.8, f"Too many concurrent writes failed: {successful}/{num_writes}"
        print(f"Concurrent writes test passed")


if __name__ == '__main__':
    lab_dir = str(pathlib.Path(__file__).resolve().parent.parent)
    
    # First, ensure the cluster is up with default settings
    print("Checking if cluster is running...")
    if not wait_for_services(timeout=30):
        print("Cluster not running, starting it...")
        env = os.environ.copy()
        try:
            subprocess.run(["docker-compose", "up", "--build", "-d"], check=True, cwd=lab_dir, env=env)
        except Exception as e:
            print(f"Failed to start cluster: {e}")
            raise SystemExit(1)
        
        if not wait_for_services(timeout=90):
            print("Services did not become healthy. Exiting.")
            raise SystemExit(1)
    
    # Run basic tests
    try:
        asyncio.run(test_basic_write_read())
        asyncio.run(test_concurrent_writes(num_writes=20))
    except AssertionError as e:
        print(f"Test failed: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
    
    # Now run performance analysis
    print("\n" + "="*60)
    print("Test 3: Performance Analysis - Write Quorum vs Latency")
    print("="*60)
    
    write_quorums = [1, 2, 3, 4, 5]
    latency_results = {q: [] for q in write_quorums}
    writes_total = 100
    max_workers = 10

    for quorum in write_quorums:
        print('=' * 60)
        print(f"Testing WRITE_QUORUM={quorum}")
        env = os.environ.copy()
        env['WRITE_QUORUM'] = str(quorum)

        try:
            subprocess.run(["docker-compose", "down"], check=True, cwd=lab_dir, env=env)
            subprocess.run(["docker-compose", "up", "--build", "-d"], check=True, cwd=lab_dir, env=env)
        except Exception as e:
            print(f"Failed to start compose: {e}")
            continue

        if not wait_for_services(timeout=60):
            print("Cluster not healthy, skipping")
            continue

        # prepare keys
        keys = [f"perf_key_{quorum}_{k}" for k in range(10)]

        # Use an async httpx client and asyncio to issue concurrent write requests.
        async def run_writes():
            sem = asyncio.Semaphore(max_workers)
            async with httpx.AsyncClient() as client:
                async def sem_write(i):
                    key = keys[i % len(keys)]
                    value = f"perf_value_{i}"
                    async with sem:
                        return await do_write_async(client, key, value)

                tasks = [asyncio.create_task(sem_write(i)) for i in range(writes_total)]

                for coro in asyncio.as_completed(tasks):
                    success, latency = await coro
                    if success:
                        latency_results[quorum].append(latency)

        # Run the async writer
        try:
            asyncio.run(run_writes())
        except Exception as e:
            print(f"Async write phase failed: {e}")

        # wait for background replications
        try:
            result = requests.get(f"{LEADER_URL}/wait_for_replication", timeout=30).json()
            print(f"Wait completed: iterations={result['iterations']}, "
                  f"unique_tasks={result['unique_tasks_processed']}, "
                  f"completed={result['completed']}, failed={result['failed']}, "
                  f"retry_success={result['retry_success']}, remaining={result['remaining_pending']}")

        except Exception as e:
            print(f"Warning: wait_for_replication failed: {e}")
            time.sleep(5)
        

        # consistency check
        try:
            leader_all = requests.get(f"{LEADER_URL}/get_all", timeout=5).json().get('data', {})
        except Exception:
            leader_all = {}

        matching = 0
        mismatches = []
        for u in FOLLOWER_URLS:
            try:
                fdata = requests.get(f"{u}/get_all", timeout=5).json().get('data', {})
            except Exception:
                fdata = {}
            all_match = True
            for k in keys:
                if leader_all.get(k) != fdata.get(k):
                    all_match = False
                    break
            if all_match:
                matching += 1
            else:
                mismatches.append(u)

        avg = mean(latency_results[quorum]) if latency_results[quorum] else float('inf')
        print(f"WRITE_QUORUM={quorum}: {len(latency_results[quorum])}/{writes_total} successes, avg latency={avg:.4f}s")
        print(f"Followers matching leader: {matching}/{len(FOLLOWER_URLS)}; mismatches={mismatches}")

    avg_latencies = {q: (mean(latency_results[q]) if latency_results[q] else float('inf')) for q in write_quorums}
    print("Average latencies by WRITE_QUORUM:")
    for q, a in avg_latencies.items():
        print(f"  quorum={q}: {a:.4f} s")

    plt.figure()
    plt.plot(list(avg_latencies.keys()), list(avg_latencies.values()), marker='o')
    plt.title('Write Quorum vs Average Write Latency')
    plt.xlabel('Write Quorum (followers)')
    plt.ylabel('Average Latency (seconds)')
    plt.grid(True)
    plt.savefig('write_quorum_vs_latency.png')
    print('Saved plot write_quorum_vs_latency.png')
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("="*60)
