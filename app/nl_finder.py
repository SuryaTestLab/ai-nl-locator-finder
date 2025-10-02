# app/nl_finder.py
from bs4 import BeautifulSoup
from typing import Set, Tuple, Optional, List, Dict
import re

# ---------------- Tokenization & similarity ----------------

def tokens(s: str) -> Set[str]:
    if not s: return set()
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s.lower())
    return {t for t in s.split() if len(t) >= 2}

def char_ngrams(s: str, n: int = 3) -> Set[str]:
    s = re.sub(r"\s+", " ", (s or "").lower()).strip()
    if not s: return set()
    if len(s) <= n:
        return {s}
    return {s[i:i+n] for i in range(len(s)-n+1)}

def text_similarity(query: str, candidate: str) -> float:
    """Blend token Jaccard + trigram overlap; language-agnostic."""
    if not query or not candidate:
        return 0.0
    qt = tokens(query)
    ct = tokens(candidate)
    jacc = len(qt & ct) / max(1, len(qt | ct))

    qg = char_ngrams(query, 3)
    cg = char_ngrams(candidate, 3)
    tri = len(qg & cg) / max(1, len(qg | cg))

    return 0.6 * jacc + 0.4 * tri

# ---------------- Text extraction helpers ----------------

def visible_text(el) -> str:
    t = (el.get_text(separator=" ", strip=True) or "")
    return re.sub(r"\s+", " ", t)

def attr_text(el) -> str:
    parts = []
    for attr in ("id","name","aria-label","placeholder","title","value","role"):
        v = el.get(attr)
        if v: parts.append(str(v))
    cls = el.get("class") or []
    parts.extend(cls[:3])
    return " ".join(parts)

def ancestor_text(el, max_up: int = 3) -> str:
    cur = el.parent
    hops = 0
    parts = []
    while cur is not None and getattr(cur, "name", None) and hops < max_up:
        txt = visible_text(cur)
        if txt: parts.append(txt[:200])
        cur = cur.parent
        hops += 1
    return " ".join(parts)

def form_of(el):
    cur = el
    hops = 0
    while cur is not None and getattr(cur, "name", None) and hops < 10:
        if (cur.name or "").lower() == "form":
            return cur
        cur = cur.parent
        hops += 1
    return None

def form_has_password(f) -> bool:
    if not f: return False
    return bool(f.select("input[type=password]"))

def inputs_in_same_form(el) -> int:
    f = form_of(el)
    if not f: return 0
    return len(f.select("input,select,textarea"))

def form_text(f) -> str:
    if not f: return ""
    return visible_text(f)[:600]

# ---------------- Label association (learn from DOM) ----------------

def build_label_maps(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Return maps:
      - id_map[id] = label text  (from <label for="...">)
      - wrapped_map[node_id_str] = label text  (for inputs wrapped by <label>)
    We also support aria-labelledby via label_text_for().
    """
    id_map: Dict[str, str] = {}
    wrapped_map: Dict[str, str] = {}

    # for="id" mapping
    for lab in soup.find_all("label"):
        txt = visible_text(lab)
        for_id = lab.get("for")
        if for_id:
            id_map[for_id] = txt

        # wrapped: label > input|select|textarea
        for field in lab.find_all(["input","select","textarea"], recursive=True):
            wrapped_map[_node_identity(field)] = txt

    return {"by_id": id_map, "by_wrap": wrapped_map}

def _node_identity(el) -> str:
    # best-effort identity string (not used as selector, just a map key)
    return f"{el.name}:{el.get('id','')}:{el.get('name','')}:{'|'.join(el.get('class',[])[:2])}"

def label_text_for(el, label_maps: Dict[str, Dict[str, str]], soup: BeautifulSoup) -> str:
    """
    Resolve label text for a control via:
      1) <label for="id">
      2) <label> wrapping the control
      3) aria-labelledby references
    """
    # 1) for="id"
    id_ = el.get("id")
    if id_ and id_ in label_maps["by_id"]:
        return label_maps["by_id"][id_]

    # 2) wrapped
    key = _node_identity(el)
    if key in label_maps["by_wrap"]:
        return label_maps["by_wrap"][key]

    # 3) aria-labelledby
    aria_ids = (el.get("aria-labelledby") or "").strip()
    if aria_ids:
        text_parts = []
        for ref in aria_ids.split():
            ref_el = soup.find(id=ref)
            if ref_el:
                text_parts.append(visible_text(ref_el))
        if text_parts:
            return " ".join(text_parts)

    return ""

# ---------------- CSS & XPath builders ----------------

def best_css(el) -> str:
    """Prefer stable attribute-based CSS; fall back progressively."""
    if el.get("id"):
        return f"#{css_esc(el.get('id'))}"
    for attr in ("data-testid", "data-test", "data-qa"):
        if el.get(attr):
            return f"[{attr}='{css_esc(el.get(attr))}']"
    if el.get("name"):
        return f"[name='{css_esc(el.get('name'))}']"
    if el.get("aria-label"):
        return f"[aria-label='{css_esc(el.get('aria-label'))}']"
    if el.get("placeholder"):
        return f"[placeholder='{css_esc(el.get('placeholder'))}']"
    cls = (el.get("class") or [])
    if cls:
        return f"{el.name}.{css_esc(cls[0])}"
    return el.name

def css_esc(s: str) -> str:
    return (s or "").replace("\\","\\\\").replace("'","\\'").replace('"','\\"')

SECTION_TAGS = {"main","header","footer","nav","aside","section","article","form","dialog","table","thead","tbody","tfoot"}

def build_ref_xpath(el) -> str:
    anchor = _find_anchor(el)
    if anchor is None:
        step = _node_step(el, allow_text=True)
        if step: return f"//{step}"
        return _absolute_xpath(el)
    anchor_step = _anchor_step(anchor)
    path_steps = _down_steps(anchor, el)
    if path_steps:
        return f"{anchor_step}//" + "/".join(path_steps)
    el_step = _node_step(el, allow_text=True) or el.name
    return f"{anchor_step}//{el_step}"

def _find_anchor(el):
    cur = el; depth = 0
    while cur and getattr(cur, "name", None) and depth < 10:
        if _is_stable(cur) or cur.name in SECTION_TAGS:
            return cur
        cur = cur.parent; depth += 1
    return None

def _is_stable(n) -> bool:
    if not getattr(n, "attrs", None): return False
    if n.get("id"): return True
    for a in ("data-testid","data-test","data-qa"):
        if n.get(a): return True
    if n.get("role"): return True
    if n.get("aria-label"): return True
    return False

def _anchor_step(n) -> str:
    if n.get("id"): return f"//*[@id='{_xp_esc(n.get('id'))}']"
    for a in ("data-testid","data-test","data-qa"):
        if n.get(a): return f"//*[@{a}='{_xp_esc(n.get(a))}']"
    if n.get("aria-label"):
        v = n.get("aria-label"); return f"//*[{_contains_attr('aria-label', v)}]"
    if n.get("role"):
        v = n.get("role"); return f"//*[@role='{_xp_esc(v)}']"
    pred = _section_predicates(n); return f"//{n.name}{pred}"

def _section_predicates(n) -> str:
    preds = []
    for a in ("data-testid","data-test","data-qa"):
        if n.get(a): preds.append(f"@{a}='{_xp_esc(n.get(a))}'")
    cls = n.get("class") or []
    if cls: preds.append(f"contains(concat(' ', normalize-space(@class), ' '), ' {_xp_esc(cls[0])} ')")
    if n.get("role"): preds.append(f"@role='{_xp_esc(n.get('role'))}'")
    return "[" + " and ".join(preds) + "]" if preds else ""

def _down_steps(anchor, target) -> List[str]:
    steps = []; cur = target; chain = []
    while cur is not None and cur is not anchor and getattr(cur, "name", None):
        chain.append(cur); cur = cur.parent
    chain.reverse()
    for node in chain:
        step = _node_step(node, allow_text=(node is chain[-1]))
        if step is None: step = _indexed_step(node)
        steps.append(step)
    return steps

def _node_step(n, allow_text: bool) -> Optional[str]:
    preds = []
    if n.get("id"): preds.append(f"@id='{_xp_esc(n.get('id'))}'")
    for a in ("data-testid","data-test","data-qa"):
        if n.get(a): preds.append(f"@{a}='{_xp_esc(n.get(a))}'")
    if n.get("name"): preds.append(f"@name='{_xp_esc(n.get('name'))}'")
    if n.get("aria-label"): preds.append(_contains_attr('aria-label', n.get('aria-label')))
    if n.get("placeholder"): preds.append(_contains_attr('placeholder', n.get('placeholder')))
    if n.get("role"): preds.append(f"@role='{_xp_esc(n.get('role'))}'")
    if allow_text:
        text_val = (n.get_text(strip=True) or "")
        if text_val:
            short = text_val[:32]
            preds.append(f"contains(normalize-space(.), '{_xp_esc(short)}')")
    if preds: return f"{n.name}[" + " and ".join(preds) + "]"
    cls = n.get("class") or []
    if cls: return f"{n.name}[contains(concat(' ', normalize-space(@class), ' '), ' {_xp_esc(cls[0])} ')]"
    return f"{n.name}"

def _indexed_step(n) -> str:
    parent = n.parent
    if not parent or not getattr(parent, "find_all", None): return n.name
    same = [sib for sib in parent.find_all(n.name, recursive=False)]
    try:
        idx = same.index(n) + 1
        return f"{n.name}[{idx}]"
    except Exception:
        return n.name

def _contains_attr(attr: str, val: str) -> str:
    v = _xp_esc(val or ""); 
    if len(v) > 28: v = v[:28]
    return f"contains(@{attr}, '{v}')"

def _absolute_xpath(el) -> str:
    parts = []; cur = el
    while cur and getattr(cur, "name", None):
        same = [sib for sib in cur.parent.find_all(cur.name, recursive=False)] if cur.parent else [cur]
        idx = same.index(cur) + 1 if cur.parent else 1
        parts.insert(0, f"/{cur.name}[{idx}]"); cur = cur.parent
    return "".join(parts) if parts else "//*"

def _xp_esc(s: str) -> str:
    return (s or "").replace("'", "\\'")

# ---------------- Intent detection (generic) ----------------

def detect_intent(nl_query: str) -> dict:
    q = (nl_query or "").lower()
    # Field intent when user says enter/type/fill/set/put/etc.
    wants_field = bool(re.search(r"\b(type|enter|fill|set|input|write|provide|key in|paste)\b", q))
    return {"wants_field": wants_field}

# ---------------- Scoring (DOM-driven, label-aware) ----------------

def score_element(el, q_tokens: Set[str], nl_query: str, soup: BeautifulSoup, label_maps) -> Tuple[int, dict]:
    tag = (el.name or "").lower()
    role = (el.get("role") or "").lower()
    itype = (el.get("type") or "").lower()

    # texts
    t_visible = visible_text(el)
    t_attr    = attr_text(el)
    t_anc     = ancestor_text(el, max_up=3)
    t_label   = label_text_for(el, label_maps, soup)

    # similarities
    sim_self  = text_similarity(nl_query, f"{t_visible} {t_attr}")
    sim_ctx   = text_similarity(nl_query, t_anc)
    sim_label = text_similarity(nl_query, t_label)

    # form context
    f          = form_of(el)
    in_form    = 1 if f else 0
    has_pwd    = 1 if form_has_password(f) else 0
    form_txt   = form_text(f)
    sim_form   = text_similarity(nl_query, form_txt) if form_txt else 0.0
    inputs_cnt = inputs_in_same_form(el)

    # intent
    intent = detect_intent(nl_query)

    # element affordance classification
    is_text_field = (
        (tag == "input" and itype in {"", "text","email","password","search","tel","url","number"}) or
        (tag in {"textarea"}) or
        (role in {"textbox","combobox","spinbutton","searchbox"})
    )
    is_select = (tag == "select")
    is_clickable = (tag == "button") or (tag == "a") or (role in {"button","link"}) or (tag == "input" and itype in {"submit","button","reset"})

    score = 0

    # Base DOM/text signals
    score += int(420 * sim_self)             # own text/attrs
    score += int(220 * sim_ctx)              # ancestor/context
    score += int(340 * sim_label)            # associated label
    score += int(200 * sim_form)             # form text match

    if in_form: score += 40
    if has_pwd: score += 120                 # credential form often relevant
    score += min(90, 12 * inputs_cnt)        # richer forms get a small boost

    # Visibility proxy
    if t_visible: score += min(80, len(t_visible)//2)

    # Affordance (generic)
    if is_clickable: score += 30

    # -------- Strong intent gating for fields --------
    if intent["wants_field"]:
        if is_text_field or is_select:
            score += 240  # prefer actual fields
        else:
            # heavy penalty for buttons/links/etc. when user wants to enter text
            score -= 400

        # Additional boosts for field-like attributes
        if el.get("placeholder"):
            score += 60
        # name/id exact-ish nudge against query tokens (esp. "username", "email", etc.)
        name_id = (el.get("name","") + " " + el.get("id","")).lower()
        if name_id:
            score += int(160 * text_similarity(nl_query, name_id))

    # Build locators
    css = best_css(el)
    xpath = build_ref_xpath(el)

    return score, {
        "tag": tag,
        "text": t_visible[:160],
        "id": el.get("id",""),
        "name": el.get("name",""),
        "dataTestId": el.get("data-testid","") or el.get("data-test","") or el.get("data-qa",""),
        "ariaLabel": el.get("aria-label",""),
        "placeholder": el.get("placeholder",""),
        "role": el.get("role","") or "",
        "css": css,
        "xpath": xpath,
    }

# ---------------- Candidate selection & ranking ----------------

def find_locators(html: str, nl_query: str, base_url: str = "about:blank"):
    soup = BeautifulSoup(html, "lxml")
    label_maps = build_label_maps(soup)

    # Broad but focused candidate pool
    sel = ",".join([
        "button","a","input","select","textarea","label",
        "[role=button]","[role=link]","[role=switch]","[role=tab]","[role=textbox]","[role=combobox]",
        "[aria-label]","[data-testid]","[data-test]","[data-qa]","[placeholder]","[title]",
        "h1","h2","h3","h4","h5","h6"
    ])
    cand = soup.select(sel)

    q_tokens = tokens(nl_query)
    scored = []
    for idx, el in enumerate(cand):
        s, payload = score_element(el, q_tokens, nl_query, soup, label_maps)
        payload["nodeId"] = f"n{idx}"
        payload["score"] = int(s)
        scored.append(payload)

    scored.sort(key=lambda x: x["score"], reverse=True)

    best = scored[0] if scored else None
    return best, scored
