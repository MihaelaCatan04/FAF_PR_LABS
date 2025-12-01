LAB4REMAKE — FastAPI single-leader replication lab

Contents
- `leader/` — FastAPI leader service (`main.py`)
- `follower/` — FastAPI follower service (`main.py`)
- `docker-compose.yml` — runs 1 leader + 5 followers
- `requirements.txt` — Python deps
- `test/test_replication.py` — integration + performance script

Prerequisites
- Docker and docker-compose installed and runnable from PowerShell
- Python 3.11 (to run the test script)

How it works (summary)
- Leader accepts writes only. It assigns a monotonically-increasing version to each write, stores locally, then replicates to all followers concurrently.
- Leader uses semi-synchronous replication: it waits until `WRITE_QUORUM` follower confirmations are received, then returns success to the client; remaining replications continue in background.
- Leader simulates per-follower network lag in the range `[MIN_DELAY, MAX_DELAY]` (milliseconds). Configure via docker-compose environment variables.

Run the cluster (PowerShell)

```powershell
cd 'c:\Users\mihae\OneDrive\Desktop\FAF_PR_LABS\LAB4REMAKE'
docker compose up --build -d

```

Run the integration test (will restart compose for each quorum value)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt


.\.venv\Scripts\python.exe .\test\test_replication.py
```

Notes
- The test script varies `WRITE_QUORUM` from 1..5, makes ~100 writes (10 at a time), records latencies, and saves `write_quorum_vs_latency.png` in the current directory.
