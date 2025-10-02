from bs4 import BeautifulSoup

def highlight(html: str, node_id: str | None) -> str:
    soup = BeautifulSoup(html, "lxml")
    if not soup.body:
        return f"<!doctype html><html><head><meta charset='utf-8'></head><body>{html}</body></html>"
    count = 0
    for el in soup.body.find_all(True):
        el["data-nid"] = f"n{count}"
        count += 1
    if node_id:
        target = soup.select_one(f'[data-nid="{node_id}"]')
        if target:
            style = target.get("style","")
            style += "; outline: 3px solid #6c8cff; background: rgba(108,140,255,.15);"
            target["style"] = style
    body = str(soup.body)
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>"
