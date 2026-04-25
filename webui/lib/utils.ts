import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimestamp(iso: string) {
  const date = new Date(iso);
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    hour12: false,
  }) + " UTC";
}

export function formatNumber(value: number) {
  if (Math.abs(value) >= 1000) return value.toLocaleString();
  if (Number.isInteger(value)) return value.toString();
  return value.toFixed(2);
}
