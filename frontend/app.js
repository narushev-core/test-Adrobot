"use strict";

const API = "/api";

const STATUS_LABELS = {
  pending: "В очереди",
  in_progress: "Создаётся",
  success: "Готово",
  failed: "Ошибка",
  rollback_failed: "Ошибка отката",
};
const CAMPAIGN_FINAL = ["success", "failed", "rollback_failed"];

const $ = (id) => document.getElementById(id);

function setStatusBadge(el, status) {
  el.textContent = STATUS_LABELS[status] || status;
  el.dataset.status = status;
  el.hidden = false;
}

function showError(el, message) {
  el.textContent = message;
  el.hidden = !message;
}

function setLoading(button, loading) {
  button.disabled = loading;
  button.classList.toggle("is-loading", loading);
}

function formatDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return null;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = formatDetail(body.detail) || detail;
    } catch {
      /* ignore body parse errors */
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function postJson(url, payload) {
  return fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    $(`tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "editor") loadCampaignList();
  });
});

function setupAutocomplete({ input, list, hidden, search, delay = 200, onSelect }) {
  let timer = null;
  let items = [];
  let active = -1;
  let requestSeq = 0;

  function close() {
    list.hidden = true;
    active = -1;
  }

  function select(item) {
    input.value = item.name;
    hidden.value = String(item.id);
    input.classList.add("is-selected");
    input.classList.remove("is-invalid");
    close();
    if (onSelect) onSelect(item);
  }

  function highlight(index) {
    const nodes = list.querySelectorAll("li[data-index]");
    nodes.forEach((n) => n.classList.remove("active"));
    active = index;
    if (nodes[index]) {
      nodes[index].classList.add("active");
      nodes[index].scrollIntoView({ block: "nearest" });
    }
  }

  function render() {
    list.innerHTML = "";
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "Ничего не найдено";
      list.appendChild(li);
    }
    items.forEach((item, index) => {
      const li = document.createElement("li");
      li.dataset.index = String(index);
      li.setAttribute("role", "option");
      const name = document.createElement("span");
      name.textContent = item.name;
      const sid = document.createElement("span");
      sid.className = "sid";
      sid.textContent = `#${item.id}`;
      li.append(name, sid);
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        select(item);
      });
      list.appendChild(li);
    });
    list.hidden = false;
    active = -1;
  }

  input.addEventListener("input", () => {
    hidden.value = "";
    input.classList.remove("is-selected");
    clearTimeout(timer);
    const query = input.value.trim();
    if (!query) {
      close();
      return;
    }
    timer = setTimeout(async () => {
      const seq = ++requestSeq;
      try {
        const result = await search(query);
        if (seq !== requestSeq) return;
        items = result;
        render();
      } catch (err) {
        console.error("autocomplete search failed", err);
      }
    }, delay);
  });

  input.addEventListener("keydown", (e) => {
    if (list.hidden || !items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      highlight((active + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      highlight((active - 1 + items.length) % items.length);
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      select(items[active]);
    } else if (e.key === "Escape") {
      close();
    }
  });

  input.addEventListener("blur", close);

  return { select };
}

setupAutocomplete({
  input: $("group-search"),
  list: $("group-suggestions"),
  hidden: document.querySelector('#create-form input[name="group_id"]'),
  delay: 250,
  search: async (query) => {
    const page = await fetchJson(`${API}/groups/search?search=${encodeURIComponent(query)}`);
    return page.items;
  },
});

const offerSearchInput = $("offer-search");
const offerHiddenInput = document.querySelector('#create-form input[name="offer_id"]');
let offersCache = null;

async function loadOffersCache() {
  if (!offersCache) {
    const page = await fetchJson(`${API}/offers?size=100`);
    offersCache = page.items;
  }
  return offersCache;
}

const offerPicker = setupAutocomplete({
  input: offerSearchInput,
  list: $("offer-suggestions"),
  hidden: offerHiddenInput,
  delay: 100,
  search: async (query) => {
    const q = query.toLowerCase();
    const offers = await loadOffersCache();
    return offers
      .filter((o) => o.name.toLowerCase().includes(q) || String(o.id) === q)
      .slice(0, 20);
  },
});

const newOfferForm = $("new-offer-form");
const newOfferNameInput = $("new-offer-name");
const newOfferUrlInput = $("new-offer-url");
const newOfferErrorEl = $("new-offer-error");
const toggleNewOfferBtn = $("toggle-new-offer");

toggleNewOfferBtn.addEventListener("click", () => {
  newOfferForm.hidden = !newOfferForm.hidden;
  toggleNewOfferBtn.textContent = newOfferForm.hidden ? "+ Новый оффер" : "Отмена";
  if (!newOfferForm.hidden) newOfferNameInput.focus();
});

$("create-offer-btn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  showError(newOfferErrorEl, "");
  const name = newOfferNameInput.value.trim();
  const url = newOfferUrlInput.value.trim();
  if (!name || !url) {
    showError(newOfferErrorEl, "Укажите название и URL редиректа");
    return;
  }
  setLoading(button, true);
  try {
    const offer = await postJson(`${API}/offers`, { name, redirect_url: url });
    offersCache = null; // сбрасываем кэш, чтобы новый оффер сразу нашёлся поиском
    offerPicker.select(offer);
    newOfferForm.hidden = true;
    toggleNewOfferBtn.textContent = "+ Новый оффер";
    newOfferNameInput.value = "";
    newOfferUrlInput.value = "";
  } catch (err) {
    showError(newOfferErrorEl, err.message);
  } finally {
    setLoading(button, false);
  }
});

const createForm = $("create-form");
const createSubmit = $("create-submit");
const createFormError = $("create-form-error");
const createPlaceholder = $("create-placeholder");
const createResult = $("create-result");
const createAliasEl = $("create-alias");
const createStatusEl = $("create-status");
const createErrorEl = $("create-error");
const createSteps = $("create-steps");
let createSource = null;

function validateCreateForm(form) {
  const errors = [];
  const nameInput = $("campaign-name");
  const geoInput = $("campaign-geo");
  const name = String(form.get("name") || "").trim();
  const geo = String(form.get("geo") || "").trim().toUpperCase();

  nameInput.classList.toggle("is-invalid", !name);
  if (!name) errors.push("укажите название");

  const geoOk = /^[A-Z]{2}$/.test(geo);
  geoInput.classList.toggle("is-invalid", !geoOk);
  if (!geoOk) errors.push("гео — две латинские буквы");

  const offerOk = Boolean(offerHiddenInput.value);
  offerSearchInput.classList.toggle("is-invalid", !offerOk);
  if (!offerOk) errors.push("выберите оффер из списка или создайте новый");

  return { errors, name, geo };
}

function renderSteps(status) {
  const order = ["pending", "in_progress", "done"];
  const current = status === "success" ? 3 : status === "in_progress" ? 1 : 0;
  const failed = status === "failed" || status === "rollback_failed";
  createSteps.querySelectorAll("li").forEach((li, i) => {
    li.className = "";
    if (failed) {
      if (i === 0) li.classList.add("done");
      if (i === 1) li.classList.add("error");
    } else if (i < current) {
      li.classList.add("done");
    } else if (i === current) {
      li.classList.add("current");
    }
    if (order[i] === "done") {
      li.textContent = failed ? STATUS_LABELS[status] : "Готово";
    }
  });
}

function updateCreateStatus(status, error) {
  setStatusBadge(createStatusEl, status);
  renderSteps(status);
  showError(createErrorEl, error || "");
}

$("campaign-geo").addEventListener("input", (e) => {
  e.target.value = e.target.value.toUpperCase().replace(/[^A-Z]/g, "");
});

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(createForm);
  const { errors, name, geo } = validateCreateForm(form);
  if (errors.length) {
    showError(createFormError, `Проверьте форму: ${errors.join(", ")}.`);
    return;
  }
  showError(createFormError, "");

  const payload = { name, geo, offer_id: Number(form.get("offer_id")) };
  const groupId = form.get("group_id");
  if (groupId) payload.group_id = Number(groupId);

  setLoading(createSubmit, true);
  try {
    const result = await postJson(`${API}/campaigns`, payload);
    createPlaceholder.hidden = true;
    createResult.hidden = false;
    createAliasEl.textContent = result.alias;
    updateCreateStatus(result.status);
    if (createSource) createSource.close();
    createSource = watchCampaignStatus(result.id);
  } catch (err) {
    showError(createFormError, err.message);
  } finally {
    setLoading(createSubmit, false);
  }
});

function watchCampaignStatus(campaignId) {
  const source = new EventSource(`${API}/campaigns/${campaignId}/events`);
  source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateCreateStatus(data.status, data.error);
    if (CAMPAIGN_FINAL.includes(data.status)) source.close();
  };
  source.onerror = () => source.close();
  return source;
}

// ---------- Editor ----------
const campaignSelect = $("campaign-select");
const editorEmpty = $("editor-empty");
const editorBody = $("editor-body");
const offersList = $("offers-list");
const addOfferForm = $("add-offer-form");
const operationBox = $("operation-box");
const operationStatusEl = $("operation-status");
const operationTextEl = $("operation-text");
const operationErrorEl = $("operation-error");

let currentCampaignId = null;

$("refresh-campaigns").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  setLoading(button, true);
  await loadCampaignList();
  setLoading(button, false);
});

async function loadCampaignList() {
  try {
    const page = await fetchJson(`${API}/campaigns?size=100&order_by=-created_at`);
    const previous = campaignSelect.value;
    campaignSelect.innerHTML = '<option value="">— выберите кампанию —</option>';
    for (const c of page.items) {
      const option = document.createElement("option");
      option.value = c.id;
      option.textContent = `${c.name} · ${c.geo} · ${STATUS_LABELS[c.status] || c.status}`;
      campaignSelect.appendChild(option);
    }
    if (previous) campaignSelect.value = previous;
  } catch (err) {
    console.error("failed to load campaigns", err);
  }
}

campaignSelect.addEventListener("change", async () => {
  currentCampaignId = campaignSelect.value || null;
  editorBody.hidden = !currentCampaignId;
  editorEmpty.hidden = Boolean(currentCampaignId);
  if (currentCampaignId) await loadCampaignEditor(currentCampaignId);
});

async function loadCampaignEditor(campaignId) {
  operationBox.hidden = true;
  showError(operationErrorEl, "");
  try {
    const campaign = await fetchJson(`${API}/campaigns/${campaignId}`);
    $("editor-title").textContent = campaign.name;
    $("editor-alias").textContent = campaign.alias;
    $("editor-keitaro-id").textContent = campaign.keitaro_id ?? "—";
    $("editor-geo").textContent = campaign.geo;
    $("editor-stream-id").textContent = campaign.offer_stream_id ?? "—";
    setStatusBadge($("editor-status"), campaign.status);

    if (campaign.status !== "success") {
      renderOffersMessage("Кампания ещё не готова к редактированию");
      setEditorDisabled(true);
      return;
    }
    setEditorDisabled(false);
    await loadOffers(campaignId);
  } catch (err) {
    showError(operationErrorEl, err.message);
  }
}

function renderOffersMessage(text) {
  offersList.innerHTML = "";
  const li = document.createElement("li");
  li.className = "offers-empty";
  li.textContent = text;
  offersList.appendChild(li);
}

async function loadOffers(campaignId) {
  const stream = await fetchJson(`${API}/campaigns/${campaignId}/offers`);
  if (!stream.offers.length) {
    renderOffersMessage("В потоке нет офферов");
    return;
  }
  offersList.innerHTML = "";
  for (const offer of stream.offers) {
    const li = document.createElement("li");
    li.className = "offer-row";
    li.innerHTML = `
      <span class="offer-id"><small>#</small>${Number(offer.offer_id)}</span>
      <span class="share-bar"><span style="width:${Number(offer.share)}%"></span></span>
      <span class="share-value">${Number(offer.share)}%</span>`;
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "icon-btn";
    removeBtn.title = "Удалить оффер из потока";
    removeBtn.setAttribute("aria-label", `Удалить оффер ${offer.offer_id}`);
    removeBtn.textContent = "✕";
    removeBtn.addEventListener("click", () => removeOffer(offer.offer_id));
    li.appendChild(removeBtn);
    offersList.appendChild(li);
  }
}

function setEditorDisabled(disabled) {
  addOfferForm.querySelectorAll("input, button").forEach((el) => (el.disabled = disabled));
  offersList.querySelectorAll("button").forEach((b) => (b.disabled = disabled));
}

addOfferForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const offerId = Number(new FormData(addOfferForm).get("offer_id"));
  await runOperation(`Добавляем оффер #${offerId}`, () =>
    postJson(`${API}/campaigns/${currentCampaignId}/offers`, { offer_id: offerId })
  );
  addOfferForm.reset();
});

async function removeOffer(offerId) {
  if (!confirm(`Удалить оффер #${offerId} из потока?`)) return;
  await runOperation(`Удаляем оффер #${offerId}`, () =>
    fetchJson(`${API}/campaigns/${currentCampaignId}/offers/${offerId}`, { method: "DELETE" })
  );
}

function showOperation(status, text) {
  operationBox.hidden = false;
  setStatusBadge(operationStatusEl, status);
  operationTextEl.textContent = text;
}

async function runOperation(label, request) {
  setEditorDisabled(true);
  showError(operationErrorEl, "");
  try {
    const result = await request();
    showOperation(result.status, `${label}…`);
    await waitForOperation(result.operation_id, label);
  } catch (err) {
    operationBox.hidden = true;
    showError(operationErrorEl, err.message);
    setEditorDisabled(false);
  }
}

function waitForOperation(operationId, label) {
  return new Promise((resolve) => {
    const source = new EventSource(`${API}/operations/${operationId}/events`);
    const finish = async () => {
      source.close();
      try {
        await loadOffers(currentCampaignId);
      } catch (err) {
        showError(operationErrorEl, err.message);
      }
      setEditorDisabled(false);
      resolve();
    };
    source.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      if (data.status === "success") {
        showOperation(data.status, `${label}: изменения применены`);
        await finish();
      } else if (data.status === "failed") {
        showOperation(data.status, `${label}: не удалось`);
        showError(operationErrorEl, data.error || "");
        await finish();
      } else {
        showOperation(data.status, `${label}…`);
      }
    };
    source.onerror = finish;
  });
}
