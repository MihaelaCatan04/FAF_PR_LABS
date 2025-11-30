from flask import Flask, request, jsonify
import os
import threading

app = Flask(__name__)

# In-memory key-value store with versioning
data_store = {}  # {key: {"value": value, "version": int}}

# Lock for thread-safe operations
data_lock = threading.Lock()

FOLLOWER_ID = os.environ.get('FOLLOWER_ID', 'follower-unknown')

# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "follower_id": FOLLOWER_ID}), 200

# Replicate data from leader
# The leader sends: {"key": "some_key", "value": "some_value", "version": int}
@app.route("/replicate", methods=["POST"])
def replicate():
    try:
        payload = request.get_json()
        key = payload['key']
        value = payload['value']
        version = payload.get('version', 0)  # Default to 0 for backward compatibility

        if key is None:
            return jsonify({"error": "Key cannot be None"}), 400
        
        # Store the key-value pair with version checking
        with data_lock:
            existing = data_store.get(key)
            
            # Only accept the write if:
            # 1. Key doesn't exist yet, OR
            # 2. New version is greater than existing version
            if existing is None or version > existing["version"]:
                data_store[key] = {"value": value, "version": version}
                print(f"[{FOLLOWER_ID}] Replicated: {key} = {value} (v{version})")
                return jsonify({"status": "success", "follower_id": FOLLOWER_ID, "key": key, "version": version}), 200
            else:
                print(f"[{FOLLOWER_ID}] Rejected stale write: {key} v{version} (current: v{existing['version']})")
                # Return 409 Conflict for stale versions so leader knows this wasn't a network failure
                return jsonify({
                    "status": "conflict",
                    "reason": "stale_version",
                    "follower_id": FOLLOWER_ID,
                    "key": key,
                    "current_version": existing["version"],
                    "provided_version": version
                }), 409
    except Exception as e:
        print(f"[{FOLLOWER_ID}] Error in replicate: {e}")
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
        "follower_id": FOLLOWER_ID
    }), 200

# Endpoint to get all data
@app.route("/get_all", methods=["GET"])
def get_all():
    with data_lock:
        all_data = data_store.copy()
    return jsonify({"data": all_data, "follower_id": FOLLOWER_ID}), 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)