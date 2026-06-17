#!/usr/bin/env node
const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");

const size = 256;
const pixels = Buffer.alloc(size * size * 4);

const black = [3, 3, 2, 255];
const lineColor = [255, 178, 26, 255];
const lineSoft = [255, 209, 95, 185];

function setPixel(x, y, r, g, b, a) {
  if (x < 0 || y < 0 || x >= size || y >= size) return;
  const index = (y * size + x) * 4;
  pixels[index] = r;
  pixels[index + 1] = g;
  pixels[index + 2] = b;
  pixels[index + 3] = a;
}

function blendPixel(x, y, r, g, b, a) {
  if (x < 0 || y < 0 || x >= size || y >= size) return;
  const index = (y * size + x) * 4;
  const alpha = a / 255;
  const oldAlpha = pixels[index + 3] / 255;
  const outAlpha = alpha + oldAlpha * (1 - alpha);
  if (outAlpha <= 0) return;
  pixels[index] = Math.round((r * alpha + pixels[index] * oldAlpha * (1 - alpha)) / outAlpha);
  pixels[index + 1] = Math.round((g * alpha + pixels[index + 1] * oldAlpha * (1 - alpha)) / outAlpha);
  pixels[index + 2] = Math.round((b * alpha + pixels[index + 2] * oldAlpha * (1 - alpha)) / outAlpha);
  pixels[index + 3] = Math.round(outAlpha * 255);
}

function roundedRect(x0, y0, x1, y1, radius, color) {
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      const dx = x < x0 + radius ? x0 + radius - x : x > x1 - radius ? x - (x1 - radius) : 0;
      const dy = y < y0 + radius ? y0 + radius - y : y > y1 - radius ? y - (y1 - radius) : 0;
      if (dx * dx + dy * dy <= radius * radius) blendPixel(x, y, ...color);
    }
  }
}

function rect(x0, y0, x1, y1, color) {
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) blendPixel(x, y, ...color);
  }
}

function line(x0, y0, x1, y1, width, color) {
  const minX = Math.floor(Math.min(x0, x1) - width);
  const maxX = Math.ceil(Math.max(x0, x1) + width);
  const minY = Math.floor(Math.min(y0, y1) - width);
  const maxY = Math.ceil(Math.max(y0, y1) + width);
  const vx = x1 - x0;
  const vy = y1 - y0;
  const len2 = vx * vx + vy * vy;
  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      const t = Math.max(0, Math.min(1, ((x - x0) * vx + (y - y0) * vy) / len2));
      const px = x0 + t * vx;
      const py = y0 + t * vy;
      const d = Math.hypot(x - px, y - py);
      if (d <= width / 2) blendPixel(x, y, ...color);
    }
  }
}

function bezierPoint(points, t) {
  if (points.length === 3) {
    const [p0, p1, p2] = points;
    const mt = 1 - t;
    return {
      x: mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
      y: mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
    };
  }
  const [p0, p1, p2, p3] = points;
  const mt = 1 - t;
  return {
    x: mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
    y: mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]
  };
}

function curve(points, width, color, steps = 90) {
  let prev = bezierPoint(points, 0);
  for (let i = 1; i <= steps; i += 1) {
    const next = bezierPoint(points, i / steps);
    line(prev.x, prev.y, next.x, next.y, width, color);
    prev = next;
  }
}

function polygon(points, color) {
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const minX = Math.floor(Math.min(...xs));
  const maxX = Math.ceil(Math.max(...xs));
  const minY = Math.floor(Math.min(...ys));
  const maxY = Math.ceil(Math.max(...ys));
  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      let inside = false;
      for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
        const [xi, yi] = points[i];
        const [xj, yj] = points[j];
        const intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
        if (intersect) inside = !inside;
      }
      if (inside) blendPixel(x, y, ...color);
    }
  }
}

roundedRect(12, 12, 244, 244, 28, black);
roundedRect(14, 14, 242, 242, 26, [0, 0, 0, 255]);

line(34, 218, 34, 68, 9, lineColor);
curve([[34, 218], [56, 218], [58, 191], [58, 168]], 9, lineColor, 60);
line(58, 168, 58, 77, 9, lineColor);
line(58, 77, 82, 96, 9, lineColor);
curve([[82, 96], [101, 114], [108, 184], [128, 190]], 9, lineColor, 80);
curve([[128, 190], [153, 193], [162, 118], [190, 78]], 9, lineColor, 85);
line(190, 78, 214, 61, 9, lineColor);
line(214, 61, 214, 168, 9, lineColor);
curve([[214, 168], [214, 191], [216, 218], [238, 218]], 9, lineColor, 60);
line(238, 218, 238, 55, 9, lineColor);

line(49, 218, 49, 84, 4, lineSoft);
curve([[49, 218], [72, 218], [73, 193], [73, 170]], 4, lineSoft, 60);
line(73, 170, 73, 94, 4, lineSoft);
curve([[73, 94], [93, 114], [103, 174], [128, 176]], 4, lineSoft, 80);
curve([[128, 176], [153, 174], [162, 113], [200, 76]], 4, lineSoft, 85);
line(200, 76, 226, 61, 4, lineSoft);
line(226, 61, 226, 172, 4, lineSoft);
curve([[226, 172], [226, 194], [228, 218], [241, 218]], 4, lineSoft, 60);

for (let y = 16; y < 242; y++) {
  for (let x = 16; x < 242; x++) {
    if (y < 78) blendPixel(x, y, 255, 255, 255, 10);
  }
}

const pngRows = Buffer.alloc((size * 4 + 1) * size);
for (let y = 0; y < size; y++) {
  const src = y * size * 4;
  const dst = y * (size * 4 + 1);
  pixels.copy(pngRows, dst + 1, src, src + size * 4);
}

function pngChunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const name = Buffer.from(type);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([name, data])));
  return Buffer.concat([length, name, data, crc]);
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let k = 0; k < 8; k++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

const header = Buffer.alloc(13);
header.writeUInt32BE(size, 0);
header.writeUInt32BE(size, 4);
header[8] = 8;
header[9] = 6;
header[10] = 0;
header[11] = 0;
header[12] = 0;

const png = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  pngChunk("IHDR", header),
  pngChunk("IDAT", zlib.deflateSync(pngRows)),
  pngChunk("IEND", Buffer.alloc(0))
]);

const icoHeader = Buffer.alloc(22);
icoHeader.writeUInt16LE(0, 0);
icoHeader.writeUInt16LE(1, 2);
icoHeader.writeUInt16LE(1, 4);
icoHeader[6] = 0;
icoHeader[7] = 0;
icoHeader[8] = 0;
icoHeader[9] = 0;
icoHeader.writeUInt16LE(1, 10);
icoHeader.writeUInt16LE(32, 12);
icoHeader.writeUInt32LE(png.length, 14);
icoHeader.writeUInt32LE(22, 18);

const outDir = path.join(__dirname, "..", "assets");
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "icon.png"), png);
fs.writeFileSync(path.join(outDir, "icon.ico"), Buffer.concat([icoHeader, png]));
console.log("assets/icon.png");
console.log("assets/icon.ico");
