import { useEffect, useState } from "react";
import { accountsApi, banksApi } from "../api/endpoints";
import type { Account, Bank } from "../api/types";
import { formatPaise } from "../lib/format";
import { apiErrorMessage } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";

export function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [selectedBankId, setSelectedBankId] = useState("");
  const [newBankName, setNewBankName] = useState("");
  const [newBankCode, setNewBankCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [accountList, bankList] = await Promise.all([accountsApi.list(), banksApi.list()]);
    setAccounts(accountList);
    setBanks(bankList);
    const balanceEntries = await Promise.all(
      accountList.map(async (a) => [a.id, (await accountsApi.balance(a.id)).balance_paise] as const),
    );
    setBalances(Object.fromEntries(balanceEntries));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreateBank(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const bank = await banksApi.create({ name: newBankName, code: newBankCode });
      setNewBankName("");
      setNewBankCode("");
      await refresh();
      setSelectedBankId(bank.id);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleOpenAccount(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedBankId) return;
    setError(null);
    setBusy(true);
    try {
      await accountsApi.create(selectedBankId);
      await refresh();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Accounts</h1>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-medium text-gray-700">Open a new account</h2>
        <form onSubmit={handleOpenAccount} className="flex items-end gap-3">
          <label className="flex-1 text-sm text-gray-700">
            Bank
            <select
              value={selectedBankId}
              onChange={(e) => setSelectedBankId(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select a bank…</option>
              {banks.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.code})
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={!selectedBankId || busy}
            className="rounded-md bg-violet-700 px-4 py-2 text-sm font-medium text-white hover:bg-violet-800 disabled:opacity-50"
          >
            Open Account
          </button>
        </form>

        <details className="mt-4">
          <summary className="cursor-pointer text-sm text-gray-500">
            Don't see your bank? Register one
          </summary>
          <form onSubmit={handleCreateBank} className="mt-3 flex items-end gap-3">
            <label className="text-sm text-gray-700">
              Name
              <input
                required
                value={newBankName}
                onChange={(e) => setNewBankName(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm text-gray-700">
              Code
              <input
                required
                value={newBankCode}
                onChange={(e) => setNewBankCode(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              Register Bank
            </button>
          </form>
        </details>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Your Accounts</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {accounts.map((a) => {
            const bank = banks.find((b) => b.id === a.bank_id);
            return (
              <div key={a.id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{bank?.name ?? "Bank"}</span>
                  <StatusBadge status={a.status} />
                </div>
                <p className="mt-1 text-sm text-gray-500">A/C {a.account_number}</p>
                <p className="mt-2 text-2xl font-semibold">{formatPaise(balances[a.id] ?? 0)}</p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
