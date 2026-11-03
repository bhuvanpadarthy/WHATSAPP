const BACKEND_URL = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", async () => {
  const phoneInput = document.getElementById("phoneInput");
  const allowAllToggle = document.getElementById("allowAllToggle");
  const saveBtn = document.getElementById("saveBtn");
  const openRealWaBtn = document.getElementById("openRealWaBtn");
  const openMetaConfigBtn = document.getElementById("openMetaConfigBtn");
  const connBadge = document.getElementById("connBadge");
  const connText = document.getElementById("connText");
  const metaStatusText = document.getElementById("metaStatusText");
  const toast = document.getElementById("toast");

  // 1. Load saved settings from Chrome local storage
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["phone", "allow_all"], (data) => {
      if (data.phone) {
        phoneInput.value = data.phone;
      }
      if (typeof data.allow_all === "boolean") {
        allowAllToggle.checked = data.allow_all;
      }
    });
  }

  // 2. Check Backend & Meta Health
  checkBackendHealth();

  async function checkBackendHealth() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/state`, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        const data = await res.json();
        connBadge.className = "status-badge status-online";
        connText.innerText = "Connected";

        if (data.meta_configured) {
          metaStatusText.innerHTML = '<span style="color: #5cf7c9;">● Connected</span>';
        } else {
          metaStatusText.innerHTML = '<span style="color: #f59e0b;">○ Setup Needed</span>';
        }

        if (data.meta_details && data.meta_details.target_phone && !phoneInput.value) {
          phoneInput.value = data.meta_details.target_phone;
        }
      } else {
        throw new Error("Bad status");
      }
    } catch (err) {
      connBadge.className = "status-badge status-offline";
      connText.innerText = "Backend Offline";
      metaStatusText.innerText = "Offline";
    }
  }

  // 3. Save Settings to both chrome.storage and backend API
  async function saveSettings() {
    const phone = phoneInput.value.trim() || "919876543210";
    const allow_all = allowAllToggle.checked;

    // Save locally in Chrome Storage
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ phone, allow_all });
    }

    // Sync with FastAPI backend
    try {
      saveBtn.innerText = "⏳ Saving...";
      saveBtn.disabled = true;

      const res = await fetch(`${BACKEND_URL}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, allow_all })
      });

      if (res.ok) {
        showToast("Settings saved & active!");
      } else {
        showToast("Saved locally (backend unreachable)");
      }
    } catch (err) {
      showToast("Saved locally (backend offline)");
    } finally {
      saveBtn.disabled = false;
      saveBtn.innerText = "💾 Save & Enable";
    }
  }

  function showToast(msg) {
    toast.innerText = msg;
    toast.style.display = "block";
    setTimeout(() => {
      toast.style.display = "none";
    }, 2800);
  }

  // Event Listeners
  saveBtn.addEventListener("click", saveSettings);
  allowAllToggle.addEventListener("change", saveSettings);

  // Open Real WhatsApp button
  openRealWaBtn.addEventListener("click", () => {
    const phone = phoneInput.value.trim() || "919876543210";
    const cleanPhone = phone.replace(/\D/g, "");
    const waUrl = `https://web.whatsapp.com/send?phone=${cleanPhone}`;
    if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.create) {
      chrome.tabs.create({ url: waUrl });
    } else {
      window.open(waUrl, "_blank");
    }
  });

  // Open Meta Facebook Config & Storage Dashboard
  openMetaConfigBtn.addEventListener("click", () => {
    if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.create) {
      chrome.tabs.create({ url: BACKEND_URL });
    } else {
      window.open(BACKEND_URL, "_blank");
    }
  });
});
