import os
import json
import threading
import time

class RequestCounterSafe:

    def __init__(self, counter_file='request_counts_safe.json'):

        self.counter_file = counter_file
        self.counts = self._load_counts()
        self.lock = threading.RLock()
    
    def _load_counts(self):
        if os.path.exists(self.counter_file):
            try:
                with open(self.counter_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading counts: {e}")
                return {}
        return {}
    
    def _save_counts(self):
        try:
            with open(self.counter_file, 'w') as f:
                json.dump(self.counts, f, indent=2)
        except Exception as e:
            print(f"Error saving counts: {e}")
    
    def increment(self, file_path):
        with self.lock: 
            if file_path not in self.counts:
                self.counts[file_path] = 0
            time.sleep(0.0001)
            
            # Step 1: READ
            current = self.counts[file_path]
            
            # Step 2: CALCULATE
            time.sleep(0.0001)
            
            # Step 3: WRITE
            self.counts[file_path] = current + 1
            
            # Save to file
            # Other threads still WAIT!
            time.sleep(0.0001)
            self._save_counts()
    
    def get_count(self, file_path):
        with self.lock:
            return self.counts.get(file_path, 0)
    
    def get_all_counts(self):
        with self.lock:
            return self.counts.copy()
    
    def reset(self):
        with self.lock:
            self.counts = {}
            if os.path.exists(self.counter_file):
                os.remove(self.counter_file)