import { useEffect, useState } from "react";
import { notificationsApi } from "../api/endpoints";
import type { Notification } from "../api/types";
import { formatDateTime } from "../lib/format";

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    notificationsApi.list().then((n) => {
      setNotifications(n);
      setLoading(false);
    });
  }, []);

  if (loading) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Notifications</h1>

      {notifications.length === 0 ? (
        <p className="text-sm text-gray-500">Nothing yet.</p>
      ) : (
        <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
          {notifications.map((n) => (
            <li key={n.id} className="px-4 py-3 text-sm">
              <p>{n.message}</p>
              <p className="mt-1 text-xs text-gray-400">{formatDateTime(n.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
