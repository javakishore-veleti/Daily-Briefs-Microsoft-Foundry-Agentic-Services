from pydantic import BaseModel

class WebSearchReq(BaseModel):
    def __init__(self, query: str = ""):
        self.query = query

class WebSearchResp(BaseModel):
    def __init__(self, results: list[str] = []):
        self.results = results

class WebSearchCtx(BaseModel):
    def __init__(self, req: WebSearchReq, resp: WebSearchResp):
        self.req = req
        self.resp = resp