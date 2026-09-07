import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";

import { env } from "@/config/env";
import { getAuthToken } from "@/lib/auth";

async function attachAuthToken(
  config: InternalAxiosRequestConfig,
): Promise<InternalAxiosRequestConfig> {
  const token = await getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

function handleResponseError(error: AxiosError): Promise<never> {
  if (error.response?.status === 401 && env.authMode === "clerk") {
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
