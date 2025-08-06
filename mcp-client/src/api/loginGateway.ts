// api/loginGateway.ts
export interface LoginGatewayTokenResponse{
  access_token: string;
  refresh_token: string;
  token_type: string;
}
export async function loginGateway(email: string, password: string): Promise<LoginGatewayTokenResponse | null> {
  try {
    const response = await fetch("http://localhost:8080/auth/token", {
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

    if (data.access_token && data.refresh_token && data.token_type) {
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
