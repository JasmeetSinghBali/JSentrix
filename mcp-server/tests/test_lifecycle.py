import pytest
from utils.lifecycle import register_shutdown_callback, shutdown_all

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
