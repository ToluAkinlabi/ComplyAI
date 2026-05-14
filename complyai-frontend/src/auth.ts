const TOKEN_KEY = "complyai_token";
const REFRESH_TOKEN_KEY = "complyai_refresh_token";

const decodeJwtPayload = (token: string): Record<string, unknown> | null => {
  try {
    const parts = token.split(".");
    if (parts.length < 2) {
      return null;
    }

    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    const json = atob(padded);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
};

const isExpired = (token: string): boolean => {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") {
    return false;
  }

  const nowSeconds = Math.floor(Date.now() / 1000);
  return nowSeconds >= payload.exp;
};

export const getAuthToken = (): string | null => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    return null;
  }

  if (isExpired(token)) {
    localStorage.removeItem(TOKEN_KEY);
    return null;
  }

  return token;
};

export const setAuthToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearAuthToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

export const setRefreshToken = (token: string | null): void => {
  if (!token) {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    return;
  }
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
};

export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

export const clearAllAuth = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};

export const isAuthenticated = (): boolean => {
  return getAuthToken() !== null;
};

export const getUserDisplayName = (): string => {
  const token = getAuthToken();
  if (!token) {
    return "Auditor";
  }

  const payload = decodeJwtPayload(token);
  const subject = typeof payload?.sub === "string" ? payload.sub : "";
  if (!subject) {
    return "Auditor";
  }

  const display = subject.split("@")[0].trim();
  return display || "Auditor";
};

export const getUserRole = (): string | null => {
  const token = getAuthToken();
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload) return null;
  return typeof payload.role === "string" ? payload.role : null;
};

export const isAdmin = (): boolean => {
  const role = getUserRole();
  return role === "admin" || role === "owner";
};
