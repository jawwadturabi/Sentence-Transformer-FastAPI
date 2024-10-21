from fastapi import FastAPI, HTTPException,Request
from mangum import Mangum
from processDocuments import lambda_handler

app = FastAPI()
handler = Mangum(app)

@app.get("/")
def get():
    return "Hello from process document app"


@app.post("/processDocument")
async def process_document(request: Request):
    try:
        payload = await request.json()

        if "Records" not in payload:
            raise HTTPException(status_code=400, detail="Invalid payload: 'Records' key missing")

        result = lambda_handler(payload)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {e}")