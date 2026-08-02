import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { accountsApi, paymentsApi } from "../api/endpoints";
import type { Payment } from "../api/types";
import { formatPaise, formatDateTime } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";

export function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [myAccountIds, setMyAccountIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [paymentList, accounts] = await Promise.all([
        paymentsApi.list(),
        accountsApi.list(),
      ]);
      setPayments(paymentList);
      setMyAccountIds(new Set(accounts.map((a) => a.id)));
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Payments</h1>

      {payments.length === 0 ? (
        <p className="text-sm text-gray-500">No payments yet.</p>
      ) : (
        <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
          {payments.map((p) => {
            const isSender = myAccountIds.has(p.sender_account_id);
            return (
              <li key={p.id}>
                <Link
                  to={`/payments/${p.id}`}
                  className="flex items-center justify-between px-4 py-3 text-sm hover:bg-gray-50"
                >
                  <div>
                    <p className="font-medium">
                      {isSender ? "Sent" : "Received"} · {formatPaise(p.amount_paise)}
                    </p>
                    <p className="text-gray-500">{formatDateTime(p.created_at)}</p>
                  </div>
                  <StatusBadge status={p.status} />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
