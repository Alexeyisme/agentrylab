import type { PaletteId } from "../types";

// Keep in sync with src/agentrylab/room/avatars.py
export const PALETTES: Record<PaletteId, string> = {
  cyan: "#22d3ee",
  magenta: "#e879f9",
  lime: "#a3e635",
  amber: "#fbbf24",
  coral: "#fb7185",
  violet: "#a78bfa",
  mint: "#34d399",
  ice: "#93c5fd",
};

export const SHELL = {
  dark: "#1a1f2e",
  mid: "#283047",
  light: "#3a4460",
  line: "#0d1019",
  screen: "#0a0d16",
} as const;

export function accentFor(id: string): string {
  return PALETTES[id as PaletteId] ?? PALETTES.cyan;
}

/** Translucent version of a hex colour. */
export function alpha(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}
