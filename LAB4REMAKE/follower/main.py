import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# In-memory key-value store
data_store = {}
data_lock = asyncio.Lock()

FOLLOWER_ID = os.environ.get("FOLLOWER_ID", "follower-unknown")

class ReplicateRequest(BaseModel):
    key: str
    value: str
    version: int


@app.post("/replicate")
async def replicate(req: ReplicateRequest):
    # Accept if new version is greater than current
    async with data_lock:
        existing = data_store.get(req.key)
        if existing is None or req.version > existing["version"]:
            data_store[req.key] = {"value": req.value, "version": req.version}
            return {"status": "success", "follower_id": FOLLOWER_ID, "key": req.key, "version": req.version}
        else:
            raise HTTPException(status_code=409, detail={"status": "conflict", "reason": "stale_version", "current_version": existing["version"]})


@app.get("/read")
async def read(key: str):
    async with data_lock:
        v = data_store.get(key)
    if v is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": v["value"], "version": v["version"], "follower_id": FOLLOWER_ID}


@app.get("/get_all")
async def get_all():
    async with data_lock:
        copy = dict(data_store)
    return {"data": copy, "follower_id": FOLLOWER_ID}


@app.get("/health")
async def health():
    return {"status": "healthy", "follower_id": FOLLOWER_ID}
