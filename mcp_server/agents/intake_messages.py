# mcp_server/agents/intake_messages.py

from .message_a2aserializer import A2AMessageSerializable


class IntakeInput(A2AMessageSerializable):
    """
    Describes the message input type for intake agent
    """

    def __init__(
        self, txn_id: str, amount: float, source: str = "faker", metadata: dict = None
    ):
        self.txn_id = txn_id
        self.amount = amount
        self.source = source
        self.metadata = metadata or {}


class IntakeOutput(A2AMessageSerializable):
    """
    Describes the message output type for intake agent
    """

    def __init__(self, enriched_txn: dict, prior_events: list):
        self.enriched_txn = enriched_txn
        self.prior_events = prior_events
