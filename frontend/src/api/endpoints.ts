import { apiClient } from "./client";
import type {
  Account,
  Balance,
  Bank,
  LedgerEntry,
  Notification,
  Payment,
  PaymentEvent,
  Psp,
  TokenResponse,
  User,
  Vpa,
} from "./types";

export const authApi = {
  register: (data: { name: string; email: string; phone: string; password: string }) =>
    apiClient.post<User>("/users/register", data).then((r) => r.data),
  login: (data: { email: string; password: string }) =>
    apiClient.post<TokenResponse>("/users/login", data).then((r) => r.data),
  me: () => apiClient.get<User>("/users/me").then((r) => r.data),
};

export const banksApi = {
  list: () => apiClient.get<Bank[]>("/banks").then((r) => r.data),
  create: (data: { name: string; code: string }) =>
    apiClient.post<Bank>("/banks", data).then((r) => r.data),
};

export const pspsApi = {
  list: () => apiClient.get<Psp[]>("/psps").then((r) => r.data),
  create: (data: { name: string; code: string }) =>
    apiClient.post<Psp>("/psps", data).then((r) => r.data),
};

export const accountsApi = {
  list: () => apiClient.get<Account[]>("/accounts").then((r) => r.data),
  create: (bank_id: string) =>
    apiClient.post<Account>("/accounts", { bank_id }).then((r) => r.data),
  balance: (accountId: string) =>
    apiClient.get<Balance>(`/accounts/${accountId}/balance`).then((r) => r.data),
  ledger: (accountId: string) =>
    apiClient.get<LedgerEntry[]>(`/accounts/${accountId}/ledger`).then((r) => r.data),
};

export const vpasApi = {
  list: () => apiClient.get<Vpa[]>("/vpas").then((r) => r.data),
  create: (data: { account_id: string; psp_id: string; address: string }) =>
    apiClient.post<Vpa>("/vpas", data).then((r) => r.data),
  setPrimary: (vpaId: string) =>
    apiClient.patch<Vpa>(`/vpas/${vpaId}/primary`).then((r) => r.data),
};

export const paymentsApi = {
  list: () => apiClient.get<Payment[]>("/payments").then((r) => r.data),
  get: (paymentId: string) =>
    apiClient.get<Payment>(`/payments/${paymentId}`).then((r) => r.data),
  events: (paymentId: string) =>
    apiClient.get<PaymentEvent[]>(`/payments/${paymentId}/events`).then((r) => r.data),
  initiate: (
    data: { sender_vpa: string; receiver_vpa: string; amount_paise: number },
    idempotencyKey: string,
  ) =>
    apiClient
      .post<Payment>("/payments", data, { headers: { "Idempotency-Key": idempotencyKey } })
      .then((r) => r.data),
};

export const notificationsApi = {
  list: () => apiClient.get<Notification[]>("/notifications").then((r) => r.data),
};
