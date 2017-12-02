const MAX_COMP = 50;
const N_SUPPORT = 40;
const NOTE_RADIUS_X = 30000, NOTE_RADIUS_Y = 300000;

function leftPad(str, len, char) {
  while (str.length < len) str = char + str;
  return str;
}

function toColourHex(num) {
  const comps = [num >> 16, num % (1 << 16) >> 8, num % (1 << 8)];
  return '#' + comps.map(c => leftPad(c.toString(16).toUpperCase(), 2, '0')).join('');
}

export async function preprocessImage(image) {
  const pixels = image.data;

  // Find the median centre of each colour
  const colourMap = {};
  for (let i = 0, y = 0; y < image.height; y++) {
    for (let x = 0; x < image.width; x++, i += 4) {
      if (pixels[i] === 0 || pixels[i+1] === 0 || pixels[i+2] === 0 ||
          pixels[i] > MAX_COMP || pixels[i+1] > MAX_COMP || pixels[i+2] > MAX_COMP)
        continue;
      const colour = pixels[i] * 256 * 256 + pixels[i+1] * 256 + pixels[i+2];
      colourMap[colour] = colourMap[colour] || {x: [], y: [], points: []};
      colourMap[colour].x.push(x);
      colourMap[colour].y.push(y);
      colourMap[colour].points.push({x, y});
    }
  }
  const out = {};
  for (const colour in colourMap) {
    if (!colourMap.hasOwnProperty(colour)) continue;
    const value = colourMap[colour];
    if (value.x.length < N_SUPPORT) continue;
    const colourCode = toColourHex(colour);
    value.x.sort();
    value.y.sort();
    const midIdx = Math.floor(value.x.length/2);
    const cx = value.x[midIdx], cy = value.y[midIdx];
    const points = value.points.filter(
      pt => Math.abs(pt.x - cx) <= NOTE_RADIUS_X && Math.abs(pt.y - cy <= NOTE_RADIUS_Y));
    if (points.length < N_SUPPORT) continue;
    out[colourCode] = {cx, cy, points};
  }

  // Make the image BW
  for (let i = 0; i < pixels.length; i += 4) {
    pixels[i] = pixels[i+1] = pixels[i+2] =
      (pixels[i] <= MAX_COMP && pixels[i+1] <= MAX_COMP && pixels[i+2] <= MAX_COMP) ? 0 : 255;
  }

  return out;
}
