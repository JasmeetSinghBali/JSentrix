from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# JWT config
SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI()

# CORS for local Electron app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
fake_user = {"username": "admin", "password": "secret"}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username != fake_user["username"]:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return username

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == fake_user["username"] and form_data.password == fake_user["password"]:
        token = create_access_token({"sub": form_data.username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")

async def mcp_client_call(call_type: str, tool_name: str = None, arguments: dict = None):
    server_params = StdioServerParameters(
        command="python",
        args=[r"..\mcp-server\mcp_server.py"],  # Adjust path if needed
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if call_type == "list_tools":
                tools = await session.list_tools()
                return [tool.name for tool in tools.tools]
            elif call_type == "call_tool":
                result = await session.call_tool(tool_name, arguments or {})
                return result
            else:
                raise ValueError("Unknown call_type")

@app.get("/listtools")
async def list_tools(user: str = Depends(get_current_user)):
    return {"tools": await mcp_client_call("list_tools")}

class ToolInvokeRequest(BaseModel):
    arguments: dict = {}

@app.post("/tools/{tool_name}/invoke")
async def invoke_tool(tool_name: str, req: ToolInvokeRequest, user: str = Depends(get_current_user)):
    result = await mcp_client_call("call_tool", tool_name=tool_name, arguments=req.arguments)
    return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
