from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from engines.image_engine    import analyze_image
from engines.document_engine import analyze_document
from engines.text_engine     import analyze_text
from engines.video_engine    import analyze_video
import json
import os

app = FastAPI(title="TruthLens API", version="3.0.0")

# ── CORS — allow frontend on Render + localhost ──
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://truthlens-frontend.onrender.com",
    # Add your actual Render frontend URL here after deploying
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Use ALLOWED_ORIGINS after you know your URL
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status":     "TruthLens API running",
        "version":    "3.0.0",
        "engines":    ["image", "document", "text", "video"],
        "powered_by": "Groq AI"
    }


@app.post("/analyze/image")
async def image_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    return analyze_image(contents, file.filename)


@app.post("/analyze/document")
async def document_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    return analyze_document(contents, file.filename)


@app.post("/analyze/video")
async def video_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    return analyze_video(contents, file.filename)


@app.post("/analyze/text")
async def text_endpoint(text: str = Form(...)):
    return analyze_text(text)


@app.post("/analyze/auto")
async def auto_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    ext      = file.filename.split(".")[-1].lower()
    if ext in ["jpg","jpeg","png","gif","webp","bmp"]:
        return analyze_image(contents, file.filename)
    elif ext in ["mp4","mov","avi","webm","mkv"]:
        return analyze_video(contents, file.filename)
    elif ext in ["pdf","doc","docx"]:
        return analyze_document(contents, file.filename)
    else:
        return analyze_image(contents, file.filename)


@app.post("/report/pdf")
async def pdf_report_endpoint(request: Request):
    try:
        from core.report import generate_pdf_report
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            result_dict = await request.json()
        else:
            form        = await request.form()
            result_str  = form.get("result", "{}")
            result_dict = json.loads(result_str)

        filename  = result_dict.get("filename", "analysis").replace(" ", "_")
        pdf_bytes = generate_pdf_report(result_dict)

        return Response(
            content    = pdf_bytes,
            media_type = "application/pdf",
            headers    = {
                "Content-Disposition": f'attachment; filename="TruthLens_Report_{filename}.pdf"'
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}