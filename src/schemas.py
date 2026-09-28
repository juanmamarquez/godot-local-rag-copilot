from pydantic import BaseModel
from typing import List, Optional

# Request models
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.0
    stream: Optional[bool] = False

# Response models
class Delta(BaseModel):
    content: Optional[str] = None
    role: Optional[str] = None

class ChoiceChunk(BaseModel):
    index: int
    delta: Delta
    finish_reason: Optional[str] = None

class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChoiceChunk]
