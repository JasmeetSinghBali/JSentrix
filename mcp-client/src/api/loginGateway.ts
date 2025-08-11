// api/loginGateway.ts
import { apiFetch } from "./apiFetch";

export interface LoginGatewayTokenResponse{
  access_token: string;
  refresh_token: string;
  token_type: string;
}
/**
 * @desc Login to the gateway and retrieve access/refresh tokens.
 * @params Uses x-www-form-urlencoded because FastAPI's OAuth2PasswordRequestForm expects it.
 */
export async function loginGateway(email: string, password: string): Promise<LoginGatewayTokenResponse | null> {
  try {
    const response = await apiFetch("http://localhost:8080/auth/token", {
      method: "POST",
      headers: { 
        "Content-Type": "application/x-www-form-urlencoded" 
      },
      body: new URLSearchParams({ 
        username: email, 
        password, 
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
    throw new Error(error?.message || "Access to core-gateway failed");
  }
}
