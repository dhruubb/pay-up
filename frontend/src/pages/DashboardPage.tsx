import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { accountsApi, banksApi, vpasApi } from "../api/endpoints";
import type { Account, Bank, Vpa } from "../api/types";
import { formatPaise } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";

export function DashboardPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [balances, setBalances] = useState<Record<string, number>>({});
  const [banks, setBanks] = useState<Record<string, Bank>>({});
  const [vpas, setVpas] = useState<Vpa[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [accountList, bankList, vpaList] = await Promise.all([
        accountsApi.list(),
        banksApi.list(),
        vpasApi.list(),
      ]);
      setAccounts(accountList);
      setBanks(Object.fromEntries(bankList.map((b) => [b.id, b])));
      setVpas(vpaList);

      const balanceEntries = await Promise.all(
        accountList.map(async (a) => [a.id, (await accountsApi.balance(a.id)).balance_paise] as const),
      );
      setBalances(Object.fromEntries(balanceEntries));
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <p className="text-gray-500">Loading…</p>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Link
          to="/send"
          className="rounded-md bg-violet-700 px-4 py-2 text-sm font-medium text-white hover:bg-violet-800"
        >
          Send Money
        </Link>
      </div>

      <section>
        <h2 className="mb-3 text-lg font-medium">Your Accounts</h2>
        {accounts.length === 0 ? (
          <p className="text-sm text-gray-500">
            No accounts yet. <Link to="/accounts" className="text-violet-700">Open one</Link>.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {accounts.map((a) => (
              <div key={a.id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{banks[a.bank_id]?.name ?? "Bank"}</span>
                  <StatusBadge status={a.status} />
                </div>
                <p className="mt-1 text-sm text-gray-500">A/C {a.account_number}</p>
                <p className="mt-2 text-2xl font-semibold">
                  {formatPaise(balances[a.id] ?? 0)}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Your VPAs</h2>
        {vpas.length === 0 ? (
          <p className="text-sm text-gray-500">
            No VPAs yet. <Link to="/vpas" className="text-violet-700">Create one</Link>.
          </p>
        ) : (
          <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
            {vpas.map((v) => (
              <li key={v.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <span>{v.address}</span>
                {v.is_primary && (
                  <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-medium text-violet-700">
                    Primary
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
