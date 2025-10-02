# NL Locator Finder — Natural-Language → Robust CSS/XPath (Python server + optional Chrome render)

A tiny, practical tool that turns **natural language** like _“enter Surya in Username”_ or _“click Login button”_ into stable **CSS/XPath** locators. It learns from the **DOM** (labels, attributes, ancestor context, forms), prefers **relative XPaths**, and can optionally render in **Chrome** to highlight the element live without reloading the page between queries.

## ✨ Features
- DOM-aware ranking, no hardcoded hints
- Field vs Click intent detection
- Reference XPaths first (anchor-based)
- Chrome rendering and highlight (persistent tab)
- JSON Export
- No reload single-page UI

## 📦 Folder Structure
```
nl-locator-finder-server/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── nl_finder.py
│   ├── html_highlighter.py
│   ├── browser_chrome.py
│   └── assets/
│       ├── index.html
│       ├── styles.css
│       └── main.js
```
(see full Git version for detailed README)
