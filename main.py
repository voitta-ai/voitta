import asyncio
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from voitta import VoittaRouter

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="Voitta Client API")

# Load endpoints from config file
router = VoittaRouter("voitta.yaml")


class FunctionCallRequest(BaseModel):
    function_name: str
    arguments: Dict[str, Any]
    token: Optional[str] = None
    oauth_token: Optional[str] = None
    tool_call_id: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Welcome to Voitta Client API"}


@app.get("/tools")
async def get_tools():
    """Get all available tools"""
    tools = router.get_tools()
    return {"tools": tools}


@app.post("/call-function")
async def call_function(request: FunctionCallRequest):
    """Call a function through the Voitta router"""
    try:
        result = await router.call_function(
            request.function_name,
            request.arguments,
            request.token,
            request.oauth_token,
            request.tool_call_id or ""
        )
        return JSONResponse(content={"result": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/prompt")
async def get_prompt():
    """Get the prompt for all tools"""
    prompt = router.get_prompt()
    return {"prompt": prompt}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "False").lower() == "true"

    uvicorn.run("main:app", host=host, port=port, reload=debug)
