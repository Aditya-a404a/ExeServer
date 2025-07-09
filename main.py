from fastapi import FastAPI, Request
import subprocess

app = FastAPI()

@app.post("/run")
async def run_code(request: Request):
    data = await request.json()
    code = data.get("code")
    try:
        result = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=5)
        return {"output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"error": str(e)}