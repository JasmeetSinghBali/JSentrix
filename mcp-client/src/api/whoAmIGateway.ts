// api/whoAmIGateway.ts
import { CurrentUser } from "@/shared/store";
export interface WhoAmIResponse{
  
}
export async function whoAmIGateway(accessToken: string): Promise<CurrentUser | null> {
  try {
    const response = await fetch("http://localhost:8080/auth/me", {
        headers: { Authorization: `Bearer ${accessToken}` },
    });

    if(!response.ok){
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    // 🎈 shud Cast to UserState who is logged in
    const data: CurrentUser = await response.json();


    if (data) {
      return data;
    }

    return null;

  } catch (error: any) {
    throw new Error(error?.message || "Access to gateway-whoami failed");
  }
}
