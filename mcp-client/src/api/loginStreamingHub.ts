// api/loginStreamingHub.ts
export interface LoginStreamingHubTokenResponse{
  clientId: string | null;
  token: string | null;
}
/**
 * @desc login to streaming hub
 * @returns client id and token or null 
 */
export async function loginStreamingHub(): Promise<LoginStreamingHubTokenResponse | null> {
    try {
        // 📌 apiFetch common fetch interface not called as this call is independent of the gateway and is directly to the streaming-hub via traefik 
        const response = await fetch(`http://localhost/login`, { method: "POST" });

        if(!response.ok){
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }

        const data = await response.json();

        if (data.client_id && data.token) {
            return {
                clientId: data.client_id,
                token: data.token,
            };
        }

        return null;

  } catch (error: any) {
    throw new Error(error?.message || "Access to core-streaminghub failed");
  }
}