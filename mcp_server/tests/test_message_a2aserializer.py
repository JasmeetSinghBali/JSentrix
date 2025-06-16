"""
mcp_server/tests/test_message_a2aserializer.py

Requirements:
    - pytest

Run with:
    From inside mcp_server:
        pytest tests/test_message_a2aserializer.py
"""

from agents.message_a2aserializer import A2AMessageSerializable
from datetime import datetime, timezone


class AgentA2AMessage(A2AMessageSerializable):
    def __init__(
        self,
        sender,
        recipient,
        content,
        timestamp=None,
        msg_type="A2AMessage",
        version="1.0",
    ):
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.msg_type = msg_type
        self.version = version

    @classmethod
    def from_dict(cls, d):
        return cls(
            sender=d["sender"],
            recipient=d["recipient"],
            content=d["content"],
            timestamp=d.get("timestamp"),
            msg_type=d.get("msg_type", "A2AMessage"),
            version=d.get("version", "1.0"),
        )


def test_a2a_message_passing():
    # LangChain agent sends a message
    langchain_msg = AgentA2AMessage(
        sender="LangChainAgent",
        recipient="LlamaIndexAgent",
        content={"query": "Find compliance clauses about AML."},
    )
    json_payload = langchain_msg.to_json()
    print("LangChain → LlamaIndex JSON:", json_payload)

    # LlamaIndex agent receives and deserializes the message
    received_msg = AgentA2AMessage.from_json(json_payload)
    assert received_msg.sender == "LangChainAgent"
    assert received_msg.recipient == "LlamaIndexAgent"
    assert received_msg.content["query"] == "Find compliance clauses about AML."

    # LlamaIndex replies
    llamaindex_msg = AgentA2AMessage(
        sender="LlamaIndexAgent",
        recipient="LangChainAgent",
        content={"result": ["Clause1", "Clause2"], "status": "ok"},
    )
    reply_json = llamaindex_msg.to_json()
    print("LlamaIndex → LangChain JSON:", reply_json)

    # LangChain receives and deserializes
    reply_received = AgentA2AMessage.from_json(reply_json)
    assert reply_received.sender == "LlamaIndexAgent"
    assert reply_received.content["result"] == ["Clause1", "Clause2"]


if __name__ == "__main__":
    test_a2a_message_passing()
    print("A2A message passing test passed!")
