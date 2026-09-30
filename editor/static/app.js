const $ = (id) => document.getElementById(id);
// Physical layout with the USB cutout facing away from the user.
const DISPLAY_ORDER = [11, 8, 5, 2, 10, 7, 4, 1, 9, 6, 3, 0];
const PRESET_LIGHTS = ["#35a9c1", "#8ab6e3", "#b995d4", "#e6b680", "#86b8a5", "#d498ac", "#a3c77a", "#e9c77c", "#86a9ca", "#9fd1c6", "#e7a491", "#b0aacd"];
const state = {
  connected: false, layersReady: false, options: null, ports: [], selectedPort: null, ids: [], names: {}, active: null,
  profile: null, layerId: "base", selected: 0, dirty: false, lastColors: null, colorHsv: null, colorKey: null,
  updating: false, firmware: null, latest: null,
};

function layer() { return state.profile?.layers.find((item) => item.id === state.layerId); }
function newerFirmware(latest, installed) {
  if (!latest || !installed) return false;
  if (installed === "unknown") return true;
  const left = latest.split(".").map(Number), right = installed.split(".").map(Number);
  for (let i = 0; i < 3; i++) if (left[i] !== right[i]) return left[i] > right[i];
  return false;
}
function reservedFor(index, layerId = state.layerId) {
  return state.profile?.layers.filter((item) => item.id !== layerId &&
    item.keys[index].kind === "layer" && item.keys[index].mode === "toggle" &&
    item.keys[index].target === layerId) || [];
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "Request failed");
  return value;
}

function tell(message, error = false) {
  $("message").textContent = message;
  $("message").classList.toggle("error", error);
}

function labelFor(action) {
  if (!action || action.kind === "none") return "Unassigned";
  if (action.kind === "media") return state.options.media[action.usage] || "Media";
  if (action.kind === "layer") {
    const target = state.profile.layers.find((item) => item.id === action.target);
    return `${target?.name || action.target} · ${action.mode === "timed" ? `${action.seconds}s` : action.mode}`;
  }
  const key = state.options.keys.find((item) => item.usage === action.usage);
  const mask = action.modifiers;
  const mac = state.profile.layout === "de-macos" ||
    (state.profile.layout === "us" && state.options.hostPlatform === "darwin");
  const characterAltMask = mac ? 0x04 : 0x40;
  const shifted = !!(mask & 0x22), option = !!(mask & characterAltMask);
  const character = state.options.characters[`${action.usage}:${Number(shifted)}:${Number(option)}`];
  if (!(mask & ~(0x22 | characterAltMask)) && character) return character;
  const modifiers = [];
  if (mask & 0x11) modifiers.push("Ctrl");
  if (shifted) modifiers.push("Shift");
  if (mask & 0x04) modifiers.push(mac ? "Option" : "Alt");
  if (mask & 0x40) modifiers.push(mac ? "Right Option" : "AltGr");
  if (mask & 0x88) modifiers.push(mac ? "Cmd" : "Win/Super");
  return [...modifiers, key ? key.label : `Key ${action.usage}`].join(" + ");
}

function fillSelect(element, entries) {
  element.replaceChildren();
  for (const entry of entries) {
    const option = document.createElement("option");
    option.value = String(entry.value);
    option.textContent = entry.label;
    element.append(option);
  }
}

function renderProfiles() {
  const list = $("profile-list");
  list.replaceChildren();
  for (const id of state.ids) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "profile-item";
    if (state.profile?.id === id) button.classList.add("selected");
    const title = document.createElement("span");
    title.textContent = state.names[id] || id;
    const detail = document.createElement("small");
    detail.textContent = id === state.active ? "Active on Keybow" : id;
    button.append(title, detail);
    button.addEventListener("click", () => loadProfile(id));
    list.append(button);
  }
}

function renderGrid() {
  const grid = $("key-grid");
  grid.replaceChildren();
  for (const index of DISPLAY_ORDER) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "key";
    button.style.setProperty("--key-light", layer()?.lighting.mode === "static"
      ? layer().lighting.colors[index] : PRESET_LIGHTS[index]);
    button.disabled = !state.profile;
    if (index === state.selected && state.profile) button.classList.add("selected");
    const number = document.createElement("span");
    number.className = "key-number";
    number.textContent = `KEY ${String(index + 1).padStart(2, "0")}`;
    const label = document.createElement("span");
    label.className = "key-label";
    label.textContent = state.profile ? reservedFor(index).length ? "Reserved for return" : labelFor(layer().keys[index]) : "—";
    if (state.profile && reservedFor(index).length) button.classList.add("reserved");
    button.append(number, label);
    button.addEventListener("click", () => {
      state.selected = index;
      render();
    });
    grid.append(button);
  }
}

function renderInspector() {
  const profile = state.profile;
  const action = layer()?.keys[state.selected];
  $("inspector-title").textContent = `Key ${String(state.selected + 1).padStart(2, "0")}`;
  for (const id of ["keyboard-layout", "action-kind", "key-usage", "media-usage", "lighting-mode", "preset",
                   "color-value", "color-hex", "color-r", "color-g", "color-b", "layer-target", "layer-mode", "layer-seconds"]) {
    $(id).disabled = !profile || !state.layersReady;
  }
  $("modifiers-row").disabled = !profile || !state.layersReady;
  if (!profile) return;
  const reserved = reservedFor(state.selected).length > 0;
  $("reserved-note").hidden = !reserved;
  $("action-kind").disabled = reserved || !state.layersReady;
  $("keyboard-layout").value = profile.layout || "us";
  $("action-kind").value = action.kind;
  $("key-usage-row").hidden = action.kind !== "keyboard";
  $("modifiers-row").hidden = action.kind !== "keyboard";
  $("media-usage-row").hidden = action.kind !== "media";
  $("layer-target-row").hidden = action.kind !== "layer";
  $("layer-mode-row").hidden = action.kind !== "layer";
  $("layer-seconds-row").hidden = action.kind !== "layer" || action.mode !== "timed";
  if (action.kind === "keyboard") {
    $("key-usage").value = String(action.usage);
    for (const input of $("modifiers-row").querySelectorAll("input")) {
      input.checked = !!(action.modifiers & (1 << Number(input.value)));
    }
  }
  if (action.kind === "media") $("media-usage").value = String(action.usage);
  if (action.kind === "layer") {
    fillSelect($("layer-target"), profile.layers.filter((item) => item.id !== state.layerId)
      .map((item) => ({ value: item.id, label: item.name })));
    $("layer-target").value = action.target;
    $("layer-mode").value = action.mode;
    $("layer-seconds").value = action.seconds || 5;
  }
  $("lighting-mode").value = layer().lighting.mode;
  $("preset-row").hidden = layer().lighting.mode !== "preset";
  $("key-color-row").hidden = layer().lighting.mode !== "static";
  if (layer().lighting.mode === "preset") $("preset").value = layer().lighting.preset;
  if (layer().lighting.mode === "static") renderColor();
}

function renderColor() {
  const color = layer().lighting.colors[state.selected];
  const rgb = KeybowColor.parseHex(color);
  const key = `${state.profile.id}:${state.layerId}:${state.selected}`;
  const hsv = KeybowColor.rgbToHsv(rgb);
  if (hsv.v === 0 && state.colorKey === key && state.colorHsv) {
    hsv.h = state.colorHsv.h;
    hsv.s = state.colorHsv.s;
  }
  state.colorHsv = hsv;
  state.colorKey = key;
  KeybowColor.drawWheel($("color-wheel"), hsv.v);
  const radians = hsv.h * Math.PI / 180;
  $("wheel-marker").style.left = `${50 + Math.cos(radians) * hsv.s * 48.75}%`;
  $("wheel-marker").style.top = `${50 + Math.sin(radians) * hsv.s * 48.75}%`;
  $("color-wheel").setAttribute("aria-valuenow", String(Math.round(hsv.h)));
  $("color-wheel").setAttribute("aria-valuetext", `Hue ${Math.round(hsv.h)} degrees, saturation ${Math.round(hsv.s * 100)} percent`);
  $("color-value").value = String(Math.round(hsv.v * 100));
  $("color-hex").value = color.toUpperCase();
  ["r", "g", "b"].forEach((channel, index) => $("color-" + channel).value = String(rgb[index]));
  $("selected-swatch").style.backgroundColor = color;
  for (const id of ["color-hex", "color-r", "color-g", "color-b"]) $(id).removeAttribute("aria-invalid");
  $("color-error").textContent = "";
}

function setColor(color, hsvHint = null) {
  layer().lighting.colors[state.selected] = color;
  state.lastColors = [...layer().lighting.colors];
  state.colorHsv = hsvHint || KeybowColor.rgbToHsv(KeybowColor.parseHex(color));
  state.colorKey = `${state.profile.id}:${state.layerId}:${state.selected}`;
  changed();
}

function invalidColor(message, fields) {
  $("color-error").textContent = message;
  for (const id of fields) $(id).setAttribute("aria-invalid", "true");
  $("save-profile").disabled = true;
}

function render() {
  $("profile-list").inert = state.updating;
  $("serial-port").disabled = state.updating;
  $("refresh-ports").disabled = state.updating;
  $("main").inert = state.updating;
  $("install-firmware").disabled = state.updating || !state.connected || !state.firmware?.supported ||
    !state.latest || !newerFirmware(state.latest.version, state.firmware.version);
  $("device-status").textContent = state.connected ? "Connected over USB" : "Keybow is disconnected";
  $("device-status").classList.toggle("online", state.connected);
  $("profile-title").textContent = state.profile ? state.profile.name : "Connect Keybow";
  $("profile-subtitle").textContent = state.profile
    ? `${state.profile.id === state.active ? "Active profile" : "Saved profile"}${state.dirty ? " · Unsaved changes" : ""}`
    : "Plug Keybow into this computer to edit its keys and lights.";
  $("save-profile").disabled = !state.profile || !state.connected || !state.layersReady || !state.dirty;
  $("activate-profile").disabled = !state.profile || !state.connected || state.profile.id === state.active || state.dirty;
  $("delete-profile").disabled = !state.profile || !state.connected || state.profile.id === state.active;
  $("add-profile").disabled = !state.connected || !state.layersReady;
  $("rename-profile").disabled = !state.profile || !state.connected || !state.layersReady;
  $("add-layer").disabled = !state.profile || !state.connected || !state.layersReady || state.profile.layers.length >= 4;
  $("rename-layer").disabled = !state.profile || !state.connected || !state.layersReady || state.layerId === "base";
  $("delete-layer").disabled = !state.profile || !state.connected || !state.layersReady || state.layerId === "base";
  renderProfiles();
  renderLayers();
  renderGrid();
  renderInspector();
}

function renderLayers() {
  const tabs = $("layer-tabs");
  tabs.replaceChildren();
  for (const item of state.profile?.layers || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "layer-tab";
    button.setAttribute("aria-pressed", String(item.id === state.layerId));
    button.textContent = item.name;
    button.addEventListener("click", () => {
      state.layerId = item.id;
      state.selected = 0;
      state.lastColors = layer().lighting.mode === "static" ? [...layer().lighting.colors] : null;
      render();
    });
    tabs.append(button);
  }
}

function changed() {
  state.dirty = true;
  render();
}

async function refresh(preferred) {
  const listing = await api("/api/profiles");
  state.ids = listing.ids;
  state.active = listing.active;
  state.names = {};
  await Promise.all(state.ids.map(async (id) => {
    try { state.names[id] = (await api(`/api/profiles/${id}`)).name; }
    catch { state.names[id] = id; }
  }));
  const next = preferred && state.ids.includes(preferred) ? preferred : state.active;
  await loadProfile(next);
}

async function loadProfile(id) {
  if (state.dirty && !confirm("Discard unsaved changes?")) return;
  try {
    state.profile = await api(`/api/profiles/${id}`);
    state.layerId = "base";
    await loadOptions(state.profile.layout || "us");
    state.selected = 0;
    state.dirty = false;
    if (layer().lighting.mode === "static") state.lastColors = [...layer().lighting.colors];
    tell("");
    render();
  } catch (error) { tell(error.message, true); }
}

async function startup() {
  await loadOptions("us");
  await refreshPorts();
  const status = await api("/api/status");
  state.connected = status.connected;
  state.layersReady = !!status.layersReady;
  state.selectedPort = status.selectedPort;
  if (status.connected) {
    try {
      await refresh();
      if (!state.layersReady) tell("Install the layer SD card update before saving with this editor.", true);
    }
    catch (error) { tell(error.message, true); }
  } else {
    tell(status.message || "Connect Keybow and refresh this page.", true);
  }
  render();
  await refreshFirmware();
}

async function refreshFirmware() {
  if (!state.connected) {
    state.firmware = null;
    $("firmware-current").textContent = "Connect Keybow to see its version.";
    render();
    return;
  }
  try {
    state.firmware = await api("/api/firmware");
    $("firmware-current").textContent = state.firmware.supported
      ? `Installed: ${state.firmware.version}${state.firmware.state === "idle" ? "" : ` · ${state.firmware.state}`}`
      : "One-time SD card upgrade required.";
  } catch (error) {
    $("firmware-current").textContent = error.message;
  }
  render();
}

$("check-firmware").addEventListener("click", async () => {
  $("firmware-message").textContent = "Checking GitHub releases…";
  try {
    await refreshFirmware();
    if (!state.firmware?.supported) throw new Error("Install the one-time SD card upgrade first.");
    state.latest = await api("/api/firmware/latest");
    $("firmware-latest").textContent = `Latest: ${state.latest.version}`;
    $("firmware-message").textContent = newerFirmware(state.latest.version, state.firmware.version)
      ? "A firmware update is available." : "Keybow is up to date.";
    render();
  } catch (error) { $("firmware-message").textContent = error.message; }
});

$("install-firmware").addEventListener("click", async () => {
  if (state.dirty && !confirm("Discard unsaved profile changes and update? Cancel to save them first.")) return;
  if (!confirm(`Install firmware ${state.latest.version}? Keybow will restart. Saved profiles will be backed up.`)) return;
  state.updating = true;
  $("firmware-progress").hidden = false;
  $("firmware-progress").value = 0;
  $("firmware-message").textContent = "Starting update…";
  render();
  try {
    await api("/api/firmware/update", { method: "POST", body: JSON.stringify({ tag: state.latest.tag }) });
    const timer = setInterval(async () => {
      try {
        const job = await api("/api/firmware/job");
        $("firmware-progress").value = job.percent;
        $("firmware-message").textContent = job.error || `${job.phase}${job.backup ? ` · Backup: ${job.backup}` : ""}`;
        if (!job.running) {
          clearInterval(timer);
          state.updating = false;
          state.dirty = false;
          await startup();
          if (job.error) $("firmware-message").textContent = `${job.error}${job.backup ? ` · Backup: ${job.backup}` : ""}`;
          else $("firmware-message").textContent = `Firmware updated. Profile backup: ${job.backup}`;
          $("firmware-progress").hidden = true;
          render();
        }
      } catch (error) {
        clearInterval(timer);
        state.updating = false;
        $("firmware-message").textContent = error.message;
        render();
      }
    }, 1000);
  } catch (error) {
    state.updating = false;
    $("firmware-message").textContent = error.message;
    $("firmware-progress").hidden = true;
    render();
  }
});

async function loadOptions(layout) {
  state.options = await api(`/api/options?layout=${layout}`);
  fillSelect($("keyboard-layout"), Object.entries(state.options.layouts).map(([value, label]) => ({ value, label })));
  fillSelect($("key-usage"), state.options.keys.map((item) => ({ value: item.usage, label: item.label })));
  const mac = layout === "de-macos" || (layout === "us" && state.options.hostPlatform === "darwin");
  $("alt-label").textContent = mac ? "Option" : "Alt";
  $("meta-label").textContent = mac ? "Command" : "Win / Super";
  fillSelect($("media-usage"), state.options.media.map((label, value) => ({ value, label })));
  fillSelect($("preset"), state.options.presets.map((preset) => ({
    value: preset, label: preset.replaceAll("-", " ").replace(/^./, (c) => c.toUpperCase()),
  })));
}

$("keyboard-layout").addEventListener("change", async (event) => {
  const target = event.target.value;
  try {
    const translated = await api("/api/translate", {
      method: "POST", body: JSON.stringify({ profile: state.profile, layout: target }),
    });
    state.profile = translated;
    await loadOptions(target);
    tell(`Profile will use ${state.options.layouts[target]} after saving.`);
    changed();
  } catch (error) {
    event.target.value = state.profile.layout;
    tell(error.message, true);
  }
});

$("action-kind").addEventListener("change", (event) => {
  const kind = event.target.value;
  if (kind === "layer" && state.profile.layers.length < 2) {
    tell("Add another layer before assigning a layer key.", true);
    render();
    return;
  }
  const action = kind === "keyboard"
    ? { kind, usage: 4, modifiers: 0 }
    : kind === "media" ? { kind, usage: 4 }
      : kind === "layer" ? { kind, target: state.profile.layers.find((item) => item.id !== state.layerId).id, mode: "toggle" }
        : { kind };
  if (!reserveTarget(action)) { render(); return; }
  layer().keys[state.selected] = action;
  changed();
});

function reserveTarget(action) {
  if (action.kind !== "layer" || action.mode !== "toggle") return true;
  const target = state.profile.layers.find((item) => item.id === action.target);
  const previous = target.keys[state.selected];
  if (previous.kind !== "none") {
    if (!confirm(`Key ${String(state.selected + 1).padStart(2, "0")} on ${target.name} is ${labelFor(previous)}. Replace it with a reserved return key?`)) return false;
    target.keys[state.selected] = { kind: "none" };
  }
  return true;
}

function changeLayerAction(update) {
  const action = { ...layer().keys[state.selected], ...update };
  if (action.mode === "timed") action.seconds = action.seconds || 5;
  else delete action.seconds;
  if (!reserveTarget(action)) { render(); return; }
  layer().keys[state.selected] = action;
  changed();
}

$("layer-target").addEventListener("change", (event) => changeLayerAction({ target: event.target.value }));
$("layer-mode").addEventListener("change", (event) => changeLayerAction({ mode: event.target.value }));
$("layer-seconds").addEventListener("change", (event) => {
  const seconds = Number(event.target.value);
  if (!Number.isInteger(seconds) || seconds < 1 || seconds > 3600) {
    tell("Choose a whole number of seconds from 1 to 3600.", true);
    render();
    return;
  }
  changeLayerAction({ seconds });
});
$("key-usage").addEventListener("change", (event) => {
  layer().keys[state.selected].usage = Number(event.target.value); changed();
});
$("media-usage").addEventListener("change", (event) => {
  layer().keys[state.selected].usage = Number(event.target.value); changed();
});
$("modifiers-row").addEventListener("change", () => {
  let mask = 0;
  for (const input of $("modifiers-row").querySelectorAll("input")) {
    if (input.checked) mask |= 1 << Number(input.value);
  }
  layer().keys[state.selected].modifiers = mask;
  changed();
});
$("lighting-mode").addEventListener("change", (event) => {
  if (event.target.value === "static") {
    layer().lighting = { mode: "static", colors: state.lastColors || Array(12).fill("#ffffff") };
  } else {
    state.lastColors = [...layer().lighting.colors];
    layer().lighting = { mode: "preset", preset: "default" };
  }
  changed();
});
$("preset").addEventListener("change", (event) => {
  layer().lighting.preset = event.target.value; changed();
});
$("color-hex").addEventListener("change", (event) => {
  const rgb = KeybowColor.parseHex(event.target.value.trim());
  if (!rgb) { invalidColor("Use a six-digit hex color, such as #3FA9D2.", ["color-hex"]); return; }
  setColor(KeybowColor.toHex(rgb));
});
for (const channel of ["r", "g", "b"]) {
  $("color-" + channel).addEventListener("change", () => {
    const fields = ["color-r", "color-g", "color-b"];
    const values = fields.map((id) => Number($(id).value));
    if (fields.some((id, index) => $(id).value.trim() === "" || !Number.isInteger(values[index]) || values[index] < 0 || values[index] > 255)) {
      invalidColor("RGB values must be whole numbers from 0 to 255.", fields);
      return;
    }
    setColor(KeybowColor.toHex(values));
  });
}
$("color-value").addEventListener("input", (event) => {
  const { h, s } = state.colorHsv;
  const next = { h, s, v: Number(event.target.value) / 100 };
  setColor(KeybowColor.toHex(KeybowColor.hsvToRgb(next.h, next.s, next.v)), next);
});
const wheel = $("color-wheel");
function updateWheel(event) {
  if (!state.profile || layer().lighting.mode !== "static") return;
  const { h, s } = KeybowColor.wheelPoint(event, wheel);
  const v = state.colorHsv?.v ?? 1;
  setColor(KeybowColor.toHex(KeybowColor.hsvToRgb(h, s, v)), { h, s, v });
}
wheel.addEventListener("pointerdown", (event) => { wheel.setPointerCapture(event.pointerId); updateWheel(event); });
wheel.addEventListener("pointermove", (event) => { if (wheel.hasPointerCapture(event.pointerId)) updateWheel(event); });
wheel.addEventListener("keydown", (event) => {
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
  if (!state.profile || layer().lighting.mode !== "static") return;
  event.preventDefault();
  const hsv = { ...state.colorHsv };
  if (event.key === "ArrowLeft") hsv.h -= 5;
  if (event.key === "ArrowRight") hsv.h += 5;
  if (event.key === "ArrowUp") hsv.s = Math.min(1, hsv.s + .05);
  if (event.key === "ArrowDown") hsv.s = Math.max(0, hsv.s - .05);
  setColor(KeybowColor.toHex(KeybowColor.hsvToRgb(hsv.h, hsv.s, hsv.v)), hsv);
});
$("save-profile").addEventListener("click", async () => {
  try {
    await api(`/api/profiles/${state.profile.id}`, { method: "PUT", body: JSON.stringify(state.profile) });
    state.dirty = false;
    state.names[state.profile.id] = state.profile.name;
    tell(state.profile.id === state.active ? "Saved and applied on Keybow." : "Profile saved on Keybow.");
    render();
  } catch (error) { tell(error.message, true); }
});
$("rename-profile").addEventListener("click", () => {
  const name = prompt("Profile name:", state.profile.name);
  if (name === null) return;
  if (!name.trim() || name.length > 48) { tell("Use 1–48 characters for the profile name.", true); return; }
  state.profile.name = name.trim();
  changed();
});
$("add-layer").addEventListener("click", () => {
  const name = prompt("Name for the new layer:", `Layer ${state.profile.layers.length + 1}`);
  if (name === null) return;
  if (!name.trim() || name.length > 48) { tell("Use 1–48 characters for the layer name.", true); return; }
  const slug = name.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 28) || "layer";
  let id = slug, suffix = 2;
  while (state.profile.layers.some((item) => item.id === id)) id = `${slug.slice(0, 27)}-${suffix++}`;
  state.profile.layers.push({ id, name: name.trim(),
    keys: Array.from({ length: 12 }, () => ({ kind: "none" })),
    lighting: structuredClone(layer().lighting) });
  state.layerId = id;
  state.selected = 0;
  changed();
});
$("rename-layer").addEventListener("click", () => {
  const name = prompt("Layer name:", layer().name);
  if (name === null) return;
  if (!name.trim() || name.length > 48) { tell("Use 1–48 characters for the layer name.", true); return; }
  layer().name = name.trim();
  changed();
});
$("delete-layer").addEventListener("click", () => {
  const references = state.profile.layers.flatMap((item) => item.keys
    .filter((action) => action.kind === "layer" && action.target === state.layerId)
    .map(() => item.name));
  if (references.length) {
    tell(`Change the layer keys in ${[...new Set(references)].join(", ")} before deleting this layer.`, true);
    return;
  }
  if (!confirm(`Delete ${layer().name} from this profile?`)) return;
  state.profile.layers = state.profile.layers.filter((item) => item.id !== state.layerId);
  state.layerId = "base";
  changed();
});
$("activate-profile").addEventListener("click", async () => {
  try {
    await api("/api/active", { method: "POST", body: JSON.stringify({ id: state.profile.id }) });
    state.active = state.profile.id;
    tell("Profile is active on Keybow.");
    render();
  } catch (error) { tell(error.message, true); }
});
$("add-profile").addEventListener("click", async () => {
  const name = prompt("Name for the new profile:");
  if (!name) return;
  const id = name.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 32);
  if (!id || state.ids.includes(id)) { tell("Choose a different profile name.", true); return; }
  const profile = await api("/api/template");
  profile.id = id;
  profile.name = name.trim();
  try {
    await api(`/api/profiles/${id}`, { method: "PUT", body: JSON.stringify(profile) });
    state.dirty = false;
    await refresh(id);
    tell("Profile created. Make it active when ready.");
  } catch (error) { tell(error.message, true); }
});
$("delete-profile").addEventListener("click", async () => {
  if (!confirm(`Delete ${state.profile.name} from Keybow?`)) return;
  try {
    await api(`/api/profiles/${state.profile.id}`, { method: "DELETE" });
    state.dirty = false;
    await refresh(state.active);
    tell("Profile deleted.");
  } catch (error) { tell(error.message, true); }
});

async function refreshPorts() {
  const result = await api("/api/ports");
  state.ports = result.ports;
  state.selectedPort = result.selected;
  fillSelect($("serial-port"), [{ value: "", label: "Automatic" },
    ...result.ports.map((port) => ({ value: port.device,
      label: `${port.likely ? "Keybow · " : ""}${port.label} (${port.device})` }))]);
  $("serial-port").value = result.selected || "";
}

$("refresh-ports").addEventListener("click", async () => {
  try {
    await refreshPorts();
    const status = await api("/api/status");
    state.connected = status.connected;
    state.layersReady = !!status.layersReady;
    if (status.connected) await refresh(state.profile?.id);
    else tell(status.message, true);
    render();
  } catch (error) { tell(error.message, true); }
});
$("serial-port").addEventListener("change", async (event) => {
  const previous = state.selectedPort || "";
  if (state.dirty && !confirm("Discard unsaved changes and change serial port?")) {
    event.target.value = previous;
    return;
  }
  try {
    await api("/api/port", { method: "POST", body: JSON.stringify({ device: event.target.value || null }) });
    state.dirty = false;
    state.profile = null;
    await startup();
  } catch (error) { event.target.value = previous; tell(error.message, true); }
});

startup().catch((error) => tell(error.message, true));
