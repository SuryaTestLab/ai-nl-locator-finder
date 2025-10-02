import time
import threading
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlsplit

_driver_lock = threading.Lock()
_driver: Optional[webdriver.Chrome] = None
_last_url: Optional[str] = None  # <— track last navigated URL (normalized)

def _normalize(u: Optional[str]) -> Optional[str]:
    if not u: return None
    parts = urlsplit(u)
    # ignore fragment and trailing slash differences
    path = parts.path.rstrip("/")
    return f"{parts.scheme}://{parts.netloc}{path}{('?' + parts.query) if parts.query else ''}".lower()

def _get_driver() -> webdriver.Chrome:
    global _driver
    with _driver_lock:
        if _driver is not None:
            return _driver
        opts = Options()
        # opts.add_argument("--headless=new")  # keep commented to SEE the browser
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        _driver = webdriver.Chrome(options=opts)  # Selenium Manager resolves chromedriver
        _driver.set_page_load_timeout(45)
        return _driver

def load_and_get_dom(url: Optional[str], wait_selector: Optional[str], wait_ms: int, reuse: bool = True) -> str:
    """
    If reuse=True and we're already on the same normalized URL, DON'T navigate again.
    If url is None and driver exists, also DON'T navigate — just use current page.
    """
    global _last_url
    d = _get_driver()

    target = _normalize(url) if url else None
    current = _normalize(d.current_url) if d.current_url else None

    should_navigate = False
    if url:
        if not reuse:
            should_navigate = True
        elif target != current:
            should_navigate = True

    if should_navigate:
        d.get(url)
        _last_url = _normalize(url)
    else:
        # stay on current page
        # optional: no-op or soft refresh logic could go here if needed
        pass

    # best-effort settle
    if wait_selector:
        try:
            end = time.time() + 20
            while time.time() < end:
                found = d.execute_script("return document.querySelector(arguments[0]) != null", wait_selector)
                if found: break
                time.sleep(0.25)
        except Exception:
            pass

    if wait_ms and wait_ms > 0:
        time.sleep(min(wait_ms, 5000)/1000.0)

    return d.page_source

def highlight_in_page(xpath: Optional[str], css: Optional[str]) -> bool:
    d = _get_driver()
    js = r"""
    (function(xp, css){
      function byXPath(x){
        try{
          return document.evaluate(x, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }catch(e){ return null; }
      }
      function mark(el){
        if(!el) return false;
        try{ el.scrollIntoView({block:'center', inline:'center'}); }catch(e){}
        el.style.outline = '3px solid #6c8cff';
        el.style.background = 'rgba(108,140,255,.15)';
        return true;
      }
      var el = null;
      if(xp){ el = byXPath(xp); }
      if(!el && css){
        try{ el = document.querySelector(css); }catch(e){}
      }
      return mark(el);
    })(arguments[0], arguments[1]);
    """
    try:
        return bool(d.execute_script(js, xpath, css))
    except Exception:
        return False

def close_driver():
    global _driver, _last_url
    with _driver_lock:
        try:
            if _driver:
                _driver.quit()
        finally:
            _driver = None
            _last_url = None
