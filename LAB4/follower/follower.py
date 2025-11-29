from flask import Flask, request, jsonify
import os
import threading

app = Flask(__name__)

# In-memory key-value store
data_store = {}

# Lock for thread-safe operations
data_lock = threading.Lock()

FOLLOWER_ID = os.environ.get('FOLLOWER_ID', 'follower-unknown')

# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "follower_id": FOLLOWER_ID}), 200

# Replicate data from leader
# The leader sends: {"key": "some_key", "value": "some_value"}
@app.route("/replicate", methods=["POST"])
def replicate():
    try:
        payload = request.get_json()
        key = payload['key']
        value = payload['value']

        if key is None:
            return jsonify({"error": "Key cannot be None"}), 400
        
        # Store the key-value pair in a thread-safe manner
        with data_lock:
            data_store[key] = value

        print(f"[{FOLLOWER_ID}] Replicated: {key} = {value}")

        return jsonify({"status": "success", "follower_id": FOLLOWER_ID, "key": key}), 200
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
        value = data_store.get(key)

    if value is None:
        return jsonify({"error": "Key not found"}), 404
    
    return jsonify({"key": key, "value": value, "follower_id": FOLLOWER_ID}), 200

# Endpoint to get all data
@app.route("/get_all", methods=["GET"])
def get_all():
    with data_lock:
        all_data = data_store.copy()
    return jsonify({"data": all_data, "follower_id": FOLLOWER_ID}), 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)