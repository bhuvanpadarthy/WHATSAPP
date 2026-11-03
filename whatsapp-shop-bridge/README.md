# WhatsApp Cross-Platform Price Sync 🛍️📲

An automated cross-platform e-commerce comparison engine and Chrome Extension that detects what product you are searching for on **Amazon India, Flipkart, Meesho, or Myntra**, and automatically delivers price comparisons, star ratings, and direct deep links straight to your **WhatsApp**.

Includes a built-in **Live WhatsApp Web Simulator & Control Dashboard** (`http://localhost:8000`) so you can test the full end-to-end sync, the **"Allow All"** permission switch, and interactive WhatsApp chat controls even before setting up Meta WhatsApp Cloud API credentials.

---

## 🎯 How It Works

1. **One-Time "Allow All" Authorization:**
   The user enters their WhatsApp phone number and activates the **"Allow All Auto-Sync"** toggle inside the Browser Extension (or Web Dashboard).
2. **Instant Search Detection:**
   When searching for any item (e.g., *"office chair"*, *"wireless earbuds"*, *"sneakers"*) on Amazon, Flipkart, Meesho, or Myntra, the extension's content script intercepts the query with a 2.5s debounce.
3. **Cross-Platform Price Engine:**
   The query is sent to the FastAPI backend (`POST /trigger-search`). The backend verifies the user's `allow_all` permission, checks deduplication (60s cooldown per query to prevent spam), and fetches/generates comparison links, prices, discounts, and ratings across all 4 platforms.
4. **WhatsApp Delivery & Webhook Controls:**
   A formatted WhatsApp message is dispatched via Meta WhatsApp Cloud API (or logged directly to the local **Live WhatsApp Simulator** if credentials are not configured). If a user ever replies with **"STOP"**, auto-sync pauses immediately; replying with **"ALLOW ALL"** re-enables it.

---

## 📁 Project Architecture

```
whatsapp-shop-bridge/
├── backend/
│   ├── main.py            # FastAPI server, webhook handler, trigger-search API, live simulator endpoints
│   ├── database.py        # SQLite helper (shop_bridge.db) for user permissions and message logs
│   ├── scraper.py         # 4-platform link builder, category pricing engine, WhatsApp formatter
│   ├── static/
│   │   └── index.html     # Real-time Web Dashboard & WhatsApp Chat Simulator (at http://localhost:8000)
│   ├── .env.example       # Template for Meta WhatsApp Cloud API credentials
│   ├── .env               # Active environment file
│   └── requirements.txt   # FastAPI, Uvicorn, HTTPX, BeautifulSoup4, Pydantic, python-dotenv
├── extension/
│   ├── manifest.json      # Chrome Extension Manifest V3
│   ├── popup.html         # Modern UI with phone input & Allow-All toggle
│   ├── popup.js           # Local storage + backend /api/settings synchronization
│   ├── content.js         # Content script for Amazon, Flipkart, Meesho, Myntra + toast notifications
│   └── icon.png           # 128x128 extension icon
└── README.md              # Project documentation and setup guide
```

---

## 🚀 Quickstart: Running Backend & Web Simulator

### Step 1: Open Terminal in the Backend Folder
```bash
cd whatsapp-shop-bridge/backend
```

### Step 2: Create and Activate Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(Or on macOS / Linux: `python3 -m venv venv && source venv/bin/activate`)*

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Start the FastAPI Server
```bash
uvicorn main:app --reload --port 8000
```

### Step 5: Open the Live Simulator & Dashboard
Open your browser and navigate to:
```
http://localhost:8000
```
- **Left Panel:** Manage linked phone numbers, toggle **"Allow All"** ON/OFF, and trigger test searches with quick product chips.
- **Right Panel:** Live WhatsApp chat window that automatically polls and updates in real time with comparison messages, clickable platform links, and interactive `ALLOW ALL` / `STOP` action buttons!

---

## 🧩 Installing the Chrome Extension

1. Open Google Chrome (or Microsoft Edge / Brave) and navigate to:
   ```
   chrome://extensions/
   ```
2. Enable **"Developer mode"** in the top-right corner.
3. Click the **"Load unpacked"** button in the top-left corner.
4. Select the `whatsapp-shop-bridge/extension` directory.
5. Click the extension icon in your Chrome toolbar:
   - Verify your WhatsApp phone number (pre-filled with `919876543210` for testing).
   - Ensure **"Allow All Auto-Sync"** is switched **ON**.
   - Confirm the badge shows **"Connected"** (indicating `http://localhost:8000` is active).

---

## 🧪 Testing the Integration

### Scenario A: Testing in Browser on Supported Websites
1. Open any of the 4 supported sites:
   - [Amazon.in](https://www.amazon.in) (e.g. search *"Ergonomic Chair"*)
   - [Flipkart.com](https://www.flipkart.com) (e.g. search *"Wireless Earbuds"*)
   - [Meesho.com](https://www.meesho.com) (e.g. search *"Cotton T-Shirt"*)
   - [Myntra.com](https://www.myntra.com) (e.g. search *"Running Shoes"*)
2. Within 2.5 seconds, an animated floating toast notification appears in the bottom-right corner:
   ```
   📲 Allow All Active: Price Sync [WhatsApp]
   Sent "Ergonomic Chair" price comparison across Flipkart, Meesho & Myntra to your WhatsApp!
   [View in WhatsApp Simulator ↗]
   ```
3. Switch to `http://localhost:8000` to see the message waiting in your simulated WhatsApp inbox.

### Scenario B: Testing Directly from the Live Dashboard
1. Go to `http://localhost:8000`.
2. Under **"Test Cross-Platform Search"**, pick a preset (e.g. `🎧 Earbuds` or `👟 Sneakers`) or type your own query.
3. Click **"⚡ Trigger Cross-Platform Sync"**.
4. The comparison card appears in the chat simulator with verified direct links for Amazon, Flipkart, Meesho, and Myntra.

### Scenario C: Testing User Permissions ("STOP" & "ALLOW ALL")
1. In the WhatsApp chat simulator, click the **"🛑 STOP"** button (or type `"STOP"` and hit Enter).
2. The bot replies confirming that auto-sync is paused, and the "Allow All" toggle turns **OFF**.
3. Any searches conducted while paused will be blocked from sending messages.
4. Click **"✅ ALLOW ALL"** (or toggle it back ON in the extension popup) to immediately resume syncing!

---

## 📲 How to Receive Messages into Your Real / Original WhatsApp

You can receive price comparisons in your **real, physical WhatsApp** using any of the following 3 methods:

### Method 1: Instant 1-Click / Auto-Open WhatsApp Web (Zero Setup & Free)
- In the Chrome Extension popup, enter your WhatsApp number (e.g., `91XXXXXXXXXX`) and toggle **"Auto-Open Real WhatsApp"** ON.
- Now, when you search on **Amazon, Flipkart, Meesho, or Myntra**, a new tab opens directly in [WhatsApp Web](https://web.whatsapp.com) with the full 4-platform comparison message pre-filled to your personal chat!
- Alternatively, whenever the floating toast appears on shopping sites, click **"📲 Open in Real WhatsApp ↗"**.

### Method 2: Free Background Push via CallMeBot (Texts Your Phone in 10s!)
CallMeBot is a free API used to send WhatsApp messages directly to your personal phone without needing a business account:
1. Open WhatsApp on your phone and send:
   ```
   I allow callmebot to send me messages
   ```
   to **+34 941 83 14 06** (CallMeBot's official WhatsApp bot).
2. The bot will instantly reply with your personal `apikey`.
3. Open `whatsapp-shop-bridge/backend/.env` and paste:
   ```env
   CALLMEBOT_API_KEY=your_apikey_here
   ```
4. Now, every time you search for a product on Amazon, Flipkart, Meesho, or Myntra, the comparison is dispatched automatically to your physical phone's WhatsApp!

### Method 3: Official Meta WhatsApp Cloud API (For Business / Developers)
If you have a Meta Developer account:
1. Create a WhatsApp App in [Meta for Developers](https://developers.facebook.com/).
2. Obtain your **System User Access Token** and **Phone Number ID**.
3. Open `whatsapp-shop-bridge/backend/.env` and fill in:
   ```env
   WHATSAPP_TOKEN=EAABw...
   PHONE_NUMBER_ID=109876543210987
   VERIFY_TOKEN=shop_bridge_verify_token_2026
   PORT=8000
   ```
4. Dispatches will now go directly to physical phone numbers via Meta's Graph API.
   ```
4. Restart the FastAPI server. Dispatches will now go directly to physical phone numbers via Meta's Graph API, while continuing to display live in the Web Simulator!

---

## 🛡️ Key Features & Edge Case Handling

- **Deduplication:** Automatic 60-second cooldown per query to protect users from duplicate spam when navigating paginated results.
- **Graceful Scraper Fallback:** Deterministic category-based price intelligence model so comparisons are consistently realistic even when e-commerce platforms deploy anti-scraping Captcha walls.
- **Anti-CORS Architecture:** Full CORS authorization headers and manifest host permissions configured for seamless communication between extensions and backend.
- **Double-Sync Persistence:** User preferences are persisted simultaneously in `chrome.storage.local` and SQLite `shop_bridge.db`.

