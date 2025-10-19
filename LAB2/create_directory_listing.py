import os
from urllib.parse import quote

from create_response import create_response


def create_directory_listing(directory_path, url_path, base_dir, request_counts=None):
    if request_counts is None:
        request_counts = {}

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
                        .container {{
                            max-width: 900px;
                            margin: 0 auto;
                            background: white;
                            padding: 30px;
                            border-radius: 10px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
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
                        .name {{
                            flex-grow: 1;
                        }}
                        .count {{
                            background: #667eea;
                            color: white;
                            padding: 5px 12px;
                            border-radius: 20px;
                            font-size: 12px;
                            font-weight: bold;
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
        html += (
            f'<li class="back"><a href="{parent_path}">← Parent Directory</a></li>\n'
        )

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

        file_request_path = item_url
        count = request_counts.get(file_request_path, 0)

        html += f"""        <li class="file">
                    <span class="name"><a href="{item_url}">{item}</a></span>
                    <span class="count">{count} requests</span>
                </li>\n"""

    html += """        </ul>
                    </div>
                </body>
                </html>
                """

    return html.encode("utf-8")
