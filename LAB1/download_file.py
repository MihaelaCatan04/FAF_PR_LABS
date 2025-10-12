import socket
import os
from parse_response import parse_response
def download_file(host, port, path, save_dir):

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect((host, port))
        
        if not path.startswith('/'):
            path = '/' + path
        
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"
        
        
        client_socket.sendall(request.encode('utf-8'))
        
        response_data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response_data += chunk
        
        
        status_code, headers, body = parse_response(response_data)
        
        if status_code == 404:
            raise FileNotFoundError(f"File not found: {path}")
        elif status_code != 200:
            raise ValueError(f"HTTP Error: {status_code}")
        
        content_type = headers.get('content-type', '')
        
        if 'text/html' in content_type:
            try:
                print(body.decode('utf-8'))
            except UnicodeDecodeError:
                print(body.decode('utf-8', errors='ignore'))
            print("="*60)
        
        elif 'application/pdf' in content_type or 'image/png' in content_type:
            filename = os.path.basename(path)
            if not filename:
                filename = 'downloaded_file'
            
            os.makedirs(save_dir, exist_ok=True)
            
            save_path = os.path.join(save_dir, filename)
            
            with open(save_path, 'wb') as f:
                f.write(body)
        
        else:
            raise ValueError(f"Unsupported Content-Type: {content_type}")
    except ConnectionRefusedError:
        raise ConnectionError(f"Could not connect to {host}:{port}")
    except Exception as e:
        raise e
    finally:
        client_socket.close()
