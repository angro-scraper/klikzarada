const SH_GO_LIVE = (() => {
  const state = { snapshot: null };
  const el = (id) => document.getElementById(id);
  const present = (value, fallback) => (value === null || value === undefined ? fallback : value);
  const esc = (value) => String(present(value, "")).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));

  function api(path, options) {
    const requestOptions = options || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, requestOptions.headers || {});
    return fetch(path, Object.assign({}, requestOptions, {
      credentials: "same-origin",
      headers,
    })).then((response) => response.text().then((text) => {
      let data;
      try {
        data = JSON.parse(text);
      } catch (error) {
        data = { raw: text };
      }
      if (!response.ok) {
        throw new Error(data.detail || data.message || text || `HTTP ${response.status}`);
      }
      return data;
    }));
  }

  function setBusy(button, busy) {
    if (!button) return;
    button.disabled = busy;
    if (!button.dataset.originalText) {
      button.dataset.originalText = button.textContent;
    }
    button.textContent = busy ? "Radim..." : button.dataset.originalText;
  }

  function log(data) {
    const node = el("actionLog");
    node.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  }

  function logSummary(snapshot) {
    const checks = snapshot.checks || [];
    const lines = [
      `Status: ${snapshot.status || "-"}`,
      `Odluka: ${snapshot.decision || "-"}`,
      `Ažurirano: ${formatDate(snapshot.generated_at)}`,
      "",
      "Provere:",
    ];
    checks.forEach((item) => {
      lines.push(`${item.ok ? "OK" : "PROBLEM"} - ${item.label}: ${present(item.value, item.fix || "")}`);
    });
    log(lines.join("\n"));
  }

  function renderDecision(snapshot) {
    const card = el("decisionCard");
    const isOk = !!snapshot.ok;
    card.classList.toggle("is-red", !isOk);
    card.classList.toggle("is-green", isOk);
    el("decisionStatus").textContent = snapshot.status || (isOk ? "GREEN" : "RED");
    el("decisionTitle").textContent = snapshot.decision || (isOk ? "Spremno" : "Nije spremno");
    el("decisionMeta").textContent = `Ažurirano: ${formatDate(snapshot.generated_at)}`;
  }

  function formatDate(value) {
    if (!value) return "-";
    try {
      return new Intl.DateTimeFormat("sr-RS", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value));
    } catch (error) {
      return value;
    }
  }

  function checkCard(item) {
    return `
      <article class="go-live-check-v113 ${item.ok ? "is-green" : "is-red"}">
        <span>${item.ok ? "✓" : "!"}</span>
        <div>
          <strong>${esc(item.label)}</strong>
          <small>${esc(present(item.value, item.ok ? "Spremno" : item.fix))}</small>
        </div>
      </article>
    `;
  }

  function renderChecks(snapshot) {
    el("statusGrid").innerHTML = (snapshot.checks || []).map(checkCard).join("");
  }

  function renderActions(snapshot) {
    const actions = snapshot.next_actions || [];
    el("nextActions").innerHTML = actions.map((item) => `
      <div class="go-live-row-v113">
        <span>${actions.length === 1 && snapshot.ok ? "✓" : "→"}</span>
        <strong>${esc(item)}</strong>
      </div>
    `).join("");
  }

  function renderLinks(snapshot) {
    const links = snapshot.links || {};
    el("quickLinks").innerHTML = Object.entries(links).map(([label, href]) => `
      <a href="${esc(href)}">${esc(label.split("_").join(" "))}</a>
    `).join("");
  }

  function renderMissingImages(snapshot) {
    const missing = snapshot.missing_images || { products: [], missing_count: 0 };
    el("missingImagesCount").textContent = missing.ok ? "Sve imaju sliku" : `${missing.missing_count} bez slike`;
    el("missingImagesTable").innerHTML = missing.products.length
      ? missing.products.map((product) => `
        <tr>
          <td>${esc(product.id)}</td>
          <td><strong>${esc(product.name)}</strong></td>
          <td>${esc(product.store_name)}</td>
          <td>${esc(product.category || "-")}</td>
          <td>${esc(product.status)}</td>
          <td><a class="link-button secondary-link" href="${esc(product.admin_url)}">Otvori</a></td>
        </tr>
      `).join("")
      : `<tr><td colspan="6">Nema javnih ponuda bez slike.</td></tr>`;
  }

  function renderBlocks(snapshot) {
    const customers = snapshot.customers || {};
    const sellers = snapshot.sellers || {};
    el("customerBlocks").innerHTML = (customers.blocked_customers || []).length
      ? customers.blocked_customers.map((item) => `
        <div class="go-live-row-v113 is-red">
          <span>!</span>
          <div>
            <strong>${esc(item.name || item.phone)}</strong>
            <small>${esc(item.cancelled_reservations)} otkazivanja · ${esc(item.block_reason || "blokiran")}</small>
          </div>
        </div>
      `).join("")
      : `<div class="go-live-row-v113"><span>✓</span><strong>Nema blokiranih kupaca.</strong></div>`;

    el("sellerBlocks").innerHTML = (sellers.sellers || []).length
      ? sellers.sellers.map((item) => `
        <div class="go-live-row-v113 ${item.blocked ? "is-red" : ""}">
          <span>${item.blocked ? "!" : "→"}</span>
          <div>
            <strong>${esc(item.store_name)}</strong>
            <small>${esc(item.blocked_reason || "provera faktura")} · kasni: ${esc(item.late_payment_count)} · dospelo: ${esc(item.overdue_invoice_count)}</small>
          </div>
        </div>
      `).join("")
      : `<div class="go-live-row-v113"><span>✓</span><strong>Nema blokiranih prodavaca.</strong></div>`;
  }

  function renderFinance(snapshot) {
    const finance = snapshot.finance || {};
    const items = [
      ["Plaćene rezervacije", finance.paid_count],
      ["Plaćanje pri preuzimanju", finance.pay_on_pickup_count],
      ["Provizija za naplatu", `${finance.commission_due_total || 0} RSD`],
      ["Blokirane isplate", finance.blocked_payout_count],
      ["Dospelih faktura", finance.overdue_invoice_count],
      ["Isplata na čekanju", `${finance.pending_payout_amount || 0} RSD`],
    ];
    el("financeGrid").innerHTML = items.map(([label, value]) => `
      <article>
        <strong>${esc(present(value, 0))}</strong>
        <span>${esc(label)}</span>
      </article>
    `).join("");
  }

  function render(snapshot) {
    state.snapshot = snapshot;
    renderDecision(snapshot);
    renderChecks(snapshot);
    renderActions(snapshot);
    renderLinks(snapshot);
    renderMissingImages(snapshot);
    renderBlocks(snapshot);
    renderFinance(snapshot);
  }

  function refresh() {
    log("Učitavam Go Live kontrolni centar...");
    return api("/pilot-live/control-center").then((snapshot) => {
      render(snapshot);
      logSummary(snapshot);
      return snapshot;
    });
  }

  function runAction(buttonId, path, options) {
    const button = el(buttonId);
    setBusy(button, true);
    log(`Pokrećem: ${button.dataset.originalText || button.textContent}`);
    return api(path, options || {}).then((result) => {
      if (result.snapshot) {
        render(result.snapshot);
        logSummary(result.snapshot);
        return result;
      }
      return refresh().then(() => result);
    }).catch((error) => {
      log(`Greška: ${error.message}`);
    }).then((result) => {
      setBusy(button, false);
      return result;
    });
  }

  function bind() {
    el("refreshBtn").addEventListener("click", () => refresh().catch((error) => log(`Greška: ${error.message}`)));
    el("testFlowBtn").addEventListener("click", () => runAction("testFlowBtn", "/pilot-live/control-center/test-flow", { method: "POST" }));
    el("backupBtn").addEventListener("click", () => runAction("backupBtn", "/pilot-live/control-center/backup", { method: "POST" }));
    el("missingImagesBtn").addEventListener("click", () => runAction("missingImagesBtn", "/pilot-live/control-center/missing-images"));
    el("blocksBtn").addEventListener("click", () => runAction("blocksBtn", "/pilot-live/control-center/blocks"));
    el("financeBtn").addEventListener("click", () => runAction("financeBtn", "/pilot-live/control-center/finance"));
    el("readyBtn").addEventListener("click", () => runAction("readyBtn", "/pilot-live/control-center/mark-ready", { method: "POST" }));
  }

  return { bind, refresh };
})();

document.addEventListener("DOMContentLoaded", () => {
  SH_GO_LIVE.bind();
  SH_GO_LIVE.refresh().catch((error) => {
    document.getElementById("actionLog").textContent = `Greška: ${error.message}`;
  });
});
