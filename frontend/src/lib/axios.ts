import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";

import { env } from "@/config/env";
import { clearOnboardingComplete } from "@/lib/onboarding";

const TOKEN_STORAGE_KEY = "access_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  clearOnboardingComplete();
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  clearOnboardingComplete();
}

function attachAuthToken(
  config: InternalAxiosRequestConfig,
): InternalAxiosRequestConfig {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

function handleResponseError(error: AxiosError): Promise<never> {
  if (error.response?.status === 401) {
    clearAccessToken();
    window.location.assign("/login");
  }
  return Promise.reject(error);
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: env.apiBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15_000,
});

apiClient.interceptors.request.use(attachAuthToken);
apiClient.interceptors.response.use((response) => response, handleResponseError);
