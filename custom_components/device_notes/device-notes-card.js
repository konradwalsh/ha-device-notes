/**
 * Device Notes Card
 *
 * Renders the append-only note log from a `sensor.<device>_notes` entity
 * (reads `attributes.log`), newest-first, showing source + timestamp + text.
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

    // Skip re-render when the log hasn't changed.
    const logJson = JSON.stringify(log);
    if (logJson === this._lastLogJson && this._rendered) return;
    this._lastLogJson = logJson;
    this._rendered = true;

    const title = this._config.title ?? "Notes";
    if (!stateObj) {
      this.innerHTML = this._shell(
        title,
        `<div class="dn-empty">Entity <code>${this._esc(
          this._config.entity
        )}</code> not found.</div>`
      );
      return;
    }

    const body = log.length
      ? `<div class="dn-list">${log.map((e) => this._row(e)).join("")}</div>`
      : `<div class="dn-empty">No notes yet.</div>`;
    this.innerHTML = this._shell(title, body);
  }

  _row(e) {
    const src = (e.source || "").toString();
    return `
      <div class="dn-entry">
        <div class="dn-meta">
          <span class="dn-src dn-src-${this._esc(src.toLowerCase())}">${this._esc(
            src
          )}</span>
          <span class="dn-ts">${this._esc(this._fmt(e.ts))}</span>
        </div>
        <div class="dn-text">${this._esc(e.text || "")}</div>
      </div>`;
  }

  _shell(title, inner) {
    return `
      <ha-card header="${this._esc(title)}">
        <div class="card-content">${inner}</div>
      </ha-card>
      <style>
        .dn-list { display: flex; flex-direction: column; gap: 10px; }
        .dn-entry { padding-bottom: 10px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
        .dn-entry:last-child { border-bottom: none; padding-bottom: 0; }
        .dn-meta { display: flex; justify-content: space-between; align-items: center;
                   font-size: 0.75rem; margin-bottom: 2px; }
        .dn-src { text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600;
                  padding: 1px 6px; border-radius: 9px;
                  color: var(--text-primary-color, #fff);
                  background: var(--secondary-text-color, #888); }
        .dn-src-agent { background: var(--primary-color, #03a9f4); }
        .dn-src-user { background: var(--success-color, #4caf50); }
        .dn-ts { color: var(--secondary-text-color, #888); }
        .dn-text { color: var(--primary-text-color, #212121); white-space: pre-wrap;
                   word-break: break-word; }
        .dn-empty { color: var(--secondary-text-color, #888); font-style: italic; }
      </style>`;
  }

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

  static getStubConfig() {
    return { entity: "" };
  }
}

customElements.define("device-notes-card", DeviceNotesCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "device-notes-card",
  name: "Device Notes Card",
  description: "Shows a device's append-only note log (from its Notes sensor).",
});

console.info(
  "%c DEVICE-NOTES-CARD ",
  "color: white; background: #03a9f4; font-weight: 700;"
);
