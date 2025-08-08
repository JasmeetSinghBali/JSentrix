import { refreshGatewayTokens } from "@/api/refreshGatewayTokens";
import { useGatewayAuthStore } from "./store";

let refreshInterval: NodeJS.Timeout | null = null;

export function startTokenRotation() {
  
  // mitigate duplicate intervals
  stopTokenRotation(); 

  // Run every 55 minutes
  refreshInterval = setInterval(async () => {
    
    const { refreshToken, setTokens, clearTokens } = useGatewayAuthStore.getState();

    if (!refreshToken) {
      console.warn("No refresh token found, skipping rotation.");
      return;
    }

    try {
      console.log("Refreshing access token...");
      const res = await refreshGatewayTokens(refreshToken);
      setTokens(res.access_token, res.refresh_token || refreshToken);
      console.log("Token refreshed at", new Date().toISOString());
    } catch (err: any) {
      console.error("Token refresh error:", err);
      clearTokens();
      stopTokenRotation();
    }
  }, 55 * 60 * 1000); // 55 min in ms
}

export function stopTokenRotation() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}