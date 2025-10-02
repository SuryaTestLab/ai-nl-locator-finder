# NL Locator Finder — Natural-Language → Robust CSS/XPath (Python server + optional Chrome render)

A tiny, practical tool that turns **natural language** like _“enter Surya in Username”_ or _“click Login button”_ into stable **CSS/XPath** locators. It learns from the **DOM** (labels, attributes, ancestor context, forms), prefers **relative XPaths**, and can optionally render in **Chrome** to highlight the element live without reloading the page between queries.

---

## ✨ Features

- **DOM-aware ranking** (no hard-coded keywords)
- **Intent awareness**: Understands when query implies typing vs clicking
- **Relative XPath preference**
- **Chrome render** (persistent tab, highlight without reload)
- **Export JSON** of locator candidates
- **Single-page UI** (no reload per query)

---

## 📦 Folder Structure

```
nl-locator-finder-server/
└─ app/
   ├─ main.py                # FastAPI entry
   ├─ models.py              # Pydantic request/response
   ├─ nl_finder.py           # Scoring + DOM parsing
   ├─ html_highlighter.py    # Static preview
   ├─ browser_chrome.py      # Selenium Chrome render
   └─ assets/
      ├─ index.html
      ├─ main.js
      └─ styles.css
```

---

## 🚀 Quick Start (Windows-friendly)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install fastapi uvicorn[standard] bs4 lxml selenium requests pydantic
uvicorn app.main:app --host 0.0.0.0 --port 7071
```

Then open http://localhost:7071/

---

## 🧠 How it Works

- Parses DOM (with BeautifulSoup / lxml)
- Tokenizes your query (`click`, `enter`, `checkbox`, etc.)
- Scores each element based on:
  - Tag type relevance
  - Matching visible text / placeholder / aria-label / id / name
  - Context (form labels, ancestor headers, fieldset legends)
  - Role attribute
  - Class names
- Generates CSS and relative XPath for each candidate

---

## 💡 Example Natural Language Queries

### 🔘 Buttons
```
click Login button
click Save button in Profile dialog
click Continue button next to Shipping Address
press Submit button
tap Add to Cart
click Remove button in Cart
```

### 🔗 Links
```
open Forgot password? link
click View details link in Order section
open link with aria-label Company Homepage
```

### 🧠 Text Inputs
```
enter Surya in Username
type user@example.com into Email field
set Username to qa_user
type in input with placeholder Search products
```

### 🔒 Passwords
```
enter password in Password field
fill Confirm Password with Secret123!
```

### 📝 Textareas
```
fill Description textarea with This is a test note
type feedback in Comments box
```

### 🔽 Selects / Dropdowns
```
choose United States from Country dropdown
select High in Priority combobox
pick June 2026 in Expiry Month
```

### ☑️ Checkboxes (including custom div/span)
```
check I agree to Terms
uncheck Receive marketing emails
enable Remember me checkbox
check custom checkbox with class a-checkbox
```

### 🔘 Radios
```
choose Credit Card payment
select Female in Gender
```

### 🔁 Toggles / Switches
```
enable Notifications toggle
disable Auto-renew switch
```

### 📅 Dates
```
set Start Date to 2025-10-15
pick next Friday in Delivery Date
set time to 14:30
```

### 🧱 Sections
```
in Profile section click Edit
inside Shipping card click Change
in Filters drawer apply Price Low to High
```

### 📦 Tables
```
click Edit in row #A-1042
select checkbox for user alice@example.com
open details where Status = Failed
```

### 🧩 Icons
```
click search icon
click trash icon in Documents row
```

### 📜 Pagination
```
click Next page
go to page 5
go to Last page
```

### 📁 File Upload
```
upload file in Resume uploader
click Choose File in Attachments
```

### 🧷 Attribute-Based
```
click [data-testid=primary-cta]
focus input[aria-label='Search site']
click button[title='Retry']
```

### 🌐 Multilingual
```
haz clic en Iniciar sesión
cliquez sur Continuer dans Profil
클릭 장바구니 담기 버튼
```

---

## 🧩 Chrome Rendering Mode

When enabled in UI (“Use Chrome”), backend opens one persistent Chrome tab:
- Loads page once (reuses it for next queries)
- Finds element
- Scrolls + outlines it in blue
- Returns updated DOM snapshot

Use this for **JS-heavy / dynamic** pages.

---

## 🧪 API Example

POST `/api/locate`
```json
{
  "url": "https://example.com/login",
  "query": "enter Surya in Username",
  "render": "chrome",
  "wait_selector": "#root",
  "reuse": true
}
```

Response
```json
{
  "query": "enter Surya in Username",
  "totalCandidates": 23,
  "best": {
    "tag": "input",
    "css": "#username",
    "xpath": "//*[@id='loginForm']//input[@id='username']",
    "score": 782
  }
}
```

---

## ⚙️ Troubleshooting

| Issue | Cause | Fix |
|-------|--------|------|
| UI reloads on Find | Button type missing | Ensure `<button type="button">` |
| Chrome reloads | Reuses URL | Remove URL on second run |
| CSS/XPath show %23 | URL-encoded | Use `textContent` in render |
| Element not found | Wrong intent | Include action: click/enter/check |
| Checkboxes missed | Non-semantic | Added `role`/class heuristics |

---

## 🔧 Export JSON

Click “Export JSON” → downloads `locator-candidates.json`:
```json
{
  "query": "click login button",
  "best": { "css": "#login", "xpath": "//button[@id='login']" },
  "candidates": [
    { "css": "#login", "xpath": "//button[@id='login']", "score": 742 }
  ]
}
```

---

## 📜 License

MIT (customize if needed)

---

## 🤝 Contributing

PRs welcome!
- Add more heuristics (custom widgets)
- Integrate local LLM reranker
- Add React UI variant
