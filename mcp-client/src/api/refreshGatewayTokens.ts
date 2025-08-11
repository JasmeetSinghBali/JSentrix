// api/refreshGatewayTokens.ts
import { apiFetch } from "./apiFetch";

export interface RefreshGatewayTokenResponse{
  access_token: string;
  refresh_token: string;
  token_type: string;
}
/**
 * Refresh gateway tokens using a valid refresh token.
 * @param refreshToken - The current refresh token.
 * @returns New access and refresh tokens, or null if failed.
 */
export async function refreshGatewayTokens(
    refresh_token: string,
): Promise<RefreshGatewayTokenResponse | null> {
  try {
    const response = await apiFetch("http://localhost:8080/auth/refresh", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json" 
      },
      body: JSON.stringify({
        refresh_token: refresh_token
      }),
    });

    if(!response.ok){
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    const data = await response.json();

     if (
      typeof data.access_token === "string" &&
      typeof data.refresh_token === "string" &&
      typeof data.token_type === "string"
    ) {
      return {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type,
      };
    }

    return null;

  } catch (error: any) {
    throw new Error(error?.message || "Refresh gateway token request failed");
  }
}
