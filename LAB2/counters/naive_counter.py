import os
import json
import time

class RequestCounterNaive:

    def __init__(self, counter_file='request_counts_naive.json'):
        self.counter_file = counter_file
        self.counts = self._load_counts()
    
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
        # Add delays to FORCE race conditions
        time.sleep(0.0001)
        
        # Step 1: READ current value
        if file_path not in self.counts:
            self.counts[file_path] = 0
        
        current = self.counts[file_path]
        
        # Step 2: CALCULATE new value
        time.sleep(0.0001)
        
        # Step 3: WRITE new value
        self.counts[file_path] = current + 1
        
        # Save to file with delay
        time.sleep(0.0001)
        self._save_counts()
    
    def get_count(self, file_path):
        return self.counts.get(file_path, 0)
    
    def get_all_counts(self):
        return self.counts.copy()
    
    def reset(self):
        self.counts = {}
        if os.path.exists(self.counter_file):
            os.remove(self.counter_file)