import { API_BASE_URL, NGROK_HEADERS } from "./http";

export interface FeatureFlags {
  cash_payments_enabled: boolean;
  no_drivers_message_minutes: number;
  support_phone_number: string;
}

const DEFAULT_FLAGS: FeatureFlags = {
  cash_payments_enabled: false,
  no_drivers_message_minutes: 45,
  support_phone_number: "",
};

/** Public, unauthenticated — same pattern as getBankOptions(). Never
 * rejects; falls back to the conservative defaults above (cash off) if the
 * request fails, rather than risking a cash option appearing when the
 * backend actually has it disabled. */
export function getFeatureFlags(): Promise<FeatureFlags> {
  return fetch(`${API_BASE_URL}/config/flags`, { headers: NGROK_HEADERS })
    .then((r) => r.json())
    .then((data) => ({ ...DEFAULT_FLAGS, ...data }))
    .catch(() => DEFAULT_FLAGS);
}
