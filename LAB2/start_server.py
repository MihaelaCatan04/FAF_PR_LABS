import os
import socket
from handle_request import handle_request

def start_server(directory, port):
    if not os.path.isdir(directory):
        raise ValueError(f"The directory {directory} does not exist or is not a directory.")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen(5)
    print(f"Server started at port {port}, serving directory: {directory}")

    print(f"Server started!")
    print(f"Serving files from: {os.path.abspath(directory)}")
    print(f"Listening on: http://localhost:{port}")
    print(f"Press Ctrl+C to stop.")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")
            try:
                request_data = client_socket.recv(4096).decode('utf-8')
                if not request_data:
                    client_socket.close()
                    continue
                response = handle_request(request_data, directory)
                client_socket.sendall(response)
                client_socket.close()
            except Exception as e:
                print(f"Error handling client {client_address}: {e}")
                client_socket.close()
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        server_socket.close()