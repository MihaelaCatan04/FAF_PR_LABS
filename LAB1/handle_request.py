import os
from constants import MIME_TYPES
from create_response import create_response
from get_content_type import get_content_type
from create_directory_listing import create_directory_listing
from urllib.parse import unquote

def handle_request(request_data, base_dir):
    try:
        request_line = request_data.split("\n")[0]
        method, path, version = request_line.split()

        print(f"Received request: {method} {path} {version}")

        path = unquote(path)
        

        if path == '/':
            path = ''
        else:
            path = path.lstrip('/')
        
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
        
        # If it's a directory, serve directory listing
        if os.path.isdir(file_path):
            url_path = '/' + path if path else '/'
            body = create_directory_listing(file_path, url_path, base_dir)
            return create_response(200, "OK", "text/html", body)
        
        # If it's a file, serve the file
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in MIME_TYPES:
                print(f"Unknown file type: {ext}")
                body = b"<h1>404 Not Found</h1><p>Unsupported file type.</p>"
                return create_response(404, "Not Found", "text/html", body)

            print(f"Serving file: {file_path}")
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            content_type = get_content_type(file_path)
            return create_response(200, "OK", content_type, file_content)
        body = b"<h1>404 Not Found</h1>"
        return create_response(404, "Not Found", "text/html", body)
    except Exception as e:
        print(f"Error handling request: {e}")
        body = b"<h1>500 Internal Server Error</h1>"
        return create_response(500, "Internal Server Error", "text/html", body)