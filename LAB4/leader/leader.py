from flask import Flask, request, jsonify
import os
import threading
import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# In-memory key-value store
data_store = {}

# Lock for thread-safe operations
data_lock = threading.Lock()

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
        print(f"Warning: configured WRITE_QUORUM={configured_quorum} is greater than available followers={num_followers}. Capping to {num_followers}.")
        WRITE_QUORUM = num_followers

# Replicate a key-value pair to a single follower.
# Returns True if successful, False otherwise.
def replicate_to_follower(follower_url, key, value):
    try:
        delay = random.randint(MIN_DELAY, MAX_DELAY) / 1000.0  # Convert to seconds
        time.sleep(delay)  # Simulate network delay

        response = requests.post(
            f"{follower_url}/replicate",
            json={"key": key, "value": value},
            timeout=5
        )
        if response.status_code == 200:
            print(f"Replicated to {follower_url} (delay: {delay * 1000}ms)")
            return True
        else:
            print(f"Failed to replicate to {follower_url}: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error replicating to {follower_url}: {e}")
        return False
    
# Replicate to all followers concurrently.
# Returns the number of successful replications.
def replicate_to_followers(key, value):
    successful_replicas = 0
    num_followers = len(FOLLOWERS)

    # If there are no followers configured, nothing to replicate to.
    if num_followers == 0:
        return 0

    executor = ThreadPoolExecutor(max_workers=num_followers)
    shut_down_early = False
    try:
        future_to_follower = {
            executor.submit(replicate_to_follower, follower_url, key, value): follower_url
            for follower_url in FOLLOWERS
        }

        for future in as_completed(future_to_follower):
            try:
                ok = future.result()
            except Exception:
                ok = False

            if ok:
                successful_replicas += 1

            # As soon as we reach the write quorum, return to caller
            # without waiting for remaining followers' replies.
            if successful_replicas >= WRITE_QUORUM:
                # Shut down without waiting for running tasks to finish
                # so we don't block here. Remaining requests will continue
                # in background threads until they complete.
                try:
                    executor.shutdown(wait=False)
                except Exception:
                    pass
                shut_down_early = True
                break
    finally:
        # Ensure executor is shut down; if we already shut down early,
        # this is a no-op.
        try:
            executor.shutdown(wait=False)
        except Exception:
            pass

    return successful_replicas

# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "role": "leader", "write_quorum": WRITE_QUORUM, "followers": len(FOLLOWERS)}), 200

# Endpoint to write data
# Body: {"key": "some_key", "value": "some_value"}
    
#     Process:
#     1. Write to leader's store
#     2. Replicate to followers concurrently
#     3. Wait for WRITE_QUORUM confirmations
#     4. Return success or failure
@app.route("/write", methods=["POST"])
def write():
    start_time = time.time()
    try:
        payload = request.get_json()
        key = payload['key']
        value = payload['value']

        if key is None or value is None:
            return jsonify({"error": "Key and Value cannot be None"}), 400
        
        # Step 1: Write to leader's store
        with data_lock:
            data_store[key] = value

        print(f"Leader wrote: {key} = {value}")

        # Step 2 & 3: Replicate to followers and count successes
        successful_replications = replicate_to_followers(key, value)

        latency = (time.time() - start_time) * 1000
        # Step 4: Check if we met the quorum requirement
        if successful_replications >= WRITE_QUORUM:
            return jsonify({
                "status": "success",
                "key": key,
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
        value = data_store.get(key)
    
    if value is None:
        return jsonify({"error": "Key not found"}), 404
    
    return jsonify({
        "key": key,
        "value": value,
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