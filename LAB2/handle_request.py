import os
from rate_limiter.rate_limiter import RateLimiter
from constants import MIME_TYPES
from create_response import create_response
from get_content_type import get_content_type
from create_directory_listing import create_directory_listing
from urllib.parse import unquote
import time

rate_limiter = RateLimiter(max_requests_per_second=5)

def handle_request(request_data, base_dir, client_ip, add_delay=False, delay_time=1.0, request_counter=None):
    error_template = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{code} {title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 80vh;
            }}
            .error-container {{
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 600px;
            }}
            .error-code {{
                font-size: 72px;
                font-weight: bold;
                color: #007bff;
                margin: 0;
            }}
            h1 {{
                color: #333;
                margin: 20px 0;
                font-size: 32px;
            }}
            p {{
                color: #666;
                font-size: 16px;
                line-height: 1.6;
            }}
            a {{
                color: #007bff;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e9ecef;
                color: #999;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-code">{code}</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <p><a href="/">← Return to home</a></p>
            <div class="footer">Python HTTP File Server</div>
        </div>
    </body>
    </html>"""

    try:
        request_line = request_data.split("\n")[0]
        method, path, version = request_line.split()

        print(f"Received request: {method} {path} {version}")
        if not rate_limiter.is_allowed(client_ip):
            current_count = rate_limiter.get_status(client_ip)
            print(f"  ⛔ RATE LIMITED: {client_ip} ({current_count} requests in last 1s)")
            
            body = error_template.format(
                code=429,
                title="Too Many Requests",
                message="You are sending requests too quickly!",
                extra="""<div class="warning">
                    <strong>Rate Limit Exceeded:</strong> Maximum 5 requests per second per IP.
                    <br>Please wait a moment and try again.
                </div>"""
            ).encode('utf-8')
            return create_response(429, "Too Many Requests", "text/html", body)

        path = unquote(path)

        if path == "/":
            path = ""
        else:
            path = path.lstrip("/")

        file_path = os.path.join(base_dir, path)

        if add_delay:
            time.sleep(delay_time)

        # Security check: prevent directory traversal attacks
        # (stop people from requesting ../../../etc/passwd)
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_dir)):
            print("Security alert: Attempted directory traversal attack.")
            body = error_template.format(
                code=403,
                title="Forbidden",
                message="You don't have permission to access this resource.",
            ).encode("utf-8")
            return create_response(403, "Forbidden", "text/html", body)

        # Security check: check if file exists
        if not os.path.exists(file_path):
            print("Security alert: File not found.")
            body = error_template.format(
                code=404,
                title="Not Found",
                message="The requested resource could not be found on this server."
            ).encode("utf-8")
            return create_response(404, "Not Found", "text/html", body)

        # If it's a directory, serve directory listing
        if os.path.isdir(file_path):
            url_path = "/" + path if path else "/"
            if request_counter:
                request_path = '/' + path if path else '/'
                request_counter.increment(request_path)
            counts = request_counter.get_all_counts() if request_counter else {}
            body = create_directory_listing(file_path, url_path, base_dir, counts)
            return create_response(200, "OK", "text/html", body)

        # If it's a file, serve the file
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if request_counter:
                request_path = '/' + path if path else '/'
                request_counter.increment(request_path)
            counts = request_counter.get_all_counts() if request_counter else {}
            if ext not in MIME_TYPES:
                print(f"Unknown file type: {ext}")
                body = error_template.format(
                    code=404, title="Not Found", message="Unsupported file type."
                ).encode("utf-8")
                return create_response(404, "Not Found", "text/html", body)
            print(f"Serving file: {file_path}")
            with open(file_path, "rb") as f:
                file_content = f.read()

            content_type = get_content_type(file_path)
            return create_response(200, "OK", content_type, file_content)

        body = error_template.format(
            code=404,
            title="Not Found",
            message="The requested resource could not be found on this server."
        ).encode("utf-8")
        return create_response(404, "Not Found", "text/html", body)

    except Exception as e:
        print(f"Error handling request: {e}")
        body = error_template.format(
            code=500,
            title="Internal Server Error",
            message="An unexpected error occurred while processing your request."
        ).encode("utf-8")
        return create_response(500, "Internal Server Error", "text/html", body)
