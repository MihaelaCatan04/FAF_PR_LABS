import os
from create_response import create_response
from get_content_type import get_content_type

def handle_request(request_data, base_dir):
    try:
        request_line = request_data.split("\n")[0]
        method, path, version = request_line.split()

        print(f"Received request: {method} {path} {version}")

        if path == "/":
            path = "/index.html"
        path = path.lstrip("/")

        file_path = os.path.join(base_dir, path)

        # Security check: prevent directory traversal attacks
        # (stop people from requesting ../../../etc/passwd)
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_dir)):
            print("Security alert: Attempted directory traversal attack.")
            body = b"<h1>403 Forbidden</h1>"
            return create_response(403, "Forbidden", "text/html", body)
        
        # Security check: check if file exists
        if not os.path.exists(file_path):
            print("Security alert: File not found.")
            body = b"<h1>404 Not Found</h1>"
            return create_response(404, "Not Found", "text/html", body)
        
        # Security check: check if it is a file
        if not os.path.isfile(file_path):
            print("Security alert: Not a file.")
            body = b"<h1>400 Bad Request</h1>"
            return create_response(400, "Bad Request", "text/html", body)
        
        # Security check: check if file is supported
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ['.html', '.pdf', '.png']:
            print("Security alert: Unsupported file type.")
            body = b"<h1>415 Unsupported Media Type</h1>"
            return create_response(415, "Unsupported Media Type", "text/html", body)
        
        print(f"Serving file: {file_path}")
        with open(file_path, 'rb') as f:
            body = f.read()

        content_type = get_content_type(file_path)
        return create_response(200, "OK", content_type, body)
    except Exception as e:
        print(f"Error handling request: {e}")
        body = b"<h1>500 Internal Server Error</h1>"
        return create_response(500, "Internal Server Error", "text/html", body)