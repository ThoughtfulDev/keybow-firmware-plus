/* Recorder and sequence controls. Record only while the capture field has focus. */
(function (root) {
  const codes = {};
  for (let i = 0; i < 26; i++) codes[`Key${String.fromCharCode(65 + i)}`] = 4 + i;
  for (let i = 1; i <= 9; i++) codes[`Digit${i}`] = 29 + i;
  Object.assign(codes, {Digit0:39, Enter:40, Escape:41, Backspace:42, Tab:43, Space:44,
    Minus:45, Equal:46, BracketLeft:47, BracketRight:48, Backslash:49, Semicolon:51,
    Quote:52, Backquote:53, Comma:54, Period:55, Slash:56, CapsLock:57, Insert:73,
    Home:74, PageUp:75, Delete:76, End:77, PageDown:78, ArrowRight:79, ArrowLeft:80,
    ArrowDown:81, ArrowUp:82, NumLock:83, NumpadDivide:84, NumpadMultiply:85,
    NumpadSubtract:86, NumpadAdd:87, NumpadEnter:88, Numpad0:98, NumpadDecimal:99,
    IntlBackslash:100, ContextMenu:101, NumpadEqual:103});
  for (let i = 1; i <= 12; i++) codes[`F${i}`] = 57 + i;
  for (let i = 13; i <= 24; i++) codes[`F${i}`] = 91 + i;
  for (let i = 1; i <= 9; i++) codes[`Numpad${i}`] = 88 + i;
  const modifierCodes = {ControlLeft:0, ShiftLeft:1, AltLeft:2, MetaLeft:3,
    ControlRight:4, ShiftRight:5, AltRight:6, MetaRight:7};
  const modifierNames = ["Left Control", "Left Shift", "Left Alt / Option", "Left Command / Win",
    "Right Control", "Right Shift", "Right Alt / AltGr", "Right Command / Win"];
  const mediaCodes = {MediaTrackNext:0, MediaTrackPrevious:1, MediaStop:2, Eject:3,
    MediaPlayPause:4, AudioVolumeMute:5, AudioVolumeUp:6, AudioVolumeDown:7};
  function physical(code) {
    if (code in modifierCodes) return {device:"modifier", usage:modifierCodes[code]};
    if (code in mediaCodes) return {device:"media", usage:mediaCodes[code]};
    return code in codes ? {device:"keyboard", usage:codes[code]} : null;
  }
  class Recorder {
    constructor(clock = () => performance.now()) { this.clock = clock; this.steps = []; this.down = new Map(); this.last = null; }
    push(item) {
      const now = this.clock();
      if (this.last !== null && Math.round(now - this.last) > 0) this.steps.push({kind:"delay", ms:Math.round(now - this.last)});
      this.steps.push({kind:"event", ...item}); this.last = now;
    }
    input(event) {
      if (event.repeat || event.isComposing) return false;
      const item = physical(event.code); if (!item) return false;
      const pressed = event.type === "keydown";
      // WebKit/native input can carry flags without separate modifier events.
      // Infer missing flags while preserving explicit left/right modifier keys.
      for (const [flag, left, right] of [["ctrlKey","ControlLeft","ControlRight"],
        ["shiftKey","ShiftLeft","ShiftRight"], ["altKey","AltLeft","AltRight"], ["metaKey","MetaLeft","MetaRight"]]) {
        if (typeof event[flag] !== "boolean" || event.code === left || event.code === right) continue;
        if (event[flag] && !this.down.has(left) && !this.down.has(right)) {
          const modifier = physical(left); this.down.set(left, modifier); this.push({...modifier, pressed:true});
        } else if (!event[flag]) {
          for (const code of [left, right]) {
            if (this.down.has(code)) { this.push({...this.down.get(code), pressed:false}); this.down.delete(code); }
          }
        }
      }
      if (pressed === this.down.has(event.code)) return false;
      if (pressed) this.down.set(event.code, item); else this.down.delete(event.code);
      this.push({...item, pressed}); return true;
    }
    finish() {
      for (const item of [...this.down.values()].reverse()) this.push({...item, pressed:false});
      this.down.clear(); return this.steps;
    }
  }
  root.KeybowSequences = {Recorder, physical};
  if (typeof module !== "undefined") module.exports = root.KeybowSequences;
  if (typeof document === "undefined") return;
  const $ = (id) => document.getElementById(id);
  let action = null, options = null, notify = null, recording = null, onRecording = null;
  function select(entries, value, update, label) {
    const el = document.createElement("select"); el.setAttribute("aria-label", label);
    for (const [val, text] of entries) { const option = document.createElement("option"); option.value = val; option.textContent = text; el.append(option); }
    el.value = String(value); el.addEventListener("change", () => update(el.value)); return el;
  }
  function number(value, low, high, update, label) {
    const el = document.createElement("input"); el.type = "number"; el.min = low; el.max = high; el.value = value;
    el.setAttribute("aria-label", label); el.addEventListener("change", () => update(Number(el.value))); return el;
  }
  function text(value, update, label) {
    const el = document.createElement("textarea"); el.rows = 3; el.value = value; el.setAttribute("aria-label", label);
    el.addEventListener("change", () => update(el.value)); return el;
  }
  function keyEntries(device) {
    return device === "modifier" ? modifierNames.map((name, i) => [i, name]) :
      device === "media" ? options.media.map((name, i) => [i, name]) : [...options.keys.filter(item => item.usage <= 115).map(item => [item.usage, item.label]), [83, "Num Lock"], [101, "Context menu"]];
  }
  function draw() {
    const list = $("macro-events"); list.replaceChildren();
    if (!action || action.kind !== "macro") return;
    $("macro-count").textContent = `${action.steps.length} / 256 events`;
    if (!action.steps.length) { const empty = document.createElement("p"); empty.className = "field-help"; empty.textContent = "Record a sequence or add an event below."; list.append(empty); }
    action.steps.forEach((step, index) => {
      const row = document.createElement("li"); row.className = "macro-event";
      const caption = document.createElement("span"); caption.textContent = `${index + 1}. ${step.kind === "event" ? "Recorded key" : step.kind}`; row.append(caption);
      const update = (field, value) => { step[field] = value; notify(); };
      if (step.kind === "delay") row.append(number(step.ms, 0, 120000, value => update("ms", value), "Delay in milliseconds"));
      if (step.kind === "text") row.append(text(step.text, value => update("text", value), "Macro text"));
      if (["event", "keyboard", "media"].includes(step.kind)) {
        if (step.kind === "event") row.append(select([["keyboard","Keyboard"],["modifier","Modifier"],["media","Media"]], step.device,
          value => { step.device = value; step.usage = value === "keyboard" ? 4 : 0; notify(); }, "Recorded device"));
        row.append(select(keyEntries(step.device || step.kind), step.usage, value => update("usage", Number(value)), "Key or media control"));
        if (step.kind === "event") row.append(select([["true","Press"],["false","Release"]], step.pressed, value => update("pressed", value === "true"), "Press or release"));
        if (step.kind === "keyboard") {
          const group = document.createElement("div"); group.className = "modifiers";
          [0,1,2,3,6].forEach(bit => { const label = document.createElement("label"), input = document.createElement("input"); input.type="checkbox"; input.checked=!!(step.modifiers & (1<<bit));
            input.addEventListener("change", () => update("modifiers", input.checked ? step.modifiers | (1<<bit) : step.modifiers & ~(1<<bit)));
            label.append(input, modifierNames[bit]); group.append(label); }); row.append(group);
        }
      }
      const insert = document.createElement("button"); insert.type="button"; insert.className="text-button"; insert.textContent="Insert before";
      insert.setAttribute("aria-label", `Insert before event ${index+1}`); insert.disabled = action.steps.length >= 256;
      insert.addEventListener("click", () => { action.steps.splice(index, 0, newStep()); notify(); }); row.append(insert);
      const remove = document.createElement("button"); remove.type="button"; remove.className="text-button"; remove.textContent="Delete"; remove.setAttribute("aria-label", `Delete event ${index+1}`);
      remove.addEventListener("click", () => { action.steps.splice(index, 1); notify(); }); row.append(remove); list.append(row);
    });
  }
  function finish(cancel = false) {
    if (!recording) return;
    const current = recording; recording = null; clearTimeout(current.timeout);
    const modified = !cancel && current.recorder.steps.length > 0;
    if (modified) current.action.steps = current.recorder.finish();
    $("record-status").textContent = cancel ? "Recording cancelled." : "Recording stopped. Review the events before saving.";
    $("macro-capture").textContent = "Focus here to record. Escape stops recording.";
    if (onRecording) onRecording(false);
    if (modified) notify();
  }
  $("record-start").addEventListener("click", () => {
    if (recording) return;
    recording = {action, recorder:new Recorder(), timeout:setTimeout(() => finish(), 115000)};
    $("record-status").textContent = "Recording… Escape stops. Stop replaces the current event list; Cancel keeps it.";
    $("macro-capture").textContent = "Recording keyboard events…";
    if (onRecording) onRecording(true);
    $("record-stop").disabled = false; $("record-cancel").disabled = false; $("macro-capture").focus();
  });
  for (const id of ["record-stop", "record-cancel"]) $(id).addEventListener("pointerdown", event => event.preventDefault());
  $("record-stop").addEventListener("click", () => finish());
  $("record-cancel").addEventListener("click", () => finish(true));
  $("macro-capture").addEventListener("blur", () => finish());
  for (const type of ["keydown", "keyup"]) $("macro-capture").addEventListener(type, event => {
    if (!recording) return;
    event.preventDefault(); event.stopPropagation();
    if (event.code === "Escape") { if (type === "keydown") finish(); return; }
    if (event.isComposing || event.key === "Process") { $("record-status").textContent="IME composition cannot be recorded; add supported text manually."; return; }
    if (recording.recorder.steps.length >= 190 || recording.recorder.down.size >= 20) { finish(); return; }
    const captured = recording.recorder.input(event);
    if (!captured && !event.repeat && !physical(event.code)) $("record-status").textContent=`Unsupported key: ${event.code || event.key}. Add it manually if available.`;
    $("macro-capture").textContent = `${recording.recorder.steps.length} events recorded`;
    if (recording.recorder.steps.length >= 190) finish();
  });
  function newStep() {
    const kind = $("macro-insert-kind").value;
    return kind === "delay" ? {kind,ms:100} : kind === "text" ? {kind,text:"Text"} :
      kind === "keyboard" ? {kind,usage:4,modifiers:0} : kind === "media" ? {kind,usage:4} : {kind:"event",device:"keyboard",usage:4,pressed:kind === "press"};
  }
  $("macro-add").addEventListener("click", () => { action.steps.push(newStep()); notify(); });
  $("type-text").addEventListener("input", event => { action.text = event.target.value; notify(); });
  root.KeybowSequences.render = (next, nextOptions, enabled, change, recordingChanged) => {
    if (recording && recording.action !== next) finish(true);
    action = next; options = nextOptions; notify = change; onRecording = recordingChanged;
    $("text-action").hidden = !action || action.kind !== "text";
    $("macro-action").hidden = !action || action.kind !== "macro";
    $("type-text").disabled = !enabled; $("type-text").value = action?.text || "";
    $("record-start").disabled = !enabled || !!recording;
    $("record-stop").disabled = $("record-cancel").disabled = !recording;
    $("macro-add").disabled = !enabled || !!recording || (action?.steps?.length || 0) >= 256;
    $("macro-events").inert = !enabled || !!recording;
    $("macro-capture").tabIndex = enabled ? 0 : -1;
    draw();
  };
})(typeof window === "undefined" ? globalThis : window);
