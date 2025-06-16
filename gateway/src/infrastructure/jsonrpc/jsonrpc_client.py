"""
gateway/src/infrastructure/jsonrpc/jsonrpc_client.py
Password hashing and verification using bcrypt.
"""

import httpx
import itertools
import asyncio


class JsonRpcClient:
    def __init__(self, url):
        self.url = url
        self._id_counter = itertools.count(1)

    async def call(self, method, params=None):
        rpc_id = next(self._id_counter)
        req = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": rpc_id}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.url, json=req, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise Exception(f"JSON-RPC error: {data['error']}")
            return data["result"]
