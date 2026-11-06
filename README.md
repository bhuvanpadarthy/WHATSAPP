# WhatsApp Cross-Platform Price Sync 🛍️📲

An automated cross-platform e-commerce comparison engine and Chrome Extension that detects what product you are searching for on **Amazon India, Flipkart, Meesho, or Myntra**, and automatically delivers price comparisons, star ratings, and direct deep links straight to your **WhatsApp** via the official **Meta Facebook WhatsApp Business Cloud API**.

Includes a built-in **Meta Configuration & Ultra-Low Storage Dashboard** (`http://localhost:8000`).

---

## 📁 Repository Structure

```
├── .gitignore
├── README.md
└── whatsapp-shop-bridge/
    ├── backend/
    │   ├── main.py            # FastAPI server with Meta Cloud API & storage endpoints
    │   ├── database.py        # Ultra-low storage SQLite helper (auto-vacuum & pruning)
    │   ├── scraper.py         # 4-platform link builder & structured comparison engine
    │   ├── static/
    │   │   └── index.html     # Meta Facebook Account Manager & Storage Dashboard
    │   ├── .env.example       # Template for Meta WhatsApp credentials
    │   └── requirements.txt   # FastAPI, Uvicorn, HTTPX, BeautifulSoup4, Pydantic, python-dotenv
    ├── extension/
    │   ├── manifest.json      # Chrome Extension Manifest V3
    │   ├── popup.html         # Settings UI with Meta status & Allow-All toggle
    │   ├── popup.js           # Bidirectional sync between Chrome storage & backend
    │   ├── content.js         # Debounced query detector + non-intrusive floating toast
    │   └── icon.png           # 128x128 extension icon
    └── README.md              # Full documentation and walkthrough
```

---

## 🚀 Quickstart

### 1. Run the Backend Server
```bash
cd whatsapp-shop-bridge/backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Open **`http://localhost:8000`** to configure your Meta Facebook WhatsApp Business account credentials.

### 2. Load the Chrome Extension
1. Open `chrome://extensions/` in Google Chrome.
2. Toggle on **Developer mode**.
3. Click **Load unpacked** and select the folder:
   `whatsapp-shop-bridge/extension`

### 3. Search Any Product
Open **Amazon.in**, **Flipkart.com**, **Meesho.com**, or **Myntra.com** and search for any product (e.g., *"office chair"* or *"sneakers"*). Price and quality comparisons across all 4 platforms will be dispatched automatically to your WhatsApp!

