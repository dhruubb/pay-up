const COLORS: Record<string, string> = {
  SUCCESS: "bg-green-100 text-green-800",
  ACTIVE: "bg-green-100 text-green-800",
  SENT: "bg-green-100 text-green-800",
  PROCESSING: "bg-yellow-100 text-yellow-800",
  INITIATED: "bg-yellow-100 text-yellow-800",
  FAILED: "bg-red-100 text-red-800",
  FROZEN: "bg-red-100 text-red-800",
  CLOSED: "bg-gray-200 text-gray-700",
};

export function StatusBadge({ status }: { status: string }) {
  const classes = COLORS[status] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>
      {status}
    </span>
  );
}
