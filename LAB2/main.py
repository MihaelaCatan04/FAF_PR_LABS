import sys
from start_server import start_server


def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <directory> <port>")
        print("Example: python main.py ./my_website 8080")
        sys.exit(1)

    directory = sys.argv[1]
    port = int(sys.argv[2])

    start_server(directory, port, num_threads=10, delay_requests=True, delay_time=1.0)


if __name__ == "__main__":
    main()
