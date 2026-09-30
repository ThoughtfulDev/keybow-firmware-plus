/* Shared color math for the wheel and the hex/RGB fields. */
const KeybowColor = (() => {
  const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

  function parseHex(value) {
    if (!/^#[\da-f]{6}$/i.test(value)) return null;
    return [1, 3, 5].map((offset) => parseInt(value.slice(offset, offset + 2), 16));
  }

  function toHex(rgb) {
    return `#${rgb.map((part) => clamp(Math.round(part), 0, 255).toString(16).padStart(2, "0")).join("")}`;
  }

  function hsvToRgb(h, s, v) {
    const chroma = v * s;
    const segment = ((h % 360) + 360) % 360 / 60;
    const other = chroma * (1 - Math.abs(segment % 2 - 1));
    const parts = segment < 1 ? [chroma, other, 0]
      : segment < 2 ? [other, chroma, 0]
      : segment < 3 ? [0, chroma, other]
      : segment < 4 ? [0, other, chroma]
      : segment < 5 ? [other, 0, chroma] : [chroma, 0, other];
    const base = v - chroma;
    return parts.map((part) => Math.round((part + base) * 255));
  }

  function rgbToHsv(rgb) {
    const [r, g, b] = rgb.map((part) => part / 255);
    const high = Math.max(r, g, b), low = Math.min(r, g, b), delta = high - low;
    let h = 0;
    if (delta) {
      if (high === r) h = ((g - b) / delta) % 6;
      else if (high === g) h = (b - r) / delta + 2;
      else h = (r - g) / delta + 4;
      h = (h * 60 + 360) % 360;
    }
    return { h, s: high ? delta / high : 0, v: high };
  }

  function drawWheel(canvas, brightness) {
    const context = canvas.getContext("2d");
    const { width, height } = canvas;
    const image = context.createImageData(width, height);
    const radius = Math.min(width, height) / 2 - 3;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const dx = x - width / 2, dy = y - height / 2;
        const saturation = Math.hypot(dx, dy) / radius;
        if (saturation > 1) continue;
        const hue = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;
        const rgb = hsvToRgb(hue, saturation, brightness);
        const offset = (y * width + x) * 4;
        image.data.set([...rgb, 255], offset);
      }
    }
    context.putImageData(image, 0, 0);
  }

  function wheelPoint(event, canvas) {
    const bounds = canvas.getBoundingClientRect();
    const dx = (event.clientX - bounds.left) / bounds.width * canvas.width - canvas.width / 2;
    const dy = (event.clientY - bounds.top) / bounds.height * canvas.height - canvas.height / 2;
    return { h: (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360,
             s: clamp(Math.hypot(dx, dy) / (canvas.width / 2 - 3), 0, 1) };
  }

  return { parseHex, toHex, hsvToRgb, rgbToHsv, drawWheel, wheelPoint };
})();

if (typeof module !== "undefined") module.exports = KeybowColor;
