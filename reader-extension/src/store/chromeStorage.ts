import type { StateStorage } from "zustand/middleware";

function hasChromeStorage(): boolean {
  return typeof chrome !== "undefined" && !!chrome.storage?.local;
}

/**
 * Zustand `persist` storage adapter backed by chrome.storage.local, with a
 * localStorage fallback so the store also works in plain browser contexts
 * (tests, `vite dev` preview outside the extension shell).
 */
export const chromeStorage: StateStorage = {
  getItem: async (name) => {
    if (hasChromeStorage()) {
      const result = await chrome.storage.local.get(name);
      return typeof result[name] === "string" ? result[name] : null;
    }
    return localStorage.getItem(name);
  },
  setItem: async (name, value) => {
    if (hasChromeStorage()) {
      await chrome.storage.local.set({ [name]: value });
      return;
    }
    localStorage.setItem(name, value);
  },
  removeItem: async (name) => {
    if (hasChromeStorage()) {
      await chrome.storage.local.remove(name);
      return;
    }
    localStorage.removeItem(name);
  },
};
