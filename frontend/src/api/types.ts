export interface User {
  id: string;
  name: string;
  email: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Bank {
  id: string;
  name: string;
  code: string;
}

export interface Psp {
  id: string;
  name: string;
  code: string;
}

export type AccountStatus = "ACTIVE" | "FROZEN" | "CLOSED";

export interface Account {
  id: string;
  bank_id: string;
  account_number: string;
  status: AccountStatus;
}

export interface Vpa {
  id: string;
  account_id: string;
  psp_id: string;
  address: string;
  is_primary: boolean;
}

export interface Balance {
  account_id: string;
  balance_paise: number;
}

export interface LedgerEntry {
  id: string;
  account_id: string;
  entry_type: "DEBIT" | "CREDIT";
  amount_paise: number;
  balance_after_paise: number;
  created_at: string;
}

export type PaymentStatus = "INITIATED" | "PROCESSING" | "SUCCESS" | "FAILED";

export interface Payment {
  id: string;
  sender_account_id: string;
  receiver_account_id: string;
  initiated_by_psp_id: string;
  amount_paise: number;
  status: PaymentStatus;
  failure_reason: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface PaymentEvent {
  id: string;
  event_type: "INITIATED" | "PROCESSING" | "DEBITED" | "CREDITED" | "SUCCESS" | "FAILED";
  payload: Record<string, unknown>;
  published_at: string | null;
  created_at: string;
}

export interface Notification {
  id: string;
  payment_id: string;
  channel: string;
  message: string;
  status: string;
  created_at: string;
}

export interface ApiErrorBody {
  error_code: string;
  message: string;
  detail: unknown;
}
