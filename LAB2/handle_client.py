from handle_request import handle_request
import threading
from counters.safe_counter import RequestCounterSafe
from record_and_print import record_and_print

request_counter = RequestCounterSafe('request_counts_server.json')



def handle_client(client_socket, client_address, base_dir, add_delay=True, delay_time=1.0):
    thread_name = threading.current_thread().name
    client_ip = client_address[0]
    print(f"Handling connection from {client_address} — connection on {thread_name}")
    try:
        request_data = client_socket.recv(4096).decode('utf-8')
        if not request_data:
            client_socket.close()
            return

        response = handle_request(
            request_data,
            base_dir,
            client_ip,
            add_delay=add_delay,
            delay_time=delay_time,
            request_counter=request_counter
        )

        status_code = 0
        try:
            resp_str = response.decode('utf-8', errors='ignore')
            status_line = resp_str.split('\r\n', 1)[0]
            parts = status_line.split()
            if len(parts) >= 2:
                status_code = int(parts[1])
        except Exception:
            status_code = 0

        client_socket.sendall(response)

        record_and_print(client_ip, status_code == 200)

    except Exception as e:
        print(f"Error handling client on {thread_name}: {e}")
    finally:
        client_socket.close()