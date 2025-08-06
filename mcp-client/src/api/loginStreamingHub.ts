// api/loginStreamingHub.ts
export interface LoginStreamingHubTokenResponse{
  clientId: string | null;
  token: string | null;
}
export async function loginStreamingHub(): Promise<LoginStreamingHubTokenResponse | null> {
    try {
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