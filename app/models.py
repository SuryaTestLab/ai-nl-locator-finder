from pydantic import BaseModel
from typing import List, Optional

class LocateRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None
    query: str
    render: Optional[str] = "requests"   # "requests" | "chrome"
    wait_selector: Optional[str] = None  # only used in chrome mode
    wait_ms: Optional[int] = 1500        # extra settle time in chrome mode
    reuse: Optional[bool] = True         # reuse current Chrome page instead of reloading

class ElementScore(BaseModel):
    nodeId: str
    tag: str
    text: str
    id: str
    name: str
    dataTestId: str
    ariaLabel: str
    placeholder: str
    role: str
    css: str
    xpath: str
    score: int

class LocatorResult(BaseModel):
    query: str
    totalCandidates: int
    best: Optional[ElementScore] = None
    candidates: List[ElementScore] = []
    previewHtml: Optional[str] = None
