from pydantic import BaseModel


class SourceRef(BaseModel):
    page: int
    quote: str
    confidence: float  # 0.0 - 1.0
