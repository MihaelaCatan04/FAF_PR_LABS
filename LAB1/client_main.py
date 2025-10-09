import sys
from start_server import start_server
from download_file import download_file

def main():
    if len(sys.argv) != 4:
        print("Usage: python client_main.py <host> <port> <filename>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    filename = sys.argv[3]
    
    save_dir = './downloads'
    
    download_file(host, port, filename, save_dir)

if __name__ == '__main__':
    main()