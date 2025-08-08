// api/invokeToolGateway.ts
import { apiFetch } from "./apiFetch";

/**
 * @desc invoke tool mcpserver via gateway
 * @param toolName  
 * @returns 
 */
export async function invokeToolGateway(toolName: string, params = {}): Promise<any | null> {
  try {
    const response = await apiFetch(
        `http://localhost:8080/api/v1/tools/${toolName}/invoke`,
        {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(params),
        }
    );

    if(!response.ok){
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    const data = await response.json();

    if (data) {
      return data;
    }

    return null;

  } catch (error: any) {
      throw new Error(error?.message || `failed to invoke tool: ${toolName} gateway-mcpserver`);
  }
}
