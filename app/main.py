from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import requests

from app.models import LocateRequest, LocatorResult, ElementScore
from app.nl_finder import find_locators
from app.html_highlighter import highlight
from app.browser_chrome import load_and_get_dom, highlight_in_page

app = FastAPI(title="NL Locator Finder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Filesystem-based mount (bullet-proof) ----------
BASE_DIR = Path(__file__).parent.resolve()          # .../nl-locator-finder-server/app
ASSETS_DIR = (BASE_DIR / "assets").resolve()        # .../nl-locator-finder-server/app/assets
INDEX_HTML = ASSETS_DIR / "index.html"

print(f"[startup] BASE_DIR   = {BASE_DIR}")
print(f"[startup] ASSETS_DIR = {ASSETS_DIR} (exists: {ASSETS_DIR.exists()})")
print(f"[startup] INDEX_HTML = {INDEX_HTML} (exists: {INDEX_HTML.exists()})")

# Serve assets at /assets/*
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR), html=False), name="assets")

# Optional: legacy redirect if your HTML still points to /static/*
from fastapi.responses import RedirectResponse
@app.get("/static/{path:path}")
def legacy_static(path: str):
    return RedirectResponse(url=f"/assets/{path}")

# Serve UI at root "/"
@app.get("/")
def serve_ui_root():
    if not INDEX_HTML.exists():
        return JSONResponse({"error": f"index.html not found at {INDEX_HTML}"}, status_code=500)
    return FileResponse(str(INDEX_HTML))

# ----------------------- API -----------------------
@app.post("/api/locate", response_model=LocatorResult)
async def locate(req: LocateRequest):
    html = req.html or ""
    render_mode = (req.render or "requests").lower()
    reuse = True if req.reuse is None else bool(req.reuse)

    if (not html) and req.url:
        if render_mode == "chrome":
            # Reuse current page if same URL (or if url omitted)
            html = load_and_get_dom(req.url, req.wait_selector, req.wait_ms or 1500, reuse=reuse)
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
            r = requests.get(req.url, headers=headers, timeout=25)
            r.raise_for_status()
            html = r.text

    if not html:
        # In Chrome mode, allow url to be omitted on subsequent queries — reuse current page
        if render_mode == "chrome":
            html = load_and_get_dom(None, req.wait_selector, req.wait_ms or 1500, reuse=True)
        if not html:
            return JSONResponse({"error": "Provide either url or html (or reuse Chrome page)."}, status_code=400)

    best, candidates = find_locators(html, req.query, req.url or "about:blank")

    if render_mode == "chrome":
        xp = best["xpath"] if best else None
        css = best["css"] if best else None
        highlight_in_page(xp, css)
        prev_html = "<!-- live highlight in persistent Chrome tab -->"
    else:
        prev_html = highlight(html, best["nodeId"] if best else None)

    best_model = ElementScore(**best) if best else None
    cand_models = [ElementScore(**c) for c in candidates[:10]]

    return LocatorResult(
        query=req.query,
        totalCandidates=len(candidates),
        best=best_model,
        candidates=cand_models,
        previewHtml=prev_html
    )

@app.get("/api/health")
def health():
    return {"ok": True}
