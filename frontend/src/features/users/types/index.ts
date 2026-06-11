export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface UserCreatePayload {
  email: string;
  full_name: string;
  password: string;
}

export interface UserUpdatePayload {
  email?: string;
  full_name?: string;
  is_active?: boolean;
}
