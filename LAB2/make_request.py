import time
import socket
def make_request(request_id, host, port, path='/'):
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        request = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        sock.sendall(request.encode('utf-8'))
        
        response = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        
        sock.close()
        
        duration = time.time() - start_time
        print(f"  Request {request_id}: Completed in {duration:.3f}s")
        return (request_id, duration, True)
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"  Request {request_id}: Failed in {duration:.3f}s - {e}")
        return (request_id, duration, False)