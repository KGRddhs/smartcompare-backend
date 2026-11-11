/**
 * S81-11 -- the per-session reading of the cached /app/version body.
 *
 * Pure: no React import at module scope beyond the hook, no copy, no
 * network. Fed ONLY from appVersionService.checkForcedUpdate (one record per
 * successful version read); absent / invalid keys = ABSENT (the
 * fragrance-only row, no selected_category).
 */
import { useEffect, useState } from 'react';

export type LaunchSurfaces = {
  categoriesLive: readonly string[] | null;
  surfaces: { skincare: boolean; makeup: boolean };
};

export const ABSENT_LAUNCH_SURFACES: LaunchSurfaces = {
  categoriesLive: null,
  surfaces: { skincare: false, makeup: false },
};

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

export function parseLaunchSurfaces(payload: unknown): LaunchSurfaces {
  if (!isPlainObject(payload)) return ABSENT_LAUNCH_SURFACES;
  const rawLive = payload.categories_live;
  let categoriesLive: string[] | null = null;
  if (Array.isArray(rawLive) && rawLive.every((x) => typeof x === 'string')) {
    categoriesLive = (rawLive as string[]).map((s) => s.trim().toLowerCase());
  }
  const rawSurfaces = payload.surfaces;
  const surfaces = { skincare: false, makeup: false };
  if (isPlainObject(rawSurfaces)) {
    surfaces.skincare = rawSurfaces.skincare === true;
    surfaces.makeup = rawSurfaces.makeup === true;
  }
  return { categoriesLive, surfaces };
}

let current: LaunchSurfaces = ABSENT_LAUNCH_SURFACES;
const listeners = new Set<(s: LaunchSurfaces) => void>();

export function recordLaunchSurfaces(payload: unknown): void {
  try {
    current = parseLaunchSurfaces(payload);
  } catch {
    current = ABSENT_LAUNCH_SURFACES;
  }
  listeners.forEach((fn) => {
    try {
      fn(current);
    } catch {
      // a listener never breaks the version read
    }
  });
}

export function getLaunchSurfaces(): LaunchSurfaces {
  return current;
}

export function subscribeLaunchSurfaces(fn: (s: LaunchSurfaces) => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export function useLaunchSurfaces(): LaunchSurfaces {
  const [value, setValue] = useState<LaunchSurfaces>(current);
  useEffect(() => {
    setValue(current);
    return subscribeLaunchSurfaces(setValue);
  }, []);
  return value;
}

export function categoryToSend(selected: string | null, s: LaunchSurfaces): string | undefined {
  if (selected !== 'fragrances') return undefined;
  if (!s.categoriesLive || !s.categoriesLive.includes('fragrances')) return undefined;
  return 'fragrances';
}

/** Tests only. */
export function __resetLaunchSurfaces(): void {
  current = ABSENT_LAUNCH_SURFACES;
  listeners.clear();
}
