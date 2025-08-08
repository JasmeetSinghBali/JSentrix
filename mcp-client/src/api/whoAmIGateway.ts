// api/whoAmIGateway.ts
import { CurrentUser } from "@/shared/store";
import { apiFetch } from "./apiFetch";

export async function whoAmIGateway(accessToken: string): Promise<CurrentUser | null> {
  try {
    const response = await apiFetch("http://localhost:8080/auth/me");

    if(!response.ok){
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    // Cast to UserState who is logged in
    const data: CurrentUser = await response.json();

    return data ?? null;

  } catch (error: any) {
    throw new Error(error?.message || "Access to gateway-whoami failed");
  }
}
