import sys
from download_file import download_file

def main():
    if len(sys.argv) != 5:
        print("Usage: python client_main.py <host> <port> <url_path> <save_dir>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    url_path = sys.argv[3]
    save_dir = sys.argv[4]

    download_file(host, port, url_path, save_dir)

if __name__ == '__main__':
    main()