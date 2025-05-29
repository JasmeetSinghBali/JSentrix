import json
from datetime import datetime, date
from typing import Any, Type, TypeVar, Dict

# T can be any type unless its subclass of A2AMessageSerializable or itself as this generalized type is bounded to the same
T = TypeVar("T", bound="A2AMessageSerializable")

class A2AMessageSerializable:
    """
    Base class for robust agent-to-agent (A2A) message serialization.
    - Handles nested A2AMessageSerializable, lists, dicts, datetime, date, and bytes.
    - Use ONLY for A2A message passing between agents.
    """

    def to_dict(self) -> dict:
        """
        Convert object to dict
        """
        result = {}
        for key, value in self.__dict__.items():
            result[key] = self._serialize_value(value)
        return result

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        if isinstance(value, A2AMessageSerializable):
            return value.to_dict()
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, bytes):
            return value.decode("utf-8")
        elif isinstance(value, list):
            return [cls._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: cls._serialize_value(v) for k, v in value.items()}
        else:
            return value

    def to_json(self, **kwargs) -> str:
        """
        Convert dict to jsonstr
        """
        return json.dumps(self.to_dict(), sort_keys=True, indent=4, **kwargs)

    @classmethod
    def from_dict(cls: Type[T], d: Dict[str, Any]) -> T:
        """
        Create object/instance of A2AMessageSerializable or its subclass from dict unpacking keywork args
        """
        return cls(**d)

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """
        Create object/instance of  A2AMessageSerializable or its subclass from json string
        """
        return cls.from_dict(json.loads(json_str))
