# Lab 1: HTTP File Server with TCP Sockets

**Course:** Network Programming  
**Student:** Mihaela Catan
**Group:** FAF-231

---

## Introduction

This lab implements a simple HTTP file server using raw TCP sockets in Python. The server's goals:
- Serve files from a directory specified on the command line
- Correctly serve HTML, PNG and PDF files (with proper Content-Type)
- Return a styled 404 page for missing files
- Provide an optional client script to fetch files and a directory listing generator for folders

This report documents the repository contents, Docker configuration, how to run the server and client, example requests (404, HTML, PDF, PNG), and the directory listing behavior.

---

## Served directory: `my_website/` (exact contents)

Root `my_website/` contains:

- `index.html` — front page (includes `<img src="cat.png">` and a link to `Tutorial.pdf`)
- `cat.png` — image used by `index.html`
- `Tutorial.pdf` — example PDF

Subdirectories:
- `HTTP Tutorials/`
  - `HTTP Basics.pdf`
  - `What is HTTP.pdf`
- `Networking Tutorials/`
  - `Networking.pdf`
  - `OSI Model.pdf`
- `Unknown Extensions/`
  - `cat.gif`

The full `index.html` is present in the repo and shows a simple HTML page with an embedded image and a download link for `Tutorial.pdf`.

---

## How to start the server

Run the server locally:

```bash
python main.py ./my_website 8080
```

Default (Dockerfile entrypoint + CMD):

```bash
python main.py ./my_website 8080
```

When starting the container you may override the arguments, for example to use a different directory.

---

## Client usage 

Client invocation pattern:

```bash
python client_main.py <host> <port> <url_path> <save_dir>
```

```bash
python client_main.py localhost 8080 index.html ./downloads
python client_main.py localhost 8080 Tutorial.pdf ./downloads
```

Behavior summary (implemented in `download_file.py` and `parse_response.py`):
- Connects to host:port via a TCP socket and sends a minimal HTTP/1.1 GET request.
- Reads the response bytes, splits headers and body using `\r\n\r\n`.
- If Content-Type contains `text/html`, the client prints the HTML body to stdout (decoded as UTF-8).
- If `application/pdf` or `image/png`, the client saves the body to the `save_dir` using the path basename.
- If the server returns 404, the client raises FileNotFoundError.

Saved files will appear in the `downloads/`.

---

## Example requests and expected results

These requests were chosen to exercise the server's behavior for not-found, text, PDF, and image responses.

1) Inexistent file (expected 404)

```
GET http://localhost:8080/no-such-file.txt
```

- Server returns a styled 404 HTML page (status 404). The client will raise `FileNotFoundError` when it sees status 404.

2) HTML file with image

```
GET http://localhost:8080/index.html
```

- Server returns `index.html` with `Content-Type: text/html`. Browser will then request `/cat.png` for the embedded image. The client prints the HTML body to the terminal.


3) PDF file

```
GET http://localhost:8080/Tutorial.pdf
```

- Server returns `application/pdf` and the client saves the file to `downloads\Tutorial.pdf`.

4) PNG file

```
GET http://localhost:8080/cat.png
```

- Server returns `image/png` and the client saves the file to `downloads\cat.png` (or the browser displays it inline).

---

## Directory listing behavior (when a folder is requested)

When a path corresponds to a directory the server calls `create_directory_listing`, which returns an HTML page listing contents:

- Shows directories first (with a folder icon / trailing slash) and files after (with a file icon).
- Provides clickable links for each item and a "Parent Directory" link when inside subfolders.
- Example generated snippet:

```html
<h1>Directory listing for /</h1>
<ul>
  <li class="dir"><a href="/HTTP%20Tutorials/">HTTP Tutorials/</a></li>
  <li class="dir"><a href="/Networking%20Tutorials/">Networking Tutorials/</a></li>
  <li class="dir"><a href="/Unknown%20Extensions/">Unknown Extensions/</a></li>
  <li class="file"><a href="/index.html">index.html</a></li>
  <li class="file"><a href="/cat.png">cat.png</a></li>
  <li class="file"><a href="/Tutorial.pdf">Tutorial.pdf</a></li>
</ul>
```

The listing HTML is styled and returned with `Content-Type: text/html` and status 200.

---

## Conclusion

This repository implements a minimal HTTP file server (TCP sockets) with a small client, directory-listing support, and Docker configuration for easy testing. The `Report.md` above documents how to run the server & client, the Docker setup, served directory contents, and expected behavior for 404, HTML, PDF and PNG requests.


