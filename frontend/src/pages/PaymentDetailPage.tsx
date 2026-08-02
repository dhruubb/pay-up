import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { paymentsApi } from "../api/endpoints";
import type { Payment, PaymentEvent } from "../api/types";
import { formatPaise, formatDateTime } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";

export function PaymentDetailPage() {
  const { paymentId } = useParams<{ paymentId: string }>();
  const [payment, setPayment] = useState<Payment | null>(null);
  const [events, setEvents] = useState<PaymentEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!paymentId) return;
    Promise.all([paymentsApi.get(paymentId), paymentsApi.events(paymentId)]).then(
      ([p, e]) => {
        setPayment(p);
        setEvents(e);
        setLoading(false);
      },
    );
  }, [paymentId]);

  if (loading || !payment) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="max-w-xl space-y-6">
      <Link to="/payments" className="text-sm text-violet-700">
        ← Back to payments
      </Link>

      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">{formatPaise(payment.amount_paise)}</h1>
          <StatusBadge status={payment.status} />
        </div>
        <p className="mt-1 text-sm text-gray-500">Payment {payment.id}</p>
        {payment.failure_reason && (
          <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {payment.failure_reason}
          </p>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-lg font-medium">Event Trail</h2>
        <ol className="space-y-3">
          {events.map((ev) => (
            <li
              key={ev.id}
              className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{ev.event_type}</span>
                <span className="text-gray-400">{formatDateTime(ev.created_at)}</span>
              </div>
              <p className="mt-1 text-xs text-gray-400">
                {ev.published_at ? "published to Kafka" : "pending publish"}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
