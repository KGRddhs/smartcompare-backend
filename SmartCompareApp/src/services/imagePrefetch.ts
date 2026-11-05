/**
 * S81-G6 CL2 CLIENT-SPEED -- warm the image cache for the two product images
 * when a result arrives, so the Results cards paint them sooner.
 *
 * Fire-and-forget: never awaited, never throws, a rejection is swallowed by
 * an attached catch, nothing is logged (no URL ever reaches a log). Bounded:
 * the first two products only, absolute https URLs of at most 2048 chars, and
 * a FIFO memory of the last 32 URLs so the Home call and the Results effect
 * for the same result prefetch once. Image.prefetch is read at call time and
 * guarded (the jest react-native mock has none).
 */
import { Image } from 'react-native';

const PREFETCH_MAX_URLS = 2;
const PREFETCH_URL_MAX_LEN = 2048;
const PREFETCH_SEEN_MAX = 32;

const prefetchedUrls: string[] = [];

function rememberUrl(url: string): void {
  prefetchedUrls.push(url);
  while (prefetchedUrls.length > PREFETCH_SEEN_MAX) {
    prefetchedUrls.shift();
  }
}

function productsOf(result: unknown): unknown[] {
  if (!result || typeof result !== 'object') return [];
  const r = result as { overview?: { products?: unknown }; products?: unknown };
  const products = r.overview?.products ?? r.products;
  return Array.isArray(products) ? products : [];
}

function imageUrlOf(product: unknown): string | null {
  if (!product || typeof product !== 'object') return null;
  const url = (product as { image_url?: unknown }).image_url;
  if (typeof url !== 'string') return null;
  if (!url.startsWith('https://') || url.length > PREFETCH_URL_MAX_LEN) return null;
  return url;
}

export function prefetchProductImages(result: unknown): void {
  const image = Image as unknown as { prefetch?: (url: string) => unknown } | undefined;
  if (!image || typeof image.prefetch !== 'function') return;
  const urls = productsOf(result)
    .slice(0, PREFETCH_MAX_URLS)
    .map(imageUrlOf)
    .filter((url): url is string => url !== null);
  for (const url of urls) {
    if (prefetchedUrls.includes(url)) continue;
    rememberUrl(url);
    try {
      const pending = image.prefetch(url) as { catch?: (onRejected: () => void) => unknown } | null;
      if (pending && typeof pending.catch === 'function') {
        pending.catch(() => undefined);
      }
    } catch {
      // A synchronous failure never reaches the render path.
    }
  }
}
