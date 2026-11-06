/**
 * WhatsApp Cross-Platform Price Sync Content Script
 * Injected into Amazon (.in, .com), Flipkart, Meesho, and Myntra.
 * Detects product search queries, checks 'Allow All' status,
 * triggers FastAPI backend, and shows an actionable WhatsApp sync toast.
 */

(() => {
  const BACKEND_URL = "http://localhost:8000";
  let lastProcessedQuery = "";
  let debounceTimer = null;

  function identifyCurrentSite() {
    const host = window.location.hostname.toLowerCase();
    if (host.includes("amazon.")) return "Amazon";
    if (host.includes("flipkart.com")) return "Flipkart.com";
    if (host.includes("meesho.com")) return "Meesho.com";
    if (host.includes("myntra.com")) return "Myntra.com";
    return "E-Commerce Site";
  }

  function extractSearchQuery() {
    const url = new URL(window.location.href);
    const host = window.location.hostname.toLowerCase();
    let query = "";

    // 1. Amazon (in, com)
    if (host.includes("amazon.")) {
      query = url.searchParams.get("k") || url.searchParams.get("field-keywords") || "";
      if (!query) {
        const input = document.querySelector("#twotabsearchtextbox, input[name='field-keywords']");
        if (input && input.value) query = input.value;
      }
    }
    // 2. Flipkart
    else if (host.includes("flipkart.com")) {
      query = url.searchParams.get("q") || "";
      if (!query) {
        const input = document.querySelector("input[name='q'], input[title*='Search']");
        if (input && input.value) query = input.value;
      }
    }
    // 3. Meesho
    else if (host.includes("meesho.com")) {
      query = url.searchParams.get("q") || "";
      if (!query) {
        const input = document.querySelector("input[placeholder*='Search'], input[type='search']");
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
        // If stored phone is dummy demo default, let backend use the active configured target phone
        const phone = (data.phone && data.phone !== "919876543210") ? data.phone : "";
        const autoOpen = !!data.auto_open_whatsapp;

        if (!allowAll) {
          console.log("[PriceSync] 'Allow All' is disabled. Skipping WhatsApp dispatch.");
          return;
        }

        lastProcessedQuery = query;
        dispatchSearchToBackend(phone, query, autoOpen);
      });
    } else {
      lastProcessedQuery = query;
      dispatchSearchToBackend("", query, false);
    }
  }

  async function dispatchSearchToBackend(phone, query, autoOpen) {
    const currentSite = identifyCurrentSite();

    try {
      console.log(`[PriceSync] Sending search '${query}' from ${currentSite} to backend (phone: ${phone || 'default'})...`);
      const res = await fetch(`${BACKEND_URL}/trigger-search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: phone,
          query: query,
          current_site: currentSite
        })
      });

      if (!res.ok) {
        console.warn("[PriceSync] Backend response not OK:", res.status);
        lastProcessedQuery = ""; // Reset so user can retry
        return;
      }
      const data = await res.json();

      if (data.status === "success") {
        showToastNotification(query, currentSite, data);

        // Auto-open in real WhatsApp if user enabled that setting
        if (autoOpen && data.whatsapp_web_url) {
          window.open(data.whatsapp_web_url, "_blank");
        }
      } else if (data.status === "deduplicated") {
        console.log("[PriceSync] Query deduplicated (60s cooldown):", data.message);
      } else {
        lastProcessedQuery = ""; // Reset so user can retry
      }
    } catch (err) {
      console.warn("[PriceSync] Backend is offline or unreachable at http://localhost:8000:", err.message);
      lastProcessedQuery = ""; // Reset so user can retry
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

    const targetPhone = data.phone || "your WhatsApp";
    const waWebUrl = data.whatsapp_web_url || `https://web.whatsapp.com/send?phone=${targetPhone}&text=${encodeURIComponent(data.whatsapp_preview || query)}`;
    const deliveryText = data.delivery_status || "Processed";
    const isMetaDelivered = deliveryText.includes("Delivered via Meta");
    const isMetaError = deliveryText.includes("Meta Error") || deliveryText.includes("Authentication Error");

    const winnerText = (data.summary && data.summary.winner_platform) 
      ? `🏆 Best Deal: ${data.summary.winner_platform} at ${data.summary.lowest_price}`
      : `Comparison generated across 4 platforms`;

    const toast = document.createElement("div");
    toast.id = "wa-price-sync-toast";
    toast.innerHTML = `
      <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="background: #25D366; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; box-shadow: 0 2px 6px rgba(37,211,102,0.4);">
            📲
          </div>
          <div>
            <div style="font-weight: 700; font-size: 13px; color: #e9edef; display: flex; align-items: center; gap: 6px;">
              <span>WhatsApp Price Sync</span>
              ${isMetaDelivered 
                ? '<span style="background: rgba(37,211,102,0.25); color: #25D366; font-size: 10px; padding: 1px 6px; border-radius: 10px; font-weight: 600;">Sent via Meta</span>' 
                : '<span style="background: rgba(245,158,11,0.25); color: #fbbf24; font-size: 10px; padding: 1px 6px; border-radius: 10px; font-weight: 600;">Action Ready</span>'}
            </div>
            <div style="font-size: 12px; color: #8696a0; margin-top: 3px; line-height: 1.35;">
              Searched <strong>"${query}"</strong>. Compared across <strong>${otherPlatforms}</strong>!
              <div style="font-size: 11.5px; color: #5cf7c9; margin-top: 3px; font-weight: 600;">${winnerText}</div>
              <div style="font-size: 11px; margin-top: 3px; color: ${isMetaDelivered ? '#5cf7c9' : (isMetaError ? '#fca5a5' : '#93c5fd')};">
                ${isMetaDelivered ? `✅ Dispatched to +${targetPhone}` : `Target: +${targetPhone} (${deliveryText})`}
              </div>
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
          <span>📲 Send to Friend on WhatsApp ↗</span>
        </a>
      </div>
    `;

    // Modern styling for the container
    Object.assign(toast.style, {
      position: "fixed",
      bottom: "24px",
      right: "24px",
      width: "380px",
      backgroundColor: "#111b21",
      border: isMetaDelivered ? "1px solid #00a884" : "1px solid #f59e0b",
      borderRadius: "10px",
      padding: "14px",
      boxShadow: "0 10px 30px rgba(0, 0, 0, 0.6), 0 0 15px rgba(0, 168, 132, 0.2)",
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

    // Auto dismiss after 8 seconds
    setTimeout(() => {
      dismissToast(toast);
    }, 8000);
  }

  function dismissToast(toastEl) {
    if (!toastEl || !toastEl.parentNode) return;
    toastEl.style.transform = "translateY(40px)";
    toastEl.style.opacity = "0";
    setTimeout(() => {
      if (toastEl && toastEl.parentNode) toastEl.remove();
    }, 350);
  }

  // Debounced check function (2s timer)
  function handlePotentialSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const query = extractSearchQuery();
      if (query && query !== lastProcessedQuery) {
        triggerPriceSync(query);
      }
    }, 2000);
  }

  // Hook into search inputs and forms
  function attachInputListeners() {
    const inputSelectors = [
      "#twotabsearchtextbox", // Amazon
      "input[name='field-keywords']",
      "input[name='q']",       // Flipkart
      "input[placeholder*='Search']", // Meesho / Generic
      "input[type='search']",
      ".desktop-searchBar"    // Myntra
    ];

    inputSelectors.forEach(sel => {
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

    // Also hook search forms and buttons
    const formSelectors = [
      "#nav-search-bar-form", // Amazon
      "form[action*='/search']",
      "form[action*='search']",
      "header form"
    ];

    formSelectors.forEach(sel => {
      const forms = document.querySelectorAll(sel);
      forms.forEach(form => {
        if (!form.dataset.waHooked) {
          form.dataset.waHooked = "true";
          form.addEventListener("submit", () => {
            clearTimeout(debounceTimer);
            const query = extractSearchQuery();
            if (query) triggerPriceSync(query);
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
      setTimeout(() => triggerPriceSync(initialQuery), 1000);
    }
  });

  if (document.readyState === "complete" || document.readyState === "interactive") {
    attachInputListeners();
    const query = extractSearchQuery();
    if (query) {
      setTimeout(() => triggerPriceSync(query), 1000);
    }
  }

  console.log(`[PriceSync] Content script active on ${identifyCurrentSite()}`);
})();
