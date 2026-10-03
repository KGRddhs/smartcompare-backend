/**
 * Session 70 U4b (spec R9) — a minimal PNG reader for the launcher-art pins in
 * __tests__/config/nativeBundle.w37.test.ts.
 *
 * NOT a test file (jest's `testMatch` only collects `*.test.ts(x)`).
 *
 * WHY THIS EXISTS. jest.config.js maps `\.(png|…)$` to __mocks__/fileStub.ts,
 * so an imported PNG is the STUB, and the repo declares no PNG decoder:
 * `pngjs` / `parse-png` / `jimp-compact` exist only transitively (under
 * @expo/image-utils) and must not be imported by a test. Node's built-in
 * `zlib.inflateSync` is enough for the only shapes the renderer writes.
 *
 * Scope, deliberately narrow: bit depth 8, colour type 2 (RGB) or 6 (RGBA),
 * interlace 0 (non-interlaced). Anything else throws
 * `Error('pngDecode: unsupported <field> <value>')`. Every IDAT chunk is
 * concatenated before inflating (the committed master carries 37 of them —
 * spec review correction 1). Chunk CRCs are skipped, not verified. The pixel
 * layout returned is Pillow's `Image.tobytes()` for RGB / RGBA (row-major, 3
 * or 4 bytes per pixel, straight — not premultiplied — alpha), so a sha256 of
 * `pixels` can be compared with the renderer's manifest `pixels_sha256`.
 */
import * as zlib from 'zlib';

export interface PngChunk {
  type: string;
  data: Buffer;
  /** Byte offset of the chunk's length field. */
  offset: number;
}

export interface PngIhdr {
  width: number;
  height: number;
  bitDepth: number;
  colorType: number;
  interlace: number;
}

export interface DecodedPng {
  width: number;
  height: number;
  channels: 3 | 4;
  pixels: Uint8Array;
}

export const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/** Walks length / type / data / CRC from offset 8; stops after IEND. */
export function pngChunks(buf: Buffer): PngChunk[] {
  if (buf.length < 8 || !buf.subarray(0, 8).equals(PNG_SIGNATURE)) {
    throw new Error('pngDecode: bad signature');
  }
  const out: PngChunk[] = [];
  let pos = 8;
  while (pos < buf.length) {
    if (pos + 12 > buf.length) throw new Error(`pngDecode: truncated chunk header at ${pos}`);
    const length = buf.readUInt32BE(pos);
    const type = buf.toString('latin1', pos + 4, pos + 8);
    const start = pos + 8;
    const end = start + length;
    if (end + 4 > buf.length) throw new Error(`pngDecode: truncated chunk ${type} at ${pos}`);
    out.push({ type, data: buf.subarray(start, end), offset: pos });
    pos = end + 4; // the 4-byte CRC is skipped, not verified
    if (type === 'IEND') break;
  }
  return out;
}

function ihdrOf(chunks: PngChunk[]): PngIhdr {
  const first = chunks[0];
  if (first === undefined || first.type !== 'IHDR' || first.data.length !== 13) {
    throw new Error('pngDecode: the first chunk is not a 13-byte IHDR');
  }
  const d = first.data;
  return {
    width: d.readUInt32BE(0),
    height: d.readUInt32BE(4),
    bitDepth: d[8],
    colorType: d[9],
    interlace: d[12],
  };
}

/** `{ width, height, bitDepth, colorType, interlace }`; throws unless the first chunk is IHDR. */
export function readIhdr(buf: Buffer): PngIhdr {
  return ihdrOf(pngChunks(buf));
}

function paeth(a: number, b: number, c: number): number {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  if (pb <= pc) return b;
  return c;
}

/** Decodes an 8-bit, non-interlaced RGB or RGBA PNG into straight-alpha pixels. */
export function decodePng(buf: Buffer): DecodedPng {
  const chunks = pngChunks(buf);
  const { width, height, bitDepth, colorType, interlace } = ihdrOf(chunks);
  if (bitDepth !== 8) throw new Error(`pngDecode: unsupported bitDepth ${bitDepth}`);
  if (colorType !== 2 && colorType !== 6) throw new Error(`pngDecode: unsupported colorType ${colorType}`);
  if (interlace !== 0) throw new Error(`pngDecode: unsupported interlace ${interlace}`);
  const channels: 3 | 4 = colorType === 6 ? 4 : 3;

  const idat = chunks.filter((c) => c.type === 'IDAT').map((c) => c.data);
  if (idat.length === 0) throw new Error('pngDecode: no IDAT chunk');
  const raw = zlib.inflateSync(Buffer.concat(idat));

  const stride = width * channels;
  const expected = height * (stride + 1);
  if (raw.length !== expected) {
    throw new Error(`pngDecode: inflated ${raw.length} bytes, expected ${expected}`);
  }

  const bpp = channels;
  const pixels = new Uint8Array(height * stride);
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    const src = y * (stride + 1) + 1;
    const dst = y * stride;
    const up = dst - stride; // the previous output row; read only when y > 0
    switch (filter) {
      case 0:
        for (let x = 0; x < stride; x++) pixels[dst + x] = raw[src + x];
        break;
      case 1:
        for (let x = 0; x < stride; x++) {
          const a = x >= bpp ? pixels[dst + x - bpp] : 0;
          pixels[dst + x] = (raw[src + x] + a) & 0xff;
        }
        break;
      case 2:
        for (let x = 0; x < stride; x++) {
          const b = y > 0 ? pixels[up + x] : 0;
          pixels[dst + x] = (raw[src + x] + b) & 0xff;
        }
        break;
      case 3:
        for (let x = 0; x < stride; x++) {
          const a = x >= bpp ? pixels[dst + x - bpp] : 0;
          const b = y > 0 ? pixels[up + x] : 0;
          pixels[dst + x] = (raw[src + x] + ((a + b) >> 1)) & 0xff;
        }
        break;
      case 4:
        for (let x = 0; x < stride; x++) {
          const a = x >= bpp ? pixels[dst + x - bpp] : 0;
          const b = y > 0 ? pixels[up + x] : 0;
          const c = x >= bpp && y > 0 ? pixels[up + x - bpp] : 0;
          pixels[dst + x] = (raw[src + x] + paeth(a, b, c)) & 0xff;
        }
        break;
      default:
        throw new Error(`pngDecode: unsupported filter ${filter}`);
    }
  }
  return { width, height, channels, pixels };
}
