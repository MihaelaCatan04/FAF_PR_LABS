from handle_request import handle_request
import threading
from counters.safe_counter import RequestCounterSafe

request_counter = RequestCounterSafe('request_counts_server.json')

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
            client_address[0],
            add_delay=add_delay,
            delay_time=delay_time,
            request_counter=request_counter
        )

        client_socket.sendall(response)

    except Exception as e:
        print(f"Error handling client on {thread_name}: {e}")
    finally:
        client_socket.close()