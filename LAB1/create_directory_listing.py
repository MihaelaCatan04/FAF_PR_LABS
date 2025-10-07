import os
from create_response import create_response
from urllib.parse import quote, unquote


def create_directory_listing(directory_path, url_path, base_dir):
    try:
        items = os.listdir(directory_path)
    except PermissionError:
        body = b"<h1>403 Forbidden</h1>"
        return create_response(403, "Forbidden", "text/html", body)

    html = f"""<!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Directory listing for {url_path}</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            margin: 40px;
                            background-color: #f5f5f5;
                        }}
                        h1 {{
                            color: #333;
                            border-bottom: 2px solid #007bff;
                            padding-bottom: 10px;
                        }}
                        ul {{
                            list-style: none;
                            padding: 0;
                        }}
                        li {{
                            padding: 8px;
                            margin: 5px 0;
                            background: white;
                            border-radius: 4px;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        }}
                        a {{
                            text-decoration: none;
                            color: #007bff;
                            font-size: 16px;
                        }}
                        a:hover {{
                            text-decoration: underline;
                        }}
                        .dir {{
                            font-weight: bold;
                        }}
                        .dir:before {{
                            content: "📁 ";
                        }}
                        .file:before {{
                            content: "📄 ";
                        }}
                        .back {{
                            background: #e9ecef;
                        }}
                    </style>
                </head>
                <body>
                    <h1>Directory listing for {url_path}</h1>
                    <hr>
                    <ul>
                """
    if url_path != "/":
        parent_path = os.path.dirname(url_path.rstrip("/"))
        if not parent_path:
            parent_path = "/"
        html += f'<li class="back"><a href="{parent_path}">Parent Directory</a></li>\n'

    dirs = []
    files = []

    for item in sorted(items):
        item_path = os.path.join(directory_path, item)
        if os.path.isdir(item_path):
            dirs.append(item)
        else:
            files.append(item)

    for item in dirs:
        encoded_name = quote(item)
        item_url = f"{url_path.rstrip('/')}/{encoded_name}/"
        html += f'        <li class="dir"><a href="{item_url}">{item}/</a></li>\n'

    for item in files:
        encoded_name = quote(item)
        item_url = f"{url_path.rstrip('/')}/{encoded_name}"
        html += f'        <li class="file"><a href="{item_url}">{item}</a></li>\n'

    html += """    </ul>
                <hr>
                <p style="color: #666; font-size: 12px;">Python HTTP File Server</p>
            </body>
            </html>
            """

    return html.encode("utf-8")
