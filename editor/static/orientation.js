/* Display coordinates only: profile keys always retain their physical indices. */
(function (root) {
  const storageKey = "keybow-editor-orientation";
  const valid = (angle) => [0, 90, 180, 270].includes(angle);
  function view(angle) {
    angle = valid(angle) ? angle : 0;
    let rows = [[11, 8, 5, 2], [10, 7, 4, 1], [9, 6, 3, 0]];
    for (let turn = 0; turn < angle / 90; turn++) {
      rows = rows[0].map((_, column) => rows.map((row) => row[column]).reverse());
    }
    return { angle, columns: rows[0].length, order: rows.flat(),
      edge: {0: "top", 90: "right", 180: "bottom", 270: "left"}[angle] };
  }
  function read(storage) {
    try {
      const value = storage.getItem(storageKey);
      return ["0", "90", "180", "270"].includes(value) ? Number(value) : 0;
    } catch (_) { return 0; }
  }
  function write(storage, angle) {
    try { storage.setItem(storageKey, String(valid(angle) ? angle : 0)); } catch (_) { /* Optional cache. */ }
  }
  const api = {view, read, write, valid};
  if (typeof module !== "undefined") module.exports = api;
  else root.KeybowOrientation = api;
})(globalThis);
