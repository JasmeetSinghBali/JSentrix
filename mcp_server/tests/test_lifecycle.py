"""
tests/test_lifecycle.py

Unit tests for utils.lifecycle shutdown callback utilities.

- No database or server needs to be running for these tests.
- Purely tests in-memory callback logic (sync and async).
- To run: pytest tests/test_lifecycle.py inside mcp_server activated venv

Requires:
    pytest
    pytest-asyncio

Install with:
    pip install pytest pytest-asyncio
"""

import pytest
import asyncio
from utils.lifecycle import (
    register_shutdown_callback,
    shutdown_all,
    async_shutdown_all,
    reset_shutdown_callbacks,
)


def setup_function():
    # Reset callbacks before each test for isolation
    reset_shutdown_callbacks()


def test_shutdown_callbacks_are_called(monkeypatch):
    called = []

    def cb1():
        called.append("cb1")

    def cb2():
        called.append("cb2")

    register_shutdown_callback(cb1)
    register_shutdown_callback(cb2)

    shutdown_all()

    assert "cb1" in called, "Callback 1 was not called"
    assert "cb2" in called, "Callback 2 was not called"


def test_shutdown_callbacks_handle_exceptions(caplog):
    called = []

    def good_cb():
        called.append("good")

    def bad_cb():
        raise RuntimeError("fail")

    register_shutdown_callback(bad_cb)
    register_shutdown_callback(good_cb)

    shutdown_all()

    assert "good" in called, "Good callback was not called"
    # Check that the error was logged
    assert any("Error during shutdown" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_async_shutdown_callbacks_are_called():
    called = []

    def sync_cb():
        called.append("sync")

    async def async_cb():
        await asyncio.sleep(0.01)
        called.append("async")

    register_shutdown_callback(sync_cb)
    register_shutdown_callback(async_cb)

    await async_shutdown_all()

    assert "sync" in called, "Sync callback was not called"
    assert "async" in called, "Async callback was not called"


@pytest.mark.asyncio
async def test_async_shutdown_callbacks_handle_exceptions(caplog):
    called = []

    async def bad_async_cb():
        raise RuntimeError("fail_async")

    async def good_async_cb():
        called.append("good_async")

    register_shutdown_callback(bad_async_cb)
    register_shutdown_callback(good_async_cb)

    await async_shutdown_all()

    assert "good_async" in called, "Good async callback was not called"
    assert any("Error during shutdown" in rec.message for rec in caplog.records)
