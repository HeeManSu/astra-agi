import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Parse a timestamp string from the backend, defaulting to UTC if no timezone
 * marker is present. Naive ISO strings (e.g. "2026-05-24T02:09:43.123") would
 * otherwise be interpreted as the browser's local time, which produces a wrong
 * "X hours ago" offset when the backend actually wrote UTC. Old DB rows
 * (pre-tz-fix) emit naive strings; this helper keeps them rendering correctly.
 */
export function parseTimestamp(value: string | Date | null | undefined): Date {
  if (value == null) return new Date(NaN);
  if (value instanceof Date) return value;

  // Already has a tz marker (Z, +HH:MM, or -HH:MM in the time portion)?
  // Test for: trailing Z, or a +/- followed by digits after the "T".
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(value);
  return new Date(hasTz ? value : value + "Z");
}
