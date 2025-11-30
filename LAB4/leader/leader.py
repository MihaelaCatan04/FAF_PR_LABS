from flask import Flask, request, jsonify
import os
import threading
import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

app = Flask(__name__)

# In-memory key-value store with versioning
data_store = {}  # {key: {"value": value, "version": int}}

# Lock for thread-safe operations
data_lock = threading.Lock()

# Global version counter for ordering writes
version_counter = 0
version_lock = threading.Lock()

# Configuration from environment variables
WRITE_QUORUM = int(os.environ.get('WRITE_QUORUM', 3))
MIN_DELAY = int(os.environ.get('MIN_DELAY', 0))  # in milliseconds
MAX_DELAY = int(os.environ.get('MAX_DELAY', 1000))  # in milliseconds

# Follower URLs
FOLLOWERS = []
for i in range(1, 6):
    follower_url = os.environ.get(f'FOLLOWER_{i}_URL')
    if follower_url:
        FOLLOWERS.append(follower_url)

print(f"Leader started with:")
print(f"Write Quorum: {WRITE_QUORUM}")
print(f"Delay Range: [{MIN_DELAY}ms, {MAX_DELAY}ms]")
print(f"Followers: {FOLLOWERS}")

# Validate configured quorum vs available followers
configured_quorum = WRITE_QUORUM
num_followers = len(FOLLOWERS)
if num_followers == 0:
    print("Warning: no followers configured. Replication will not happen.")
else:
    if configured_quorum > num_followers:
        print(f"Warning: WRITE_QUORUM={WRITE_QUORUM} > followers={num_followers}. Capping to {num_followers}.")
        WRITE_QUORUM = num_followers

# Replicate a key-value pair to a single follower with retry logic.
# Returns True if successful, False otherwise.
def replicate_to_follower(follower_url, key, value, version, max_retries=3):
    for attempt in range(max_retries):
        try:
            # Only apply delay on first attempt (not on retries)
            if attempt == 0:
                delay = random.randint(MIN_DELAY, MAX_DELAY) / 1000.0
                time.sleep(delay)
            
            response = requests.post(
                f"{follower_url}/replicate",
                json={"key": key, "value": value, "version": version},
                timeout=5
            )
            if response.status_code == 200:
                if attempt == 0:
                    print(f"Replicated to {follower_url} v{version} (delay: {delay * 1000:.0f}ms)")
                else:
                    print(f"Replicated to {follower_url} v{version} (retry {attempt})")
                return True
            elif response.status_code == 409:
                # Conflict due to stale version - treat as success since data is already there
                print(f"Replicated to {follower_url} v{version} (conflict - already has newer version)")
                return True
            else:
                print(f"Failed to replicate to {follower_url}: {response.status_code}")
        except Exception as e:
            print(f"Error replicating to {follower_url} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
    
    return False

# Background thread pool for async replication
background_executor = ThreadPoolExecutor(max_workers=100, thread_name_prefix="bg-repl")

# Track all pending replication futures for proper cleanup
all_pending_futures = []
futures_lock = threading.Lock()

# Track failed replications for retry
failed_replications = []  # List of (key, value, version, followers_to_retry)
failed_repl_lock = threading.Lock()

# Replicate to all followers concurrently.
# Returns the number of successful replications (for quorum check).
# Semi-synchronous: wait for WRITE_QUORUM, but ensure ALL replications eventually complete.
def replicate_to_followers(key, value, version):
    if not FOLLOWERS:
        return 0

    # Submit all replication tasks
    future_to_follower = {
        background_executor.submit(replicate_to_follower, follower_url, key, value, version): follower_url
        for follower_url in FOLLOWERS
    }

    # Track ALL futures globally
    with futures_lock:
        all_pending_futures.extend(future_to_follower.keys())

    successful = 0
    failed_followers = []
    checked_count = 0
    
    # Collect results as they complete
    for future in as_completed(future_to_follower.keys()):
        follower_url = future_to_follower[future]
        checked_count += 1
        
        try:
            ok = future.result()
            if ok:
                successful += 1
            else:
                failed_followers.append(follower_url)
        except Exception as e:
            print(f"[REPL] Exception in replication to {follower_url}: {e}")
            failed_followers.append(follower_url)
        
        # Once quorum is met, return immediately
        # Remaining futures continue in background
        if successful >= WRITE_QUORUM:
            print(f"[REPL] Quorum {WRITE_QUORUM} met for {key} v{version} (checked {checked_count}/{len(FOLLOWERS)})")
            # If there are unchecked futures, they continue in background
            # and will be tracked in all_pending_futures
            break
    
    # If some replications failed and we still met quorum,
    # schedule background retry for failed ones
    if failed_followers and successful >= WRITE_QUORUM:
        with failed_repl_lock:
            failed_replications.append((key, value, version, failed_followers))
    
    return successful

# Helper endpoint to wait for all pending replications (for testing)
@app.route("/wait_for_replication", methods=["GET"])
def wait_for_replication():
    # Get snapshot of pending futures
    with futures_lock:
        pending = list(all_pending_futures)
        all_pending_futures.clear()
    
    # Also retry any failed replications
    with failed_repl_lock:
        to_retry = list(failed_replications)
        failed_replications.clear()
    
    total_futures = len(pending)
    
    if total_futures == 0 and len(to_retry) == 0:
        print("[WAIT] No pending futures or retries")
        return jsonify({"status": "no pending work"}), 200
    
    print(f"[WAIT] Waiting for {total_futures} futures, retrying {len(to_retry)} failed replications...")
    
    # Wait for all pending futures
    completed = 0
    failed = 0
    for future in pending:
        try:
            result = future.result(timeout=10)
            if result:
                completed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"[WAIT] Future failed: {e}")
    
    # Retry failed replications
    retry_success = 0
    retry_failed = 0
    for key, value, version, followers in to_retry:
        for follower_url in followers:
            if replicate_to_follower(follower_url, key, value, version, max_retries=5):
                retry_success += 1
            else:
                retry_failed += 1
                print(f"[WAIT] Failed to replicate {key} v{version} to {follower_url} after retries")
    
    print(f"[WAIT] Done. Completed: {completed}, Failed: {failed}, Retry Success: {retry_success}, Retry Failed: {retry_failed}")
    
    return jsonify({
        "status": "complete",
        "waited_for": total_futures,
        "completed": completed,
        "failed": failed,
        "retry_success": retry_success,
        "retry_failed": retry_failed
    }), 200

# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "role": "leader", "write_quorum": WRITE_QUORUM, "followers": len(FOLLOWERS)}), 200

# Endpoint to write data
# Body: {"key": "some_key", "value": "some_value"}
# Process:
#     1. Assign version number
#     2. Write to leader's store with version
#     3. Replicate to followers concurrently
#     4. Wait for WRITE_QUORUM confirmations
#     5. Return success (remaining replications continue in background)
@app.route("/write", methods=["POST"])
def write():
    start_time = time.time()
    try:
        payload = request.get_json()
        key = payload['key']
        value = payload['value']

        if key is None or value is None:
            return jsonify({"error": "Key and Value cannot be None"}), 400
        
        # Step 1: Assign a globally ordered version number
        with version_lock:
            global version_counter
            version_counter += 1
            version = version_counter
        
        # Step 2: Write to leader's store with version
        with data_lock:
            data_store[key] = {"value": value, "version": version}

        print(f"Leader wrote: {key} = {value} (v{version})")

        # Step 3 & 4: Replicate to followers and count successes
        successful_replications = replicate_to_followers(key, value, version)

        latency = (time.time() - start_time) * 1000
        
        # Step 5: Check if we met the quorum requirement
        if successful_replications >= WRITE_QUORUM:
            return jsonify({
                "status": "success",
                "key": key,
                "version": version,
                "replications": successful_replications,
                "quorum": WRITE_QUORUM,
                "latency_ms": round(latency, 2)
            }), 200
        else:
            return jsonify({
                "status": "failure",
                "message": "Write quorum not met",
                "replications": successful_replications,
                "quorum": WRITE_QUORUM,
                "latency_ms": round(latency, 2)
            }), 500
            
    except Exception as e:
        print(f"Error in write: {e}")
        return jsonify({"error": str(e)}), 500
    
# Endpoint to read data
# Query parameter: ?key=some_key
@app.route("/read", methods=["GET"])
def read():
    key = request.args.get('key')
    if key is None:
        return jsonify({"error": "Key parameter is required"}), 400
    
    with data_lock:
        data = data_store.get(key)
    
    if data is None:
        return jsonify({"error": "Key not found"}), 404
    
    return jsonify({
        "key": key,
        "value": data["value"],
        "version": data["version"],
        "source": "leader"
    }), 200

# Return all data in the leader
@app.route("/get_all", methods=["GET"])
def get_all():
    with data_lock:
        all_data = data_store.copy()
    return jsonify({"data": all_data, "source": "leader"}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)