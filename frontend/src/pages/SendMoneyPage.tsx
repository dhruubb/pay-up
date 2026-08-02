import { useEffect, useState, type FormEvent } from "react";
import { vpasApi, paymentsApi } from "../api/endpoints";
import type { Payment, Vpa } from "../api/types";
import { apiErrorMessage } from "../api/client";
import { rupeesToPaise, formatPaise } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";

export function SendMoneyPage() {
  const [myVpas, setMyVpas] = useState<Vpa[]>([]);
  const [senderVpa, setSenderVpa] = useState("");
  const [receiverVpa, setReceiverVpa] = useState("");
  const [amount, setAmount] = useState("");
  // Regenerated whenever the form content changes, so retrying an identical
  // submission (e.g. a double-click) reuses the same key — that's what makes
  // it safe to retry — while any actual change to the payment gets a fresh one.
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Payment | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    vpasApi.list().then((vpas) => {
      setMyVpas(vpas);
      const primary = vpas.find((v) => v.is_primary) ?? vpas[0];
      if (primary) setSenderVpa(primary.address);
    });
  }, []);

  function updateAndRekey(setter: (v: string) => void) {
    return (value: string) => {
      setter(value);
      setIdempotencyKey(crypto.randomUUID());
      setResult(null);
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payment = await paymentsApi.initiate(
        {
          sender_vpa: senderVpa,
          receiver_vpa: receiverVpa,
          amount_paise: rupeesToPaise(amount),
        },
        idempotencyKey,
      );
      setResult(payment);
      if (payment.status === "SUCCESS") {
        setReceiverVpa("");
        setAmount("");
        setIdempotencyKey(crypto.randomUUID());
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Send Money</h1>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      >
        <label className="block text-sm text-gray-700">
          From
          <select
            value={senderVpa}
            onChange={(e) => updateAndRekey(setSenderVpa)(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {myVpas.map((v) => (
              <option key={v.id} value={v.address}>
                {v.address} {v.is_primary ? "(primary)" : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm text-gray-700">
          To (VPA)
          <input
            required
            placeholder="friend@okpayup"
            value={receiverVpa}
            onChange={(e) => updateAndRekey(setReceiverVpa)(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm text-gray-700">
          Amount (₹)
          <input
            required
            type="number"
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(e) => updateAndRekey(setAmount)(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting || !senderVpa || !receiverVpa || !amount}
          className="w-full rounded-md bg-violet-700 py-2 text-sm font-medium text-white hover:bg-violet-800 disabled:opacity-50"
        >
          {submitting ? "Sending…" : "Send"}
        </button>
      </form>

      {result && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm shadow-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium">Payment {result.id.slice(0, 8)}</span>
            <StatusBadge status={result.status} />
          </div>
          <p className="mt-1 text-gray-500">{formatPaise(result.amount_paise)}</p>
        </div>
      )}
    </div>
  );
}
