# Lab 4: Single-Leader Replication (Semi-synchronous)

**Course:** Network Programming
**Student:** Mihaela Catan
**Group:** FAF-231

---

## Overview

This lab implements a simple single-leader replicated key-value store. The leader accepts client writes, stores them locally and replicates them concurrently to 5 follower replicas. Replication is semi-synchronous: the leader returns success to the client once a configurable number of follower acknowledgements (the write quorum) have been received. The leader simulates network lag by sleeping for a random delay in the range [MIN_DELAY, MAX_DELAY] (milliseconds) before sending each replicate request.

All services are implemented in Python + Flask and run in separate Docker containers orchestrated with `docker-compose`.

Key files and directories
- `leader/leader.py` — leader server (endpoints: `/write`, `/read`, `/get_all`, `/health`).
- `follower/follower.py` — follower server (endpoints: `/replicate`, `/read`, `/get_all`, `/health`).
- `leader/Dockerfile`, `follower/Dockerfile` — Docker build files.
- `docker-compose.yml` — compose orchestration for 1 leader + 5 followers.
- `test/test_replication.py` — integration and performance test harness (recreates cluster per-quorum, runs writes, collects latencies, plots results).
- `requirements.txt` — Python dependencies (flask, requests, matplotlib).

---

## How it works (quick)

- Client writes: POST /write {key, value} -> leader stores locally and concurrently POSTs `/replicate` to each follower.
- Leader waits until `WRITE_QUORUM` follower acknowledgements are observed, then returns success to the client (semi-synchronous behavior). Other follower replication requests continue in background.
- `MIN_DELAY` and `MAX_DELAY` control simulated per-follower network delay (ms), randomized per-replication request.

---

## Environment / Configuration (docker-compose)

All runtime configuration is provided from the `docker-compose.yml` environment blocks. The relevant env vars:

- `WRITE_QUORUM` — integer, number of follower confirmations required before leader returns success (default in compose: 3). Valid range: 1..5.
- `MIN_DELAY` / `MAX_DELAY` — integer milliseconds; leader sleeps a random value in this range before contacting each follower (default example: 0..1000 ms).
- `FOLLOWER_{N}_URL` — follower service URLs are set in compose and used by the leader to contact replicas.

Note: the `test/test_replication.py` script sets `WRITE_QUORUM` in its own `subprocess` calls when it recreates the cluster for each quorum value.

---

## How to run locally — using virtualenv + test harness

Prerequisites: Docker & docker-compose installed, Python 3.8+ and git.

1. Create and activate a Python virtual environment (PowerShell):

```powershell
python -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
.\.venv\Scripts\Activate.ps1
```

2. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the integration + performance test harness (this will bring up the cluster automatically if it is down):

```powershell
python -u .\test\test_replication.py
```

What the test does:
- Waits for the cluster (or starts it) and checks health endpoints.
- Runs a small basic write/read test and a concurrent-writes smoke test.
- For performance measurement it loops `WRITE_QUORUM` values 1..5. For each quorum it:
  - recreates the full cluster (docker-compose down && up --build -d) with the desired `WRITE_QUORUM` value;
  - runs 100 writes (10 concurrent writers) distributed across 10 keys;
  - collects per-write latencies and computes the average latency per quorum;
  - waits up to 10s for followers to converge, preferring full convergence but accepting quorum-level convergence; and
  - writes a plot `write_quorum_vs_latency.png` to the `LAB4` folder.

Notes:
- The script rebuilds the images when recreating the cluster. On slow machines this increases runtime.

---

## API (quick reference)

Leader (default port 5000)
- POST /write  — body: {"key":..., "value":...}  — returns 200 when write quorum met; response includes `replications` and `latency_ms`.
- GET /read?key=... — read value from leader.
- GET /get_all — returns full leader store snapshot.
- GET /health — health info (role, write_quorum, followers)

Follower (default ports 5001..5005)
- POST /replicate — used by the leader to replicate a key/value. Body: {"key":..., "value":...}.
- GET /read?key=... — read value from follower.
- GET /get_all — returns full follower store snapshot.
- GET /health — follower health.

---

## Expected behavior and explanation of results

- Latency vs Quorum: average write latency increases with the write quorum because the leader waits for the k-th fastest follower ack (the k-th order statistic) before returning. With IID uniform delays in [0,T], the expected k-th order statistic grows roughly linearly in k — so average latency vs quorum is close to linear for uniform delay. The test script plots the average latency per quorum in `write_quorum_vs_latency.png`.

- Replica consistency after the workload: with semi-synchronous replication the leader returns after `WRITE_QUORUM` acks; followers beyond the quorum may still be catching up. Therefore immediately after the workload it's normal that some followers don't have every key. The test waits up to 10s for eventual convergence; you can increase this timeout if your environment is slow.

---

