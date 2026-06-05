import subprocess
import asyncio
import sys
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/scrape")
async def scrape_endpoint(location: str, limit: int = 5):
    async def run_and_stream():
        process = await asyncio.create_subprocess_exec(
            sys.executable, "main.py", "--location", location, "--limit", str(limit),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            # Format the output for SSE
            text = line.decode('utf-8').strip()
            if text:
                yield f"data: {json.dumps({'log': text})}\n\n"
        
        await process.wait()
        
        slug = location.lower().replace(" ", "_")
        json_file = f"sample_output/partners_{slug}.json"
        
        results = []
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                try:
                    results = json.load(f)
                except:
                    pass
                    
        yield f"data: {json.dumps({'complete': True, 'results': results})}\n\n"

    return StreamingResponse(run_and_stream(), media_type="text/event-stream")

@app.get("/api/results/{location}")
def get_results(location: str):
    slug = location.lower().replace(" ", "_")
    json_file = f"sample_output/partners_{slug}.json"
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
