from pydantic import BaseModel


class RunConfig(BaseModel):
    model_name: str
    provider: str = 'mock'
    mode: str = 'policy'
    temperature: float = 0.0
    max_output_tokens: int = 1200
    timeout_seconds: int = 60
    max_retries: int = 1
    seed: int | None = None
    base_url: str | None = None
