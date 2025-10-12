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

## Dockerfile and docker-compose.yaml

The `Dockerfile` contains:

```bash
FROM python:3.11-slim

WORKDIR /app

COPY . .

EXPOSE 8080

# ENTRYPOINT ["python", "main.py"]
# CMD ["./my_website", "8080"]
```

The `docker-compose.yaml` file contains:

```bash
version: "3.8"

services:
  web:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./my_website:/app/my_website
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    entrypoint: ["tail", "-f", "/dev/null"]
    tty: true
    stdin_open: true

  client:
    build: .
    entrypoint: ["tail", "-f", "/dev/null"]
    depends_on:
      - web
    volumes:
      - ./downloads:/app/downloads
    tty: true
    stdin_open: true
```


## How to start the server

Run the server locally:

```bash
python main.py ./my_website 8080
```

Default:

```bash
docker compose up -d
docker compose exec web sh
python /app/main.py /app/my_website 8080
```
The  ``` docker compose build ``` command should be run first if the container doesn't exist yet.
<img width="653" height="201" alt="image" src="https://github.com/user-attachments/assets/bbe974a4-ff45-4d1f-8959-a65f9156c73a" />

<img width="402" height="263" alt="image" src="https://github.com/user-attachments/assets/bd011eb3-86db-4973-af3e-5411a310ad01" />

---

## Client usage 

Client invocation pattern:

```bash
python client_main.py <host> <port> <url_path> <save_dir>
```

```bash
python client_main.py localhost 8080 /index.html ./downloads
python client_main.py localhost 8080 /Tutorial.pdf ./downloads
```
<img width="460" height="488" alt="image" src="https://github.com/user-attachments/assets/72d21c90-7e0f-4eac-ac76-60aabe355900" />

Default (Docker compose):

```bash
docker compose up -d
docker compose exec client sh
python client_main.py web 8080 /cat.png /app/downloads
```
<img width="464" height="75" alt="image" src="https://github.com/user-attachments/assets/739488cd-87de-4d43-85bb-eebd92471831" />

<img width="239" height="30" alt="image" src="https://github.com/user-attachments/assets/c43b742b-f54b-4b1d-888a-53436a87ead2" />

<img width="746" height="56" alt="image" src="https://github.com/user-attachments/assets/eb9491a5-5f02-45ca-b6a9-ab24f7994643" />

<img width="404" height="226" alt="image" src="https://github.com/user-attachments/assets/a4bd6dbc-0cf6-4a5c-bb8f-b3ce4975cc25" />

<img width="243" height="29" alt="image" src="https://github.com/user-attachments/assets/40149875-f64d-463c-8da2-403a5a6869cd" />

<img width="452" height="268" alt="image" src="https://github.com/user-attachments/assets/6b580a0a-bf07-4094-adb0-5dbeabe61c5c" />

<img width="296" height="31" alt="image" src="https://github.com/user-attachments/assets/60764013-0475-44e3-a21c-b5b40cd460c8" />

<img width="373" height="155" alt="image" src="https://github.com/user-attachments/assets/ccf66eb2-b375-4d43-ac12-10dd0266df2e" />

<img width="283" height="35" alt="image" src="https://github.com/user-attachments/assets/ac185538-bc9f-4f1b-824d-7689781cb34f" />

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
<img width="576" height="456" alt="image" src="https://github.com/user-attachments/assets/f63be28e-f708-44d4-8bb7-14d22daf7431" />


2) HTML file with image

```
GET http://localhost:8080/index.html
```

- Server returns `index.html` with `Content-Type: text/html`. Browser will then request `/cat.png` for the embedded image. The client prints the HTML body to the terminal.
<img width="708" height="617" alt="image" src="https://github.com/user-attachments/assets/33dbccdc-ddfe-42b0-ab0c-1926c2d82293" />


3) PDF file

```
GET http://localhost:8080/Tutorial.pdf
```
<img width="1280" height="649" alt="image" src="https://github.com/user-attachments/assets/9d307747-3602-4249-98bf-43b744a58ed0" />


- Server returns `application/pdf` and the client saves the file to `downloads\Tutorial.pdf`.

4) PNG file

```
GET http://localhost:8080/cat.png
```

- Server returns `image/png` and the client saves the file to `downloads\cat.png` (or the browser displays it inline).
<img width="1278" height="655" alt="image" src="https://github.com/user-attachments/assets/21138b8e-f6c0-439a-a470-85aa2dd2f422" />

---

## Directory listing behavior (when a folder is requested)

When a path corresponds to a directory the server calls `create_directory_listing`, which returns an HTML page listing contents:

- Shows directories first (with a folder icon / trailing slash) and files after (with a file icon).
- Provides clickable links for each item and a "Parent Directory" link when inside subfolders.

The listing HTML is styled and returned with `Content-Type: text/html` and status 200.
<img width="1280" height="616" alt="image" src="https://github.com/user-attachments/assets/8a2fd57e-c764-4230-a2f1-473c722a672d" />

<img width="1280" height="620" alt="image" src="https://github.com/user-attachments/assets/e8685133-49b7-4045-9336-ab89f3ead8b0" />

---

## Conclusion

This repository implements a minimal HTTP file server (TCP sockets) with a small client, directory-listing support, and Docker configuration for easy testing. The `Report.md` above documents how to run the server & client, the Docker setup, served directory contents, and expected behavior for 404, HTML, PDF and PNG requests.


