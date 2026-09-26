export interface SignedInUser {
  id: string;
  name: string;
  email: string;
  phone: string;
  created_at?: string | null;
}

export interface ForgotPasswordResult {
  detail: string;
  reset_code: string;
}
