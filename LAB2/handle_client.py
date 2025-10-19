from handle_request import handle_request
import threading

def handle_client(client_socket, client_address, base_dir, add_delay=True, delay_time=1.0):
    thread_name = threading.current_thread().name
    print(f"Handling connection from {client_address} — connection on {thread_name}")
    try:
        request_data = client_socket.recv(4096).decode('utf-8')
        if not request_data:
            client_socket.close()
            return

        response = handle_request(
            request_data,
            base_dir,
            add_delay=add_delay,
            delay_time=delay_time
        )

        client_socket.sendall(response)

    except Exception as e:
        print(f"Error handling client {request_number} on {thread_name}: {e}")
    finally:
        client_socket.close()