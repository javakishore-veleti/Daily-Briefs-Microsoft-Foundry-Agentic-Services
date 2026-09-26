from uuid import uuid4

from pydantic import BaseModel, Field

class WebSearchReq(BaseModel):
    query: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))

    def __init__(self, query: str = "", session_id: str | None = None):
        super().__init__(
            query=query,
            session_id=session_id if session_id is not None else str(uuid4()),
        )

class WebSearchResp(BaseModel):
    def __init__(self, results: list[str] = []):
        self.results = results

class WebSearchCtx(BaseModel):
    def __init__(self, req: WebSearchReq, resp: WebSearchResp):
        self.req = req
        self.resp = resp