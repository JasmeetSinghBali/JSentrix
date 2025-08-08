// src/api/apiFetch.ts
import { useCurrentUserStore, useGatewayAuthStore, useStreamingStore, useWsAuthStore } from "../shared/store";
import { stopTokenRotation } from "../shared/tokenService";

export async function apiFetch(url: string, options: RequestInit = {}) {
  const { accessToken } = useGatewayAuthStore.getState();
  const authHeaders = accessToken ? { Authorization: `Bearer ${accessToken}` } : {};

  let res = await fetch(url, { ...options, headers: { ...options.headers, ...authHeaders } });

  if (res.status === 401) {

    console.warn("Access token invalid, forcing logout");
    useGatewayAuthStore.getState().clearTokens();
    useWsAuthStore.getState().clearAuth();
    useStreamingStore.getState().clearStreamId();
    stopTokenRotation();
    useCurrentUserStore.getState().clearUser();    
}

  return res;
}
