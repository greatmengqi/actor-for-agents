from typing import Any, Protocol
from dataclasses import dataclass

@dataclass
class Resources:
    backend: str

class ExecutionBackend(Protocol):
    async def spawn(self, *args: Any, **kwargs: Any) -> Any: ...
    async def stop(self, *args: Any, **kwargs: Any) -> Any: ...
