export function formatPaise(paise: number): string {
  return `₹${(paise / 100).toFixed(2)}`;
}

export function rupeesToPaise(rupees: string): number {
  return Math.round(parseFloat(rupees) * 100);
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
