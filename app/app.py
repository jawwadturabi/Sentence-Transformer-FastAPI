from fastapi import FastAPI, HTTPException, Request
from mangum import Mangum
from processDocuments import lambda_handler

app = FastAPI()
handler = Mangum(app)

import os



@app.get("/")
def get():
    return "Hello from process document app"


@app.post("/process_document")
async def process_document(request: Request):
    os.environ["HF_HOME"] = "/tmp"
    try:
        payload = await request.json()

        if "Records" not in payload:
            raise HTTPException(
                status_code=400, detail="Invalid payload: 'Records' key missing"
            )

        result = lambda_handler(payload)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {e}")
