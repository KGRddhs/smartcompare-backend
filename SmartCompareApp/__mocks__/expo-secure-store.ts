/**
 * In-memory mock for expo-secure-store. Resets between tests via
 * the exported `__reset` helper.
 */
const store: Record<string, string> = {};

export async function getItemAsync(key: string): Promise<string | null> {
  return store[key] ?? null;
}

export async function setItemAsync(key: string, value: string): Promise<void> {
  store[key] = value;
}

export async function deleteItemAsync(key: string): Promise<void> {
  delete store[key];
}

export function __reset(): void {
  Object.keys(store).forEach((k) => delete store[k]);
}

export default {
  getItemAsync,
  setItemAsync,
  deleteItemAsync,
  __reset,
};
