import requests
import time
import concurrent.futures
import matplotlib.pyplot as plt
from statistics import mean

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

    while time.time() - start_time < timeout:
        try:
            # Check leader health
            leader_resp = requests.get(f"{LEADER_URL}/health", timeout=2)
            if leader_resp.status_code != 200:
                continue

            # Check followers health
            all_healthy = True
            for follower_url in FOLLOWER_URLS:
                resp = requests.get(f"{follower_url}/health", timeout=2)
                if resp.status_code != 200:
                    all_healthy = False
                    break

            if all_healthy:
                print("All services are healthy.")
                return True
            
        except Exception as e:
            pass    
        time.sleep(2)
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
