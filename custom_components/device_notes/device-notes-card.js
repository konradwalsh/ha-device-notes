/**
 * Device Notes Card
 *
 * Renders the append-only note log from a `sensor.<device>_notes` entity
 * (reads `attributes.log`), newest-first, with source badges + timestamps.
 * A "?" button opens a short onboarding walkthrough that mocks how Device
 * Notes looks and how notes are added.
 *
 * Usage (Lovelace):
 *   type: custom:device-notes-card
 *   entity: sensor.living_room_trv_notes
 *   title: Notes        # optional
 */
class DeviceNotesCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Define an entity, e.g. sensor.living_room_trv_notes");
    }
    if (!String(config.entity).startsWith("sensor.")) {
      throw new Error("Entity must be the notes sensor (sensor.<device>_notes)");
    }
    this._config = config;
    this._lastLogJson = null;
    this._rendered = false;
    this._step = 0;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    const stateObj = this._hass.states[this._config.entity];
    const log =
      stateObj && Array.isArray(stateObj.attributes.log)
        ? stateObj.attributes.log
        : [];

    const logJson = JSON.stringify(log);
    if (logJson === this._lastLogJson && this._rendered) return;
    this._lastLogJson = logJson;
    this._rendered = true;

    const title = this._config.title ?? "Notes";
    let body;
    if (!stateObj) {
      body = `<div class="dn-empty">Entity <code>${this._esc(
        this._config.entity
      )}</code> not found.</div>`;
    } else if (log.length) {
      body = `<div class="dn-list">${log.map((e) => this._row(e)).join("")}</div>`;
    } else {
      body = `<div class="dn-empty">No notes yet.</div>`;
    }

    this.innerHTML = `
      <ha-card>
        <div class="dn-header">
          <span class="dn-title">${this._esc(title)}</span>
          <button class="dn-help" title="How Device Notes works" aria-label="Tutorial">?</button>
        </div>
        <div class="card-content">
          ${body}
          ${
            stateObj
              ? `<div class="dn-add">
            <input class="dn-add-input" type="text" maxlength="255" placeholder="Add a note…" />
            <button class="dn-add-btn">Add</button>
          </div>`
              : ""
          }
        </div>
      </ha-card>
      ${this._styles()}`;

    this._wire();
  }

  _wire() {
    const help = this.querySelector(".dn-help");
    if (help) help.addEventListener("click", () => this._openTutorial());
    const input = this.querySelector(".dn-add-input");
    const addBtn = this.querySelector(".dn-add-btn");
    if (input && addBtn) {
      addBtn.addEventListener("click", () => this._addNote(input));
      input.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") this._addNote(input);
      });
    }
    this.querySelectorAll(".dn-del").forEach((b) =>
      b.addEventListener("click", () => this._deleteEntry(b.getAttribute("data-ts")))
    );
  }

  _addNote(input) {
    const note = (input.value || "").trim();
    if (!note || !this._hass) return;
    this._hass.callService("device_notes", "append", {
      entity_id: this._config.entity,
      note,
      source: "user",
    });
    input.value = "";
  }

  _deleteEntry(ts) {
    if (!ts || !this._hass) return;
    this._hass.callService("device_notes", "delete", {
      entity_id: this._config.entity,
      ts,
    });
  }

  _row(e) {
    const src = (e.source || "").toString();
    return `
      <div class="dn-entry">
        <div class="dn-meta">
          <span class="dn-src dn-src-${this._esc(src.toLowerCase())}">${this._esc(
            src
          )}</span>
          <span class="dn-meta-right">
            <span class="dn-ts">${this._esc(this._fmt(e.ts))}</span>
            <button class="dn-del" title="Delete" aria-label="Delete" data-ts="${this._esc(
              e.ts
            )}">&times;</button>
          </span>
        </div>
        <div class="dn-text">${this._esc(e.text || "")}</div>
      </div>`;
  }

  // --- Tutorial ------------------------------------------------------------

  _openTutorial() {
    this._step = 0;
    if (!this._overlay) {
      this._overlay = document.createElement("div");
      this._overlay.className = "dn-overlay";
      this._overlay.addEventListener("click", (ev) => {
        if (ev.target === this._overlay) this._closeTutorial();
      });
      this.appendChild(this._overlay);
    }
    this._overlay.style.display = "flex";
    this._renderTutorial();
  }

  _closeTutorial() {
    if (this._overlay) this._overlay.style.display = "none";
  }

  _renderTutorial() {
    const panels = this._panels();
    const i = Math.max(0, Math.min(this._step, panels.length - 1));
    const p = panels[i];
    this._overlay.innerHTML = `
      <div class="dn-modal">
        <div class="dn-modal-head">
          <span>${p.title}</span>
          <button class="dn-x" aria-label="Close">&times;</button>
        </div>
        <div class="dn-modal-body">${p.body}</div>
        <div class="dn-dots">${panels
          .map((_, n) => `<span class="${n === i ? "on" : ""}"></span>`)
          .join("")}</div>
        <div class="dn-modal-foot">
          <button class="dn-back" ${i === 0 ? "disabled" : ""}>Back</button>
          <button class="dn-next">${i === panels.length - 1 ? "Done" : "Next"}</button>
        </div>
      </div>`;
    this._overlay.querySelector(".dn-x").onclick = () => this._closeTutorial();
    this._overlay.querySelector(".dn-back").onclick = () => {
      if (this._step > 0) {
        this._step--;
        this._renderTutorial();
      }
    };
    this._overlay.querySelector(".dn-next").onclick = () => {
      if (this._step < panels.length - 1) {
        this._step++;
        this._renderTutorial();
      } else {
        this._closeTutorial();
      }
    };
  }

  _panels() {
    const devicePage = `
      <p>Each opted-in device gets a grouped set of entities on its own page:</p>
      <div class="dn-mock">
        <div class="dn-mock-title">Living Room TRV</div>
        <div class="dn-mock-row"><span>Notes</span>
          <span class="dn-mock-val">Boiler serviced (today 08:00)</span></div>
        <div class="dn-mock-row"><span>Notes: new entry</span>
          <span class="dn-mock-input">Type a line, press Enter…</span></div>
      </div>
      <p class="dn-cap"><b>Notes</b> shows the log; <b>Notes: new entry</b> adds a
      line. They share a "Notes" prefix so they sit together.</p>`;

    const adding = `
      <p>Two ways to add a note:</p>
      <div class="dn-mock">
        <div class="dn-mock-row"><span class="dn-src dn-src-agent">agent</span>
          <span class="dn-mock-val">device_notes.append</span></div>
        <div class="dn-mock-row"><span class="dn-src dn-src-user">you</span>
          <span class="dn-mock-val">type in the Note entry box</span></div>
      </div>
      <p class="dn-cap">An AI agent calls the service; you can type lines too.
      Every entry is timestamped and tagged with its source.</p>`;

    const thisCard = `
      <p>This card shows the full log, newest first:</p>
      <div class="dn-mock dn-mock-log">
        <div class="dn-entry"><div class="dn-meta">
          <span class="dn-src dn-src-user">user</span>
          <span class="dn-ts">today 09:30</span></div>
          <div class="dn-text">Replaced the AA batteries</div></div>
        <div class="dn-entry"><div class="dn-meta">
          <span class="dn-src dn-src-agent">agent</span>
          <span class="dn-ts">today 08:00</span></div>
          <div class="dn-text">Boiler serviced — pressure back to 1.4 bar</div></div>
      </div>`;

    return [
      {
        title: "What is Device Notes?",
        body: `<p>A free-text, append-only <b>note log</b> attached to any device —
          written by an AI agent or by you, and kept right on the device's page.</p>
          <p class="dn-cap">Think of it as the device's memory: maintenance,
          observations, fixes.</p>`,
      },
      { title: "On the device's page", body: devicePage },
      { title: "Adding notes", body: adding },
      { title: "This card", body: thisCard },
    ];
  }

  // --- helpers -------------------------------------------------------------

  _esc(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  _fmt(ts) {
    if (!ts) return "";
    const d = new Date(ts);
    return isNaN(d.getTime()) ? String(ts) : d.toLocaleString();
  }

  getCardSize() {
    const log = this._lastLogJson ? JSON.parse(this._lastLogJson) : [];
    return 1 + Math.min(log.length, 6);
  }

  static getConfigElement() {
    return document.createElement("device-notes-card-editor");
  }

  static getStubConfig(hass) {
    // Pre-fill with an existing notes sensor so the card works immediately.
    const states = (hass && hass.states) || {};
    const candidates = Object.keys(states).filter(
      (id) =>
        id.startsWith("sensor.") &&
        id.endsWith("_notes") &&
        Array.isArray(states[id].attributes.log)
    );
    const entity = candidates.length
      ? candidates[Math.floor(Math.random() * candidates.length)]
      : "";
    return { entity };
  }

  _styles() {
    return `
      <style>
        .dn-header { display: flex; align-items: center; justify-content: space-between;
                     padding: 12px 16px 0; }
        .dn-title { font-size: 1.2rem; font-weight: 500; color: var(--primary-text-color); }
        .dn-help { width: 24px; height: 24px; border-radius: 50%; border: none; cursor: pointer;
                   font-weight: 700; line-height: 1; color: var(--text-primary-color, #fff);
                   background: var(--primary-color, #03a9f4); }
        .dn-list { display: flex; flex-direction: column; gap: 10px; }
        .dn-entry { padding-bottom: 10px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
        .dn-entry:last-child { border-bottom: none; padding-bottom: 0; }
        .dn-meta { display: flex; justify-content: space-between; align-items: center;
                   font-size: 0.75rem; margin-bottom: 2px; }
        .dn-src { text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600;
                  padding: 1px 6px; border-radius: 9px; color: var(--text-primary-color, #fff);
                  background: var(--secondary-text-color, #888); }
        .dn-src-agent { background: var(--primary-color, #03a9f4); }
        .dn-src-user { background: var(--success-color, #4caf50); }
        .dn-ts { color: var(--secondary-text-color, #888); }
        .dn-text { color: var(--primary-text-color, #212121); white-space: pre-wrap;
                   word-break: break-word; }
        .dn-empty { color: var(--secondary-text-color, #888); font-style: italic; }
        .dn-meta-right { display: inline-flex; align-items: center; gap: 6px; }
        .dn-del { border: none; background: none; cursor: pointer; line-height: 1; padding: 0 2px;
                  font-size: 1rem; color: var(--secondary-text-color, #888); opacity: 0.55; }
        .dn-del:hover { opacity: 1; color: var(--error-color, #db4437); }
        .dn-add { display: flex; gap: 8px; margin-top: 12px; }
        .dn-add-input { flex: 1; padding: 8px 10px; border-radius: 8px;
                        border: 1px solid var(--divider-color, #ccc);
                        background: var(--card-background-color, #fff);
                        color: var(--primary-text-color); }
        .dn-add-btn { border: none; border-radius: 8px; padding: 8px 16px; cursor: pointer;
                      font-weight: 600; background: var(--primary-color, #03a9f4);
                      color: var(--text-primary-color, #fff); }

        .dn-overlay { display: none; position: fixed; inset: 0; z-index: 99;
                      background: rgba(0,0,0,0.5); align-items: center; justify-content: center; }
        .dn-modal { width: min(420px, 92vw); background: var(--card-background-color, #fff);
                    border-radius: 14px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); overflow: hidden; }
        .dn-modal-head { display: flex; justify-content: space-between; align-items: center;
                         padding: 14px 16px; font-weight: 600; font-size: 1.05rem;
                         color: var(--primary-text-color); border-bottom: 1px solid var(--divider-color); }
        .dn-x { border: none; background: none; font-size: 1.4rem; cursor: pointer;
                color: var(--secondary-text-color); line-height: 1; }
        .dn-modal-body { padding: 16px; color: var(--primary-text-color); }
        .dn-modal-body p { margin: 0 0 10px; }
        .dn-cap { color: var(--secondary-text-color); font-size: 0.85rem; }
        .dn-mock { border: 1px solid var(--divider-color, #ddd); border-radius: 10px;
                   padding: 10px 12px; margin: 8px 0; background: var(--secondary-background-color, #f5f5f5); }
        .dn-mock-title { font-weight: 600; margin-bottom: 6px; color: var(--primary-text-color); }
        .dn-mock-row { display: flex; justify-content: space-between; align-items: center;
                       gap: 10px; padding: 4px 0; font-size: 0.9rem; color: var(--primary-text-color); }
        .dn-mock-val { color: var(--secondary-text-color); text-align: right; }
        .dn-mock-input { color: var(--disabled-text-color, #999); font-style: italic;
                         border: 1px dashed var(--divider-color, #ccc); border-radius: 6px;
                         padding: 2px 8px; }
        .dn-mock-log .dn-entry:last-child { border-bottom: none; }
        .dn-dots { display: flex; gap: 6px; justify-content: center; padding: 2px 0 6px; }
        .dn-dots span { width: 7px; height: 7px; border-radius: 50%;
                        background: var(--divider-color, #ccc); }
        .dn-dots span.on { background: var(--primary-color, #03a9f4); }
        .dn-modal-foot { display: flex; justify-content: space-between; gap: 8px;
                         padding: 12px 16px; border-top: 1px solid var(--divider-color); }
        .dn-modal-foot button { border: none; border-radius: 8px; padding: 8px 18px; cursor: pointer;
                                font-weight: 600; }
        .dn-back { background: var(--secondary-background-color, #eee);
                   color: var(--primary-text-color); }
        .dn-back:disabled { opacity: 0.4; cursor: default; }
        .dn-next { background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); }
      </style>`;
  }
}

customElements.define("device-notes-card", DeviceNotesCard);

/**
 * Visual config editor — a small ha-form so the card is configurable from the
 * UI (entity picker + optional title) instead of YAML-only.
 */
class DeviceNotesCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) =>
        ({ entity: "Notes sensor", title: "Title (optional)" }[schema.name] ||
          schema.name);
      this._form.computeHelper = (schema) =>
        schema.name === "entity"
          ? "Pick a device's Notes sensor (sensor.<device>_notes)."
          : "";
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: ev.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = [
      {
        name: "entity",
        required: true,
        selector: { entity: { integration: "device_notes", domain: "sensor" } },
      },
      { name: "title", selector: { text: {} } },
    ];
    this._form.data = this._config;
  }
}

customElements.define("device-notes-card-editor", DeviceNotesCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "device-notes-card",
  name: "Device Notes Card",
  description: "Shows a device's append-only note log (with a built-in tutorial).",
  preview: true,
  documentationURL: "https://github.com/konradwalsh/ha-device-notes",
});

console.info(
  "%c DEVICE-NOTES-CARD ",
  "color: white; background: #03a9f4; font-weight: 700;"
);
