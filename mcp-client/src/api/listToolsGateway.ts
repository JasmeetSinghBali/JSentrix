// api/listToolsGateway.ts
import { ToolsState } from "@/custom-components/RootWrapper";
import { apiFetch } from "./apiFetch";

/**
 * @desc list tools mcpserver via gateway
 * @returns tools list
 */
export async function listToolsGateway(): Promise<ToolsState | null> {
  try {
    const response = await apiFetch("http://localhost:8080/api/v1/listtools");

    if(!response.ok){
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    const data: ToolsState = await response.json();

    if (data) {
      return data;
    }

    return null;

  } catch (error: any) {
    throw new Error(error?.message || "Failed to list tools gateway-mcpserver");
  }
}
