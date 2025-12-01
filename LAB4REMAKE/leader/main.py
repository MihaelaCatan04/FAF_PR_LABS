import os
import asyncio
import random
import time
from typing import List

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI()

# In-memory key-value store with versioning
data_store = {}  # {key: {"value": value, "version": int}}

# Async locks
data_lock = asyncio.Lock()
version_lock = asyncio.Lock()

# Global version counter
version_counter = 0

# Configuration from environment
WRITE_QUORUM = int(os.environ.get("WRITE_QUORUM", "3"))
MIN_DELAY = int(os.environ.get("MIN_DELAY", "0"))
MAX_DELAY = int(os.environ.get("MAX_DELAY", "1000"))

# Follower URLs
FOLLOWERS: List[str] = []
for i in range(1, 6):
    url = os.environ.get(f"FOLLOWER_{i}_URL")
    if url:
        FOLLOWERS.append(url)

print("Leader started")
print(f"WRITE_QUORUM={WRITE_QUORUM}, DELAY=[{MIN_DELAY},{MAX_DELAY}]ms")
print(f"FOLLOWERS={FOLLOWERS}")

# Track pending replication tasks so tests can wait for them
pending_tasks = set()
pending_lock = asyncio.Lock()

# Track failed replications for retries
failed_replications = []  # list of (key, value, version, [follower_urls])
failed_lock = asyncio.Lock()

class WriteRequest(BaseModel):
    key: str
    value: str

# Attempt to replicate to a single follower. Returns True on success (200 or 409), False otherwise.
async def replicate_to_follower(follower_url: str, key: str, value: str, version: int, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            if attempt == 0:
                # Simulated leader-side network lag
                delay = random.randint(MIN_DELAY, MAX_DELAY) / 1000.0
                await asyncio.sleep(delay)

            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(
                    f"{follower_url}/replicate",
                    json={"key": key, "value": value, "version": version},
                )

            if r.status_code == 200:
                return True
            if r.status_code == 409:
                # stale write / conflict, treat as success for replication semantics
                return True
            # otherwise, treat as failure and retry
        except Exception:
            # backoff before retry
            await asyncio.sleep(0.1 * (attempt + 1))
    return False

# Replicate to all followers concurrently. Wait until WRITE_QUORUM confirmations then return.
# Remaining replications continue in background.
# Returns number of successful replications observed by the time of return.
async def replicate_to_followers(key: str, value: str, version: int) -> int:
    if not FOLLOWERS:
        return 0

    tasks = [asyncio.create_task(replicate_to_follower(f, key, value, version)) for f in FOLLOWERS]
    task_to_url = {t: u for t, u in zip(tasks, FOLLOWERS)}
    task_results = {}  # Track results to identify failed followers later
    results_lock = asyncio.Lock()  # Protect task_results from race conditions

    # Get current event loop for callbacks
    loop = asyncio.get_running_loop()

    # Register cleanup callbacks BEFORE adding to pending_tasks (prevents race condition)
    def make_cleanup_callback(task):
        def cleanup_callback(fut):
            # Use call_soon_threadsafe to safely schedule from callback
            loop.call_soon_threadsafe(lambda: asyncio.create_task(remove_task_from_pending(task)))
        return cleanup_callback
    
    # Register all callbacks first, then add to pending_tasks atomically
    for t in tasks:
        t.add_done_callback(make_cleanup_callback(t))
    
    # Now add all tasks to pending_tasks (callbacks are already registered)
    async with pending_lock:
        for t in tasks:
            pending_tasks.add(t)

    successful = 0
    quorum_met = False

    # Process tasks as they complete
    for fut in asyncio.as_completed(tasks):
        try:
            ok = await fut
        except Exception:
            ok = False

        # Store result with lock protection
        async with results_lock:
            task_results[fut] = ok
        
        if ok:
            successful += 1

        if successful >= WRITE_QUORUM and not quorum_met:
            quorum_met = True
            # quorum met; leave remaining tasks running in background
            break
    
    # If we broke early, identify failed followers from completed tasks only
    # Remaining tasks continue in background - no blocking wait
    if quorum_met:
        # Only check tasks that have already completed
        failed_followers = []
        async with results_lock:
            for t, url in task_to_url.items():
                # Only count as failed if task completed and returned False
                if t in task_results and not task_results[t]:
                    failed_followers.append(url)
        
        # Record failed replications for retry
        # Note: Tasks still running aren't counted as failures yet
        if failed_followers:
            async with failed_lock:
                failed_replications.append((key, value, version, failed_followers))

    return successful


# Helper to safely remove a completed task from pending_tasks
async def remove_task_from_pending(task):
    async with pending_lock:
        pending_tasks.discard(task)


@app.post("/write")
async def write(req: WriteRequest):
    global version_counter
    start = time.time()
    # assign ordered version
    async with version_lock:
        version_counter += 1
        version = version_counter

    # write locally
    async with data_lock:
        data_store[req.key] = {"value": req.value, "version": version}

    # replicate concurrently and wait for quorum
    successful = await replicate_to_followers(req.key, req.value, version)

    latency_ms = (time.time() - start) * 1000.0

    if successful >= WRITE_QUORUM:
        return {
            "status": "success",
            "key": req.key,
            "version": version,
            "replications": successful,
            "quorum": WRITE_QUORUM,
            "latency_ms": round(latency_ms, 2),
        }

    raise HTTPException(status_code=500, detail={
        "status": "failure",
        "message": "Write quorum not met",
        "replications": successful,
        "quorum": WRITE_QUORUM,
        "latency_ms": round(latency_ms, 2),
    })


@app.get("/read")
async def read(key: str):
    async with data_lock:
        v = data_store.get(key)
    if v is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": v["value"], "version": v["version"], "source": "leader"}


@app.get("/get_all")
async def get_all():
    async with data_lock:
        copy = dict(data_store)
    return {"data": copy, "source": "leader"}


@app.get("/health")
async def health():
    return {"status": "healthy", "role": "leader", "write_quorum": WRITE_QUORUM, "followers": len(FOLLOWERS)}


# Wait for all pending replication tasks and retry failed replications.
@app.get("/wait_for_replication")
async def wait_for_replication():
    total_completed = 0
    total_failed = 0
    iterations = 0
    max_iterations = 10  # Prevent infinite loops
    seen_tasks = set()  # Track tasks we've already processed to avoid double counting
    
    # Keep polling until pending_tasks is empty or we hit max iterations
    while iterations < max_iterations:
        iterations += 1
        
        # Atomically snapshot pending tasks
        async with pending_lock:
            tasks = [t for t in pending_tasks if t not in seen_tasks]
        
        # If no new tasks, we might be done
        if not tasks:
            if iterations > 1:  # Already checked at least once
                break
            # Wait a bit for any tasks that might be in flight
            await asyncio.sleep(0.1)
            continue
        
        # Mark these tasks as seen
        seen_tasks.update(tasks)
        
        # Wait for all new pending tasks to complete
        if tasks:
            # Use asyncio.gather to wait for all tasks, even if some fail
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    total_failed += 1
                elif result is True:
                    total_completed += 1
                else:
                    total_failed += 1
        
        # Tasks should have been removed by callbacks, but clean up any stragglers
        # This handles edge cases where callbacks haven't fired yet
        async with pending_lock:
            for t in tasks:
                if t.done():
                    pending_tasks.discard(t)
        
        # Small delay before checking again (allows callbacks to fire and new tasks to register)
        await asyncio.sleep(0.05)
    
    # Handle failed replications
    async with failed_lock:
        to_retry = list(failed_replications)
        failed_replications.clear()

    # Retry failed replications
    retry_success = 0
    retry_failed = 0
    for key, value, version, followers in to_retry:
        for f in followers:
            ok = await replicate_to_follower(f, key, value, version, max_retries=5)
            if ok:
                retry_success += 1
            else:
                retry_failed += 1

    # Final check of pending_tasks
    async with pending_lock:
        remaining = len(pending_tasks)

    return {
        "status": "complete", 
        "iterations": iterations,
        "unique_tasks_processed": len(seen_tasks), 
        "completed": total_completed, 
        "failed": total_failed, 
        "retry_success": retry_success, 
        "retry_failed": retry_failed,
        "remaining_pending": remaining
    }

