import axios from "axios";
import { clearAllAuth, getAuthToken, getRefreshToken, setAuthToken, setRefreshToken } from "./auth";

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");

export const buildApiUrl = (path: string) => {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config as any;
    const status = error?.response?.status;

    if (status === 401 && originalRequest && !originalRequest._retry) {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        originalRequest._retry = true;
        try {
          const refreshResponse = await axios.post(buildApiUrl("/auth/refresh"), {
            refresh_token: refreshToken,
          });

          const newAccessToken = refreshResponse.data?.access_token;
          const newRefreshToken = refreshResponse.data?.refresh_token;
          if (typeof newAccessToken === "string" && newAccessToken) {
            setAuthToken(newAccessToken);
            setRefreshToken(typeof newRefreshToken === "string" ? newRefreshToken : null);
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            return api(originalRequest);
          }
        } catch {
          // Fallback to session clear below.
        }
      }

      clearAllAuth();
      if (window.location.pathname !== "/login") {
        const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
        window.location.href = `/login?next=${next}`;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
