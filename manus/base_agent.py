from abc import ABC
from typing import Any, List, Tuple
import asyncio


# Decorators and Base Classes
def describe_class(description):
    def decorator(cls):
        cls.__description__ = description
        return cls
    return decorator


class BaseAgent(ABC):
    def __init__(self, **kwargs):
        pass

    def invoke(self, query: str, **kwargs) -> Any:
        """Invoke the agent and return the result."""
        pass


class RAGAgent(BaseAgent):
    def __init__(self, **kwargs):
        pass

    def retrieve(self, query: str, **kwargs) -> List:
        """Retrieve document results from the knowledge base."""
        pass

    def query(self, query: str, **kwargs) -> Tuple[str, List]:
        """Query the agent and return the answer and retrieved documents."""
        pass