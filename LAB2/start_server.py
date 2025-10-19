from concurrent.futures import ThreadPoolExecutor
import os
import socket
from handle_client import handle_client


def start_server(directory, port, num_threads=10, delay_requests=False, delay_time=1.0):
    if not os.path.isdir(directory):
        raise ValueError(
            f"The directory {directory} does not exist or is not a directory."
        )

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen(5)
    print(f"Server started at port {port}, serving directory: {directory}")

    print(f"Server started!")
    print(f"Serving files from: {os.path.abspath(directory)}")
    print(f"Listening on: http://localhost:{port}")
    print(f"Press Ctrl+C to stop.")

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        try:
            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Connection from {client_address}")
                try:
                    executor.submit(
                    handle_client,
                    client_socket,
                    client_address,
                    directory,
                    delay_requests,
                    delay_time
                )
                except Exception as e:
                    print(f"Error handling client {client_address}: {e}")
                    client_socket.close()
        except KeyboardInterrupt:
            print("Shutting down server.")
        finally:
            server_socket.close()
