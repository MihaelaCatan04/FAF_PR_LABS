import threading
import time
from collections import defaultdict

class RateLimiter:
    
    def __init__(self, max_requests_per_second=5):
        self.max_requests = max_requests_per_second
        
        # Dictionary: IP -> list of request timestamps
        # Example: {
        #   "192.168.1.100": [1234567.001, 1234567.051, 1234567.101],
        #   "192.168.1.101": [1234567.002, 1234567.052]
        # }
        self.request_times = defaultdict(list)
        
        self.lock = threading.Lock()
    
    def is_allowed(self, client_ip):
        with self.lock:  
            now = time.time()
            
            times = self.request_times[client_ip]
            
            times = [t for t in times if now - t < 1.0]
            self.request_times[client_ip] = times
            
            if len(times) >= self.max_requests:
                return False
            
            times.append(now)
            self.request_times[client_ip] = times
            
            return True
    
    def get_status(self, client_ip):

        with self.lock:
            now = time.time()
            times = self.request_times[client_ip]
            times = [t for t in times if now - t < 1.0]
            return len(times)
    
    def reset(self):
        with self.lock:
            self.request_times.clear()