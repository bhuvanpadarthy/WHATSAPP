/**
 * WhatsApp Cross-Platform Price Sync Content Script
 * Injected into Amazon.in, Flipkart.com, Meesho.com, and Myntra.com.
 * Detects product search queries, checks 'Allow All' status,
 * triggers FastAPI backend, and shows a non-intrusive floating toast.
 */

(() => {
  const BACKEND_URL = "http://localhost:8000";
  let lastProcessedQuery = "";
  let debounceTimer = null;

  function identifyCurrentSite() {
    const host = window.location.hostname.toLowerCase();
    if (host.includes("amazon.in")) return "Amazon.in";
    if (host.includes("flipkart.com")) return "Flipkart.com";
    if (host.includes("meesho.com")) return "Meesho.com";
    if (host.includes("myntra.com")) return "Myntra.com";
    return "E-Commerce Site";
  }

  function extractSearchQuery() {
    const url = new URL(window.location.href);
    const host = window.location.hostname.toLowerCase();
    let query = "";

    // 1. Amazon India
    if (host.includes("amazon.in")) {
      query = url.searchParams.get("k") || url.searchParams.get("field-keywords") || "";
      if (!query) {
        const input = document.querySelector("#twotabsearchtextbox");
        if (input && input.value) query = input.value;
      }
    }
    // 2. Flipkart
    else if (host.includes("flipkart.com")) {
      query = url.searchParams.get("q") || "";
      if (!query) {
        const input = document.querySelector("input[name='q']");
        if (input && input.value) query = input.value;
      }
    }
    // 3. Meesho
    else if (host.includes("meesho.com")) {
      query = url.searchParams.get("q") || "";
      if (!query) {
        const input = document.querySelector("input[placeholder*='Search']");
        if (input && input.value) query = input.value;
      }
    }
    // 4. Myntra
    else if (host.includes("myntra.com")) {
      query = url.searchParams.get("q") || url.searchParams.get("rawQuery") || "";
      if (!query) {
        const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
        const ignorePaths = ["checkout", "login", "register", "cart", "wishlist", "my", "shop"];
        if (path && !ignorePaths.includes(path.toLowerCase()) && !path.includes("/")) {
          query = decodeURIComponent(path.replace(/-/g, " "));
        }
      }
      if (!query) {
        const input = document.querySelector(".desktop-searchBar, input[placeholder*='Search']");
        if (input && input.value) query = input.value;
      }
    }

    return query ? query.trim() : "";
  }

  function triggerPriceSync(query) {
    if (!query || query.length < 2) return;
    if (query.toLowerCase() === lastProcessedQuery.toLowerCase()) return;

    // Check user settings from Chrome storage
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.get(["phone", "allow_all", "auto_open_whatsapp"], (data) => {
        const allowAll = data.allow_all !== false; // Default true
        const phone = data.phone || "919876543210";
        const autoOpen = !!data.auto_open_whatsapp;

        if (!allowAll) {
          console.log("[PriceSync] 'Allow All' is disabled. Skipping WhatsApp dispatch.");
          return;
        }

        lastProcessedQuery = query;
        dispatchSearchToBackend(phone, query, autoOpen);
      });
    } else {
      // Direct fallback if storage API not ready
      lastProcessedQuery = query;
      dispatchSearchToBackend("919876543210", query, false);
    }
  }

  async function dispatchSearchToBackend(phone, query, autoOpen) {
    const currentSite = identifyCurrentSite();

    try {
      console.log(`[PriceSync] Sending search '${query}' from ${currentSite} to backend...`);
      const res = await fetch(`${BACKEND_URL}/trigger-search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: phone,
          query: query,
          current_site: currentSite
        })
      });

      if (!res.ok) return;
      const data = await res.json();

      if (data.status === "success") {
        showToastNotification(query, currentSite, data);

        // Auto-open in real WhatsApp if user enabled that setting
        if (autoOpen && data.whatsapp_web_url) {
          window.open(data.whatsapp_web_url, "_blank");
        }
      } else if (data.status === "deduplicated") {
        console.log("[PriceSync] Query deduplicated:", data.message);
      }
    } catch (err) {
      console.warn("[PriceSync] Backend is offline or unreachable at http://localhost:8000:", err.message);
    }
  }

  function showToastNotification(query, sourceSite, data) {
    // Remove existing toast if any
    const existing = document.getElementById("wa-price-sync-toast");
    if (existing) existing.remove();

    const otherPlatforms = ["Amazon", "Flipkart", "Meesho", "Myntra"]
      .filter(p => !sourceSite.toLowerCase().includes(p.toLowerCase()))
      .slice(0, 3)
      .join(", ");

    const waWebUrl = data.whatsapp_web_url || `https://web.whatsapp.com/send?text=${encodeURIComponent(data.whatsapp_preview || query)}`;
    const deliveryText = data.delivery_status || "Dispatched";
    const winnerText = (data.summary && data.summary.winner_platform) 
      ? `🏆 Best Deal: ${data.summary.winner_platform} at ${data.summary.lowest_price}`
      : `Comparison found across 4 platforms`;

    const toast = document.createElement("div");
    toast.id = "wa-price-sync-toast";
    toast.innerHTML = `
      <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <div style="background: #25D366; width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0;">
            📲
          </div>
          <div>
            <div style="font-weight: 700; font-size: 13px; color: #e9edef; display: flex; align-items: center; gap: 6px;">
              <span>Meta WhatsApp Price Sync</span>
              <span style="background: rgba(8, 102, 255, 0.25); color: #70aaff; font-size: 10px; padding: 1px 6px; border-radius: 10px; font-weight: 600;">Meta Cloud</span>
            </div>
            <div style="font-size: 12px; color: #8696a0; margin-top: 3px; line-height: 1.3;">
              Sent <strong>"${query}"</strong> comparisons across <strong>${otherPlatforms}</strong> to WhatsApp!
              <div style="font-size: 11px; color: #5cf7c9; margin-top: 3px; font-weight: 600;">${winnerText}</div>
              <div style="font-size: 10.5px; opacity: 0.75; margin-top: 2px;">Status: ${deliveryText}</div>
            </div>
          </div>
        </div>
        <button id="wa-toast-close" style="background: none; border: none; color: #8696a0; font-size: 16px; cursor: pointer; padding: 2px 4px; line-height: 1;">✕</button>
      </div>

      <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-top: 10px; padding-top: 8px; border-top: 1px solid #2a3942;">
        <a id="wa-toast-sim" href="${BACKEND_URL}" target="_blank" style="color: #8696a0; text-decoration: none; font-size: 11px; padding: 4px 8px; border-radius: 4px;">
          Dashboard
        </a>
        <a id="wa-toast-view" href="${waWebUrl}" target="_blank" style="background: #25D366; color: #111b21; text-decoration: none; font-size: 11.5px; font-weight: 700; padding: 6px 14px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(37, 211, 102, 0.3);">
          <span>📲 Open in Real WhatsApp ↗</span>
        </a>
      </div>
    `;

    // Modern styling for the container
    Object.assign(toast.style, {
      position: "fixed",
      bottom: "24px",
      right: "24px",
      width: "360px",
      backgroundColor: "#111b21",
      border: "1px solid #00a884",
      borderRadius: "10px",
      padding: "14px",
      boxShadow: "0 10px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(0, 168, 132, 0.2)",
      zIndex: "2147483647",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      color: "#e9edef",
      boxSizing: "border-box",
      transition: "all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
      transform: "translateY(50px)",
      opacity: "0"
    });

    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
      toast.style.transform = "translateY(0)";
      toast.style.opacity = "1";
    });

    // Close button action
    document.getElementById("wa-toast-close").onclick = (e) => {
      e.stopPropagation();
      dismissToast(toast);
    };

    // Auto dismiss after 7 seconds
    setTimeout(() => {
      dismissToast(toast);
    }, 7000);
  }

  function dismissToast(toastEl) {
    if (!toastEl || !toastEl.parentNode) return;
    toastEl.style.transform = "translateY(40px)";
    toastEl.style.opacity = "0";
    setTimeout(() => {
      if (toastEl && toastEl.parentNode) toastEl.remove();
    }, 350);
  }

  // Debounced check function (2.5s timer)
  function handlePotentialSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const query = extractSearchQuery();
      if (query && query !== lastProcessedQuery) {
        triggerPriceSync(query);
      }
    }, 2500);
  }

  // Hook into search input changes
  function attachInputListeners() {
    const selectors = [
      "#twotabsearchtextbox", // Amazon
      "input[name='q']",       // Flipkart
      "input[placeholder*='Search']", // Meesho / Generic
      ".desktop-searchBar"    // Myntra
    ];

    selectors.forEach(sel => {
      const inputs = document.querySelectorAll(sel);
      inputs.forEach(input => {
        if (!input.dataset.waHooked) {
          input.dataset.waHooked = "true";
          input.addEventListener("input", handlePotentialSearch);
          input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
              clearTimeout(debounceTimer);
              const val = input.value.trim();
              if (val) triggerPriceSync(val);
            }
          });
        }
      });
    });
  }

  // Listen for SPA URL changes
  let currentHref = window.location.href;
  const observer = new MutationObserver(() => {
    attachInputListeners();
    if (window.location.href !== currentHref) {
      currentHref = window.location.href;
      handlePotentialSearch();
    }
  });

  observer.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true
  });

  // Initial check on load
  window.addEventListener("load", () => {
    attachInputListeners();
    const initialQuery = extractSearchQuery();
    if (initialQuery) {
      // Small delay on initial page load
      setTimeout(() => triggerPriceSync(initialQuery), 1200);
    }
  });

  // Also check immediately if already loaded
  if (document.readyState === "complete" || document.readyState === "interactive") {
    attachInputListeners();
    const query = extractSearchQuery();
    if (query) {
      setTimeout(() => triggerPriceSync(query), 1200);
    }
  }

  console.log(`[PriceSync] Content script active on ${identifyCurrentSite()}`);
})();

