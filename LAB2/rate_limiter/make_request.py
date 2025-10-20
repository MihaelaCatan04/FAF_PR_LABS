
import socket

def make_request(request_id, host, port, path='/'):
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
        
        response_str = response.decode('utf-8', errors='ignore')
        status_line = response_str.split('\r\n')[0]
        status_code = int(status_line.split()[1])
        
        return (request_id, status_code)
        
    except Exception as e:
        return (request_id, 0)