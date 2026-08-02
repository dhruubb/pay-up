import { useEffect, useState, type FormEvent } from "react";
import { accountsApi, pspsApi, vpasApi } from "../api/endpoints";
import type { Account, Psp, Vpa } from "../api/types";
import { apiErrorMessage } from "../api/client";

export function VpasPage() {
  const [vpas, setVpas] = useState<Vpa[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [psps, setPsps] = useState<Psp[]>([]);
  const [accountId, setAccountId] = useState("");
  const [pspId, setPspId] = useState("");
  const [address, setAddress] = useState("");
  const [newPspName, setNewPspName] = useState("");
  const [newPspCode, setNewPspCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [vpaList, accountList, pspList] = await Promise.all([
      vpasApi.list(),
      accountsApi.list(),
      pspsApi.list(),
    ]);
    setVpas(vpaList);
    setAccounts(accountList);
    setPsps(pspList);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreatePsp(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const psp = await pspsApi.create({ name: newPspName, code: newPspCode });
      setNewPspName("");
      setNewPspCode("");
      await refresh();
      setPspId(psp.id);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateVpa(e: FormEvent) {
    e.preventDefault();
    if (!accountId || !pspId) return;
    setError(null);
    setBusy(true);
    try {
      await vpasApi.create({ account_id: accountId, psp_id: pspId, address });
      setAddress("");
      await refresh();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSetPrimary(vpaId: string) {
    setError(null);
    setBusy(true);
    try {
      await vpasApi.setPrimary(vpaId);
      await refresh();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">VPAs</h1>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-medium text-gray-700">Create a VPA</h2>
        <form onSubmit={handleCreateVpa} className="flex flex-wrap items-end gap-3">
          <label className="text-sm text-gray-700">
            Account
            <select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select account…</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  A/C {a.account_number}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-gray-700">
            PSP
            <select
              value={pspId}
              onChange={(e) => setPspId(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select PSP…</option>
              {psps.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-gray-700">
            Address
            <input
              required
              placeholder="you@okpayup"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={!accountId || !pspId || busy}
            className="rounded-md bg-violet-700 px-4 py-2 text-sm font-medium text-white hover:bg-violet-800 disabled:opacity-50"
          >
            Create VPA
          </button>
        </form>

        <details className="mt-4">
          <summary className="cursor-pointer text-sm text-gray-500">
            Don't see your PSP? Register one
          </summary>
          <form onSubmit={handleCreatePsp} className="mt-3 flex items-end gap-3">
            <label className="text-sm text-gray-700">
              Name
              <input
                required
                value={newPspName}
                onChange={(e) => setNewPspName(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm text-gray-700">
              Code
              <input
                required
                value={newPspCode}
                onChange={(e) => setNewPspCode(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              Register PSP
            </button>
          </form>
        </details>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Your VPAs</h2>
        <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
          {vpas.map((v) => (
            <li key={v.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <span>{v.address}</span>
              {v.is_primary ? (
                <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-medium text-violet-700">
                  Primary
                </span>
              ) : (
                <button
                  onClick={() => handleSetPrimary(v.id)}
                  disabled={busy}
                  className="text-xs font-medium text-violet-700 hover:underline disabled:opacity-50"
                >
                  Set as primary
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
