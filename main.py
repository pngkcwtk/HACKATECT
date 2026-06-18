"""
main.py — FastAPI Backend สำหรับ Welfare Gap Finder
รัน: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, Optional
import logging

# import pipeline จากไฟล์ที่มีอยู่แล้ว
from Backend_backup.welfare_agent_pipeline import run_pipeline, build_policy_index, FinalSummaryOutput

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Welfare Gap Finder API",
    description="Backend สำหรับวิเคราะห์สวัสดิการที่ประชาชนควรได้รับ",
    version="1.0.0",
)

# อนุญาต CORS จาก frontend (localhost ทุก port สำหรับ dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # production: ระบุ domain จริง เช่น ["https://your-domain.com"]
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# REQUEST / RESPONSE MODELS
# ---------------------------------------------------------------------------

class PipelineRequest(BaseModel):
    """
    รับ payload ตรงจาก frontend buildPayload()
    โครงสร้างตรงกับที่ welfare_agent_pipeline.py ใช้อยู่แล้ว
    """
    citizen_profile: Dict[str, Any]
    structured_data: Dict[str, Any]
    rag_context: Dict[str, Any]


class PipelineResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ---------------------------------------------------------------------------
# STARTUP: build RAG index ครั้งเดียวตอนเซิร์ฟเวอร์เริ่ม
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Server starting — building RAG index...")
    build_policy_index()
    logger.info("✅ RAG index ready")

# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Welfare Gap Finder API พร้อมใช้งาน"}


@app.post("/api/analyze", response_model=PipelineResponse)
async def analyze_welfare(request: PipelineRequest):
    """
    รับข้อมูลจาก frontend แล้วรัน Multi-Agent Pipeline
    คืน FinalSummaryOutput พร้อม benefit_analysis และ next_steps
    """
    logger.info(
        f"📥 รับเคสใหม่: "
        f"{request.citizen_profile.get('personal_information', {}).get('first_name', '?')} "
        f"{request.citizen_profile.get('personal_information', {}).get('last_name', '')}"
    )

    try:
        result: Optional[FinalSummaryOutput] = run_pipeline(request.dict())

        if result is None:
            raise HTTPException(
                status_code=500,
                detail="Pipeline ประมวลผลไม่สำเร็จ กรุณาตรวจสอบ log"
            )

        return PipelineResponse(success=True, data=result.model_dump())

    except ValueError as e:
        logger.error(f"❌ ข้อมูลไม่ถูกต้อง: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")