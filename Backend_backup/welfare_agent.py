import os
import json
import logging
import time
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

# ---------------------------------------------------------------------------
# 0. SETUP LOGGING & ENVIRONMENT
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

load_dotenv()

# ---------------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------------

TYPHOON_API_KEY = os.environ.get("TYPHOON_API_KEY")
TYPHOON_BASE_URL = "https://api.opentyphoon.ai/v1"
MODEL_NAME    = "typhoon-v2.5-30b-a3b-instruct"
RAG_TOP_K     = 5      # จำนวนสวัสดิการที่ดึงจาก RAG
RAG_MIN_SCORE = 0.15   # TF-IDF score ขั้นต่ำที่ถือว่า relevant (ต่ำกว่า embedding เพราะ sparse)

if not TYPHOON_API_KEY:
    raise EnvironmentError(
        "❌ TYPHOON_API_KEY ไม่ได้ถูกกำหนดค่า "
        "กรุณาสร้างไฟล์ .env และใส่ค่า TYPHOON_API_KEY=your_key_here"
    )

logger.info(f"✅ TYPHOON_API_KEY: พบค่าแล้ว (ความยาว {len(TYPHOON_API_KEY)} ตัวอักษร)")
client = OpenAI(api_key=TYPHOON_API_KEY, base_url=TYPHOON_BASE_URL)

# ---------------------------------------------------------------------------
# 2. BENEFIT DATABASE (RAG Source) — จาก CSV จริง
# ---------------------------------------------------------------------------
# แต่ละรายการมี "rag_text" ที่ใช้สร้าง embedding
# (รวม benefit_name + category + content ไว้เป็น single string เพื่อ semantic search)

ALL_POLICIES: List[Dict[str, Any]] = [
    {
        "benefit_id": 1,
        "benefit_name": "เบี้ยยังชีพผู้สูงอายุ",
        "category": "Elderly",
        "content": "ชื่อสิทธิ์: เบี้ยยังชีพผู้สูงอายุ กลุ่มเป้าหมาย: ผู้สูงอายุ คุณสมบัติ: อายุ 60 ปีขึ้นไป สัญชาติไทย มีชื่อในทะเบียนบ้าน เอกสาร: บัตรประชาชน ทะเบียนบ้าน หน่วยงาน: องค์กรปกครองส่วนท้องถิ่น",
    },
    {
        "benefit_id": 2,
        "benefit_name": "เบี้ยความพิการ",
        "category": "Disability",
        "content": "ชื่อสิทธิ์: เบี้ยความพิการ กลุ่มเป้าหมาย: คนพิการ คุณสมบัติ: มีบัตรประจำตัวคนพิการ สัญชาติไทย เอกสาร: บัตรคนพิการ บัตรประชาชน หน่วยงาน: กรมส่งเสริมและพัฒนาคุณภาพชีวิตคนพิการ",
    },
    {
        "benefit_id": 3,
        "benefit_name": "เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด",
        "category": "Child Welfare",
        "content": "ชื่อสิทธิ์: เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด กลุ่มเป้าหมาย: ครัวเรือนรายได้น้อยที่มีเด็กแรกเกิด คุณสมบัติ: เด็กแรกเกิดตามเกณฑ์ของรัฐ เอกสาร: สูติบัตร ทะเบียนบ้าน",
    },
    {
        "benefit_id": 4,
        "benefit_name": "บัตรสวัสดิการแห่งรัฐ",
        "category": "Financial Support",
        "content": "ชื่อสิทธิ์: บัตรสวัสดิการแห่งรัฐ กลุ่มเป้าหมาย: ผู้มีรายได้น้อย คุณสมบัติ: ผ่านเกณฑ์รายได้และทรัพย์สินที่กำหนด สิทธิประโยชน์: ส่วนลดค่าน้ำ ค่าไฟ ค่าเดินทาง และวงเงินซื้อสินค้า",
    },
    {
        "benefit_id": 5,
        "benefit_name": "สิทธิหลักประกันสุขภาพแห่งชาติ",
        "category": "Healthcare",
        "content": "ชื่อสิทธิ์: สิทธิหลักประกันสุขภาพแห่งชาติ กลุ่มเป้าหมาย: ประชาชนทั่วไป คุณสมบัติ: ไม่มีสิทธิรักษาพยาบาลอื่น สิทธิประโยชน์: รับบริการตามสิทธิบัตรทอง",
    },
    {
        "benefit_id": 6,
        "benefit_name": "สิทธิประกันสังคม",
        "category": "Healthcare",
        "content": "ชื่อสิทธิ์: สิทธิประกันสังคม กลุ่มเป้าหมาย: ผู้ประกันตน คุณสมบัติ: เป็นผู้ประกันตนมาตรา 33 39 หรือ 40 สิทธิประโยชน์: ค่ารักษาพยาบาล เงินทดแทน และสวัสดิการตามกฎหมาย",
    },
    {
        "benefit_id": 7,
        "benefit_name": "สิทธิรักษาพยาบาลข้าราชการ",
        "category": "Healthcare",
        "content": "ชื่อสิทธิ์: สิทธิรักษาพยาบาลข้าราชการ กลุ่มเป้าหมาย: ข้าราชการและครอบครัว คุณสมบัติ: มีสิทธิสวัสดิการรักษาพยาบาลข้าราชการ",
    },
    {
        "benefit_id": 8,
        "benefit_name": "สถานพยาบาลประจำสิทธิรักษาพยาบาล",
        "category": "Healthcare",
        "content": "ข้อมูลสถานพยาบาลประจำตามสิทธิรักษาพยาบาลที่ประชาชนสังกัดอยู่ ใช้สำหรับการอ้างอิงและส่งต่อบริการ",
    },
    {
        "benefit_id": 9,
        "benefit_name": "สถานะผู้มีสิทธิบัตรสวัสดิการแห่งรัฐ 2569",
        "category": "Financial Support",
        "content": "ข้อมูลสถานะการผ่านเกณฑ์ผู้มีสิทธิในโครงการสวัสดิการแห่งรัฐ ปี 2569",
    },
    {
        "benefit_id": 10,
        "benefit_name": "สถานะการลงทะเบียนสวัสดิการแห่งรัฐ 2569",
        "category": "Financial Support",
        "content": "ข้อมูลสถานะการลงทะเบียน การตรวจสอบ และผลการพิจารณาโครงการสวัสดิการแห่งรัฐ ปี 2569",
    },
]

# ประวัติสิทธิ์ของแต่ละ Citizen ID
MOCK_CITIZEN_BENEFITS_DB: Dict[str, List[Dict[str, Any]]] = {
    "1234567890123": [
        {"benefit_name": "เบี้ยยังชีพผู้สูงอายุ",  "status": "Active",  "approved_date": "2025-01-10"},
        {"benefit_name": "บัตรสวัสดิการแห่งรัฐ",   "status": "Expired", "approved_date": "2024-01-01"},
    ]
}

# ---------------------------------------------------------------------------
# 3. PYDANTIC OUTPUT MODELS
# ---------------------------------------------------------------------------

class BenefitItem(BaseModel):
    benefit_name: str
    category:     str = ""
    content:      str = ""
    criteria:     str = ""   # optional — อาจถูก populate โดย AI
    amount:       str = ""

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount_to_str(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            return str(v)
        return str(v) if v is not None else ""


class ExistingBenefitItem(BaseModel):
    benefit_name:  str
    status:        str = ""
    approved_date: str = ""


class Agent1Output(BaseModel):
    possible_benefits: List[BenefitItem] = Field(default=[], description="สวัสดิการที่ผู้ลงทะเบียนมีคุณสมบัติ")
    reasoning:         str               = Field(default="", description="เหตุผลประกอบ")


class Agent2Output(BaseModel):
    approved_new_benefits:    List[BenefitItem]         = Field(default=[], description="สวัสดิการใหม่ที่ไม่ทับซ้อน")
    existing_active_benefits: List[ExistingBenefitItem] = Field(default=[], description="สวัสดิการที่ Active อยู่แล้ว")


class BenefitValueScore(BaseModel):
    """การวิเคราะห์ความคุ้มค่าของสวัสดิการแต่ละรายการ"""
    benefit_name:         str
    category:             str = ""
    eligibility_chance:   str = Field(description="โอกาสที่จะได้รับสิทธิ์ เช่น สูงมาก / ปานกลาง / ต่ำ")
    estimated_value:      str = Field(description="มูลค่าโดยประมาณที่จะได้รับ เช่น 600-1,000 บาท/เดือน")
    pros:                 List[str] = Field(default=[], description="ข้อดีของสิทธิ์นี้")
    cons:                 List[str] = Field(default=[], description="ข้อจำกัดหรือเงื่อนไขที่ต้องระวัง")
    required_documents:   List[str] = Field(default=[], description="เอกสารที่ต้องเตรียม")
    recommendation_score: int       = Field(description="คะแนนแนะนำ 1-10 (10 = แนะนำมากที่สุด)")


class FinalSummaryOutput(BaseModel):
    citizen_name:      str
    status:            str        = Field(description="สรุปสถานะ เช่น 'แนะนำสิทธิ์เพิ่มเติม'")
    benefit_analysis:  List[BenefitValueScore] = Field(default=[], description="วิเคราะห์ความคุ้มค่าแต่ละสิทธิ์")
    recommended_actions: List[str] = Field(default=[], description="สิ่งที่เจ้าหน้าที่ต้องดำเนินการต่อ")
    summary_text:      str        = Field(description="บทสรุปภาษาไทยสำหรับเจ้าหน้าที่")
    decision_note:     str        = Field(default="", description="หมายเหตุสำหรับผู้รับบริการในการตัดสินใจเลือกสิทธิ์")

# ---------------------------------------------------------------------------
# 4. RAG ENGINE — TF-IDF + Cosine Similarity (ไม่ต้องเรียก API ภายนอก)
# ---------------------------------------------------------------------------
# ใช้ char_wb n-gram (2,3) ซึ่งทำงานดีกับภาษาไทยโดยไม่ต้อง tokenize
# ---------------------------------------------------------------------------

_tfidf_vectorizer: Optional[TfidfVectorizer] = None
_tfidf_matrix     = None   # sparse matrix จาก sklearn
_policy_rag_texts: List[str] = []


def _build_rag_text(policy: Dict[str, Any]) -> str:
    """รวม field สำคัญเป็น single string สำหรับ TF-IDF index"""
    return f"{policy['benefit_name']} {policy['category']} {policy['content']}"


def build_policy_index() -> None:
    """
    สร้าง TF-IDF index สำหรับ ALL_POLICIES
    เรียกครั้งเดียวตอนเริ่มโปรแกรม — ไม่ต้องเรียก API ใดๆ
    """
    global _tfidf_vectorizer, _tfidf_matrix, _policy_rag_texts

    logger.info("[RAG] กำลังสร้าง TF-IDF policy index...")
    _policy_rag_texts = [_build_rag_text(p) for p in ALL_POLICIES]

    # char_wb ngram(2,3) ดีมากสำหรับภาษาไทย: จับ subword pattern โดยไม่ต้อง tokenize
    _tfidf_vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 3),
        sublinear_tf=True,   # log TF เพื่อลด bias จากคำที่ซ้ำมาก
    )
    _tfidf_matrix = _tfidf_vectorizer.fit_transform(_policy_rag_texts)
    logger.info(f"[RAG] ✅ index พร้อมแล้ว ({len(ALL_POLICIES)} policies, vocab={len(_tfidf_vectorizer.vocabulary_)})")


def rag_search(query: str, top_k: int = RAG_TOP_K, min_score: float = RAG_MIN_SCORE) -> List[Dict[str, Any]]:
    """
    ค้นหาสวัสดิการที่เกี่ยวข้องกับ query ด้วย TF-IDF cosine similarity
    คืน top_k รายการที่มี score >= min_score
    """
    if _tfidf_vectorizer is None or _tfidf_matrix is None:
        raise RuntimeError("Policy index ยังไม่ถูกสร้าง กรุณาเรียก build_policy_index() ก่อน")

    logger.info(f"[RAG] ค้นหาด้วย query: '{query[:80]}...'")

    query_vec = _tfidf_vectorizer.transform([query])
    scores    = sk_cosine(query_vec, _tfidf_matrix)[0]   # shape: (n_policies,)

    ranked_indices = np.argsort(scores)[::-1]

    results = []
    for idx in ranked_indices[:top_k]:
        score = float(scores[idx])
        if score < min_score:
            break
        policy = ALL_POLICIES[idx]
        results.append({
            "benefit_id":   policy["benefit_id"],
            "benefit_name": policy["benefit_name"],
            "category":     policy["category"],
            "content":      policy["content"],
            "rag_score":    round(score, 4),
        })
        logger.info(f"[RAG]   #{len(results)} {policy['benefit_name']} (score={score:.3f})")

    logger.info(f"[RAG] พบ {len(results)} รายการที่ relevant")
    return results

# ---------------------------------------------------------------------------
# 5. TOOLS (ใช้ RAG แทน keyword filter)
# ---------------------------------------------------------------------------

def rag_retrieval_tool(citizen_profile: Dict[str, Any], rag_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Agent 1 Tool: ดึงสวัสดิการที่ relevant โดยใช้ RAG
    สร้าง query จาก citizen profile + rag_context summary
    """
    # สร้าง query จาก profile จริงของผู้ลงทะเบียน
    personal  = citizen_profile.get("personal_information", {})
    economic  = citizen_profile.get("economic_information", {})
    household = citizen_profile.get("household_information", {})
    groups    = citizen_profile.get("vulnerable_groups", [])
    rag_sum   = rag_context.get("summary", "")
    keywords  = rag_context.get("keywords", [])

    query_parts = []
    if rag_sum:
        query_parts.append(rag_sum)
    if personal.get("age"):
        query_parts.append(f"อายุ {personal['age']} ปี")
    if economic.get("occupation"):
        query_parts.append(f"อาชีพ {economic['occupation']}")
    if economic.get("monthly_income"):
        query_parts.append(f"รายได้ {economic['monthly_income']} บาท/เดือน")
    if household.get("living_arrangement"):
        query_parts.append(f"สถานะ {household['living_arrangement']}")
    if groups:
        query_parts.append("กลุ่ม " + " ".join(groups))
    if keywords:
        query_parts.extend(keywords)

    query = " ".join(query_parts)
    logger.info(f"[RAG Tool] Query: {query[:120]}...")

    retrieved = rag_search(query)
    # ลบ rag_score ออกก่อนส่งให้ AI (ไม่ต้องการให้ AI เห็น internal score)
    return [{k: v for k, v in r.items() if k != "rag_score"} for r in retrieved]


def mock_db_check_tool(citizen_id: str) -> List[Dict[str, Any]]:
    """Agent 2 Tool: ดึงประวัติสิทธิ์จาก Mock DB"""
    logger.info(f"[Tool] ค้นหาข้อมูล Citizen ID: {citizen_id}")
    results = MOCK_CITIZEN_BENEFITS_DB.get(citizen_id, [])
    logger.info(f"[Tool] พบประวัติสิทธิ์ {len(results)} รายการ")
    return results

# ---------------------------------------------------------------------------
# 6. CORE API CALL HELPER
# ---------------------------------------------------------------------------

def call_typhoon_api(
    system_prompt: str,
    user_prompt:   str,
    output_model:  type,
    max_retries:   int   = 3,
    retry_delay:   float = 2.0,
) -> Any:
    from pydantic import ValidationError

    last_error: Optional[Exception] = None
    raw_content: str = ""

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"  → เรียก API (attempt {attempt}/{max_retries})...")

            response = client.chat.completions.create(
                model=MODEL_NAME,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt + "\n\nสำคัญ: ตอบกลับเป็น JSON เท่านั้น ห้ามมี Markdown, backtick, หรือข้อความอื่น",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=4096,
            )

            choice      = response.choices[0]
            raw_content = choice.message.content or ""

            if choice.finish_reason == "length":
                raise ValueError(f"Response ถูกตัดกลางคัน (finish_reason=length) ได้รับ {len(raw_content)} chars")

            if not raw_content.strip():
                raise ValueError("Model ส่งกลับ response ว่างเปล่า")

            clean = raw_content.strip()
            if clean.startswith("```"):
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else clean
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()

            parsed_dict = json.loads(clean)
            result      = output_model(**parsed_dict)

            logger.info(f"  ✅ API สำเร็จ (attempt {attempt})")
            return result

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"  ⚠️ JSON parse ล้มเหลว (attempt {attempt}): {e}")
            logger.warning(f"  Raw (200): {raw_content[:200]}")

        except ValidationError as e:
            last_error = e
            logger.warning(f"  ⚠️ ValidationError (attempt {attempt}):")
            for err in e.errors():
                logger.warning(f"     field={err['loc']} | {err['type']}: {err['msg']}")
            logger.warning(f"  Raw (200): {raw_content[:200]}")

        except Exception as e:
            last_error = e
            logger.warning(f"  ⚠️ {type(e).__name__} (attempt {attempt}): {e}")

        if attempt < max_retries:
            logger.info(f"  รอ {retry_delay}s ก่อน retry...")
            time.sleep(retry_delay)

    raise RuntimeError(
        f"API call ล้มเหลวหลังจาก {max_retries} attempts. "
        f"ข้อผิดพลาดล่าสุด: {type(last_error).__name__}: {last_error}"
    )

# ---------------------------------------------------------------------------
# 7. AGENT FUNCTIONS
# ---------------------------------------------------------------------------

def run_agent_1_rag(ui_data: Dict[str, Any]) -> Agent1Output:
    """
    Agent 1: RAG Retrieval + Policy Matching
    ใช้ Typhoon Embeddings ค้นหาสวัสดิการที่ semantic ใกล้เคียง
    แล้วให้ Typhoon LLM คัดกรองว่าใครมีคุณสมบัติจริง
    """
    logger.info("\n" + "=" * 60)
    logger.info("🤖 Agent 1: RAG Retrieval & Policy Matching")
    logger.info("=" * 60)

    citizen_profile = ui_data.get("citizen_profile", {})
    rag_context     = ui_data.get("rag_context", {})

    # ดึงสวัสดิการที่ relevant จาก RAG
    retrieved_policies = rag_retrieval_tool(citizen_profile, rag_context)

    if not retrieved_policies:
        logger.warning("[Agent 1] RAG ไม่พบสวัสดิการที่ relevant")
        return Agent1Output(possible_benefits=[], reasoning="ไม่พบสวัสดิการที่ตรงกับโปรไฟล์ผู้ลงทะเบียน")

    prompt = f"""
วิเคราะห์ข้อมูลผู้ลงทะเบียนและเลือกสวัสดิการที่เข้าเกณฑ์จริงๆ

ข้อมูลผู้ลงทะเบียน:
{json.dumps(citizen_profile, ensure_ascii=False, indent=2)}

สวัสดิการที่ RAG ค้นพบว่า relevant (อ่าน content เพื่อตรวจเกณฑ์):
{json.dumps(retrieved_policies, ensure_ascii=False, indent=2)}

คำสั่ง:
1. อ่าน content ของแต่ละสวัสดิการเพื่อดูเกณฑ์คุณสมบัติ
2. เลือกเฉพาะที่ผู้ลงทะเบียนมีคุณสมบัติตรงตามเกณฑ์จริงๆ
3. คัดลอก benefit_name และ category จากข้อมูลทุกครั้ง (ห้ามแต่ง)
4. อธิบายเหตุผลว่าทำไมถึงเลือกหรือตัดออก

ตอบกลับในรูปแบบ JSON:
{{
  "possible_benefits": [
    {{
      "benefit_name": "ชื่อสวัสดิการ (คัดลอกจากข้อมูล)",
      "category":     "หมวดหมู่ (คัดลอกจากข้อมูล)",
      "content":      "รายละเอียด (คัดลอกจากข้อมูล)"
    }}
  ],
  "reasoning": "เหตุผลที่เลือกและตัดสวัสดิการแต่ละรายการ"
}}
"""

    return call_typhoon_api(
        system_prompt="คุณคือ AI ผู้เชี่ยวชาญด้านการคัดกรองสวัสดิการรัฐ ทำงานด้วยความถูกต้องและแม่นยำ",
        user_prompt=prompt,
        output_model=Agent1Output,
    )


def run_agent_2_db_verification(citizen_id: str, agent1_result: Agent1Output) -> Agent2Output:
    """
    Agent 2: ตรวจสอบสิทธิ์ทับซ้อนกับ Mock DB
    """
    logger.info("\n" + "=" * 60)
    logger.info("🤖 Agent 2: DB Verification (Overlap Check)")
    logger.info("=" * 60)

    if not citizen_id:
        raise ValueError("citizen_id ไม่สามารถเป็นค่าว่างได้")

    existing_benefits = mock_db_check_tool(citizen_id)

    # ถ้า Agent 1 ไม่พบสิทธิ์ใหม่ ส่งแค่ Active benefits เดิม
    if not agent1_result.possible_benefits:
        return Agent2Output(
            approved_new_benefits=[],
            existing_active_benefits=[
                ExistingBenefitItem(**b)
                for b in existing_benefits
                if b.get("status") == "Active"
            ],
        )

    prompt = f"""
ตรวจสอบสิทธิ์ทับซ้อนระหว่างสวัสดิการใหม่กับสวัสดิการเดิมในระบบ

สวัสดิการใหม่ที่เสนอ (จาก Agent 1):
{json.dumps([b.model_dump() for b in agent1_result.possible_benefits], ensure_ascii=False, indent=2)}

สวัสดิการเดิมในระบบ (Mock DB):
{json.dumps(existing_benefits, ensure_ascii=False, indent=2)}

กฎการตรวจสอบ:
1. ถ้าสวัสดิการใหม่มีชื่อซ้ำกับสวัสดิการเดิมที่ status = "Active" → ตัดออก (ทับซ้อน)
2. ถ้าสวัสดิการเดิม status = "Expired" หรือไม่มีในระบบ → ถือเป็นสิทธิ์ใหม่ที่รับได้
3. existing_active_benefits คือสวัสดิการ status = "Active" เท่านั้น

ตอบกลับในรูปแบบ JSON:
{{
  "approved_new_benefits": [
    {{
      "benefit_name": "ชื่อสวัสดิการ",
      "category":     "หมวดหมู่",
      "content":      "รายละเอียด"
    }}
  ],
  "existing_active_benefits": [
    {{
      "benefit_name":  "ชื่อสวัสดิการ",
      "status":        "Active",
      "approved_date": "วันที่อนุมัติ"
    }}
  ]
}}
"""

    return call_typhoon_api(
        system_prompt="คุณคือ AI ตรวจสอบฐานข้อมูลและสิทธิ์ซ้ำซ้อนอย่างแม่นยำ",
        user_prompt=prompt,
        output_model=Agent2Output,
    )


def run_agent_3_summary_with_value(ui_data: Dict[str, Any], agent2_result: Agent2Output) -> FinalSummaryOutput:
    """
    Agent 3: สรุปผลลัพธ์ + วิเคราะห์ความคุ้มค่าแต่ละสิทธิ์
    ให้ผู้รับบริการตัดสินใจเลือกเองจาก benefit_analysis
    """
    logger.info("\n" + "=" * 60)
    logger.info("🤖 Agent 3: Summary + Value Analysis")
    logger.info("=" * 60)

    profile = (
        ui_data.get("citizen_profile", {})
               .get("personal_information", {})
    )
    full_name = f"{profile.get('first_name', 'ไม่ระบุ')} {profile.get('last_name', '')}".strip()

    # สร้างข้อมูล economic context เพื่อให้ AI วิเคราะห์ความคุ้มค่าได้แม่นยำขึ้น
    economic  = ui_data.get("citizen_profile", {}).get("economic_information", {})
    household = ui_data.get("citizen_profile", {}).get("household_information", {})

    prompt = f"""
สรุปและวิเคราะห์ความคุ้มค่าสวัสดิการสำหรับเจ้าหน้าที่และผู้รับบริการ

ชื่อผู้ลงทะเบียน: {full_name}

ข้อมูลเศรษฐกิจ:
- รายได้ต่อเดือน: {economic.get('monthly_income', 'ไม่ระบุ')} บาท
- ค่าใช้จ่ายต่อเดือน: {economic.get('monthly_expense', 'ไม่ระบุ')} บาท
- อาชีพ: {economic.get('occupation', 'ไม่ระบุ')}
- สมาชิกในครัวเรือน: {household.get('household_members', 'ไม่ระบุ')} คน

สิทธิ์ที่มีอยู่แล้ว (Active):
{json.dumps([b.model_dump() for b in agent2_result.existing_active_benefits], ensure_ascii=False, indent=2)}

สิทธิ์ใหม่ที่ผ่านการตรวจสอบแล้ว (ไม่ทับซ้อน):
{json.dumps([b.model_dump() for b in agent2_result.approved_new_benefits], ensure_ascii=False, indent=2)}

คำสั่ง:
1. สรุปภาพรวมสถานการณ์สวัสดิการของผู้ลงทะเบียน
2. วิเคราะห์ความคุ้มค่าของสิทธิ์ใหม่แต่ละรายการ ได้แก่:
   - eligibility_chance: โอกาสที่จะผ่านเกณฑ์ (สูงมาก/สูง/ปานกลาง/ต่ำ)
   - estimated_value: มูลค่าที่คาดว่าจะได้รับ
   - pros: ข้อดี 2-3 ข้อ
   - cons: ข้อจำกัด/เงื่อนไขที่ต้องระวัง 1-2 ข้อ
   - required_documents: เอกสารที่ต้องเตรียม
   - recommendation_score: คะแนนแนะนำ 1-10 ตามความเหมาะสมกับโปรไฟล์นี้
3. decision_note: เขียนหมายเหตุสั้นๆ สำหรับผู้รับบริการในการตัดสินใจเลือกสิทธิ์

ตอบกลับในรูปแบบ JSON:
{{
  "citizen_name": "{full_name}",
  "status": "แนะนำสิทธิ์เพิ่มเติม หรือ ข้อมูลครบถ้วน ไม่มีสิทธิ์เพิ่มเติม",
  "benefit_analysis": [
    {{
      "benefit_name":         "ชื่อสิทธิ์",
      "category":             "หมวดหมู่",
      "eligibility_chance":   "สูงมาก",
      "estimated_value":      "600-1,000 บาท/เดือน",
      "pros":                 ["ข้อดี 1", "ข้อดี 2"],
      "cons":                 ["ข้อจำกัด 1"],
      "required_documents":   ["เอกสาร 1", "เอกสาร 2"],
      "recommendation_score": 9
    }}
  ],
  "recommended_actions": ["สิ่งที่เจ้าหน้าที่ต้องทำ 1", "สิ่งที่เจ้าหน้าที่ต้องทำ 2"],
  "summary_text": "บทสรุปสำหรับเจ้าหน้าที่...",
  "decision_note": "หมายเหตุสำหรับผู้รับบริการในการตัดสินใจ..."
}}
"""

    return call_typhoon_api(
        system_prompt=(
            "คุณคือ AI ที่ปรึกษาสวัสดิการสำหรับเจ้าหน้าที่สังคมสงเคราะห์ "
            "วิเคราะห์ความคุ้มค่าอย่างตรงไปตรงมา ตอบเป็นภาษาไทยที่เป็นทางการและเข้าใจง่าย"
        ),
        user_prompt=prompt,
        output_model=FinalSummaryOutput,
    )

# ---------------------------------------------------------------------------
# 8. MAIN WORKFLOW
# ---------------------------------------------------------------------------

def run_pipeline(ui_input_json: Dict[str, Any]) -> Optional[FinalSummaryOutput]:
    """
    รัน Multi-Agent Pipeline
    Agent 1 (RAG) → Agent 2 (DB Overlap Check) → Agent 3 (Summary + Value Analysis)
    """
    citizen_id = (
        ui_input_json
        .get("citizen_profile", {})
        .get("personal_information", {})
        .get("citizen_id")
    )
    if not citizen_id:
        raise ValueError("❌ ไม่พบ citizen_id ใน citizen_profile.personal_information.citizen_id")

    logger.info(f"\n🚀 เริ่มต้น Pipeline สำหรับ Citizen ID: {citizen_id}")

    # Build RAG index ก่อนรัน pipeline
    build_policy_index()

    try:
        # Step 1: RAG Retrieval + Policy Matching
        agent1_res = run_agent_1_rag(ui_input_json)
        logger.info("\n📋 [Agent 1 Output]:")
        logger.info(agent1_res.model_dump_json(indent=2, ensure_ascii=False))

        # Step 2: DB Overlap Verification
        agent2_res = run_agent_2_db_verification(citizen_id, agent1_res)
        logger.info("\n📋 [Agent 2 Output]:")
        logger.info(agent2_res.model_dump_json(indent=2, ensure_ascii=False))

        # Step 3: Summary + Value Analysis
        final_report = run_agent_3_summary_with_value(ui_input_json, agent2_res)
        logger.info("\n📋 [Agent 3 - Final Report]:")
        logger.info(json.dumps(final_report.model_dump(), indent=2, ensure_ascii=False))

        return final_report

    except RuntimeError as e:
        logger.error(f"❌ Pipeline ล้มเหลว: {e}")
        return None
    except ValueError as e:
        logger.error(f"❌ ข้อมูลไม่ถูกต้อง: {e}")
        return None


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ui_input_json = {
        "citizen_profile": {
            "personal_information": {
                "first_name":   "เนิส",
                "last_name":    "ดีใจ อยากใจดี",
                "citizen_id":   "1234567890123",
                "date_of_birth":"2005-10-09",
                "age":          20,
                "phone_number": "0812345678",
            },
            "address_information": {
                "province":    "กรุงเทพมหานคร",
                "district":    "จตุจักร",
                "subdistrict": "ลาดยาว",
                "postal_code": "10900",
                "full_address":"123/4 หมู่บ้านสุขใจ",
            },
            "household_information": {
                "household_members":  1,
                "elderly":            0,
                "children":           0,
                "disabled_persons":   0,
                "living_arrangement": "Living Alone",
            },
            "economic_information": {
                "occupation":        "นักศึกษา",
                "monthly_income":    1000,
                "monthly_expense":   3500,
                "employment_status": "Student",
            },
            "vulnerable_groups": ["Low Income"],
            "case_notes": "ต้องการความช่วยเหลือเรื่องค่าครองชีพและค่าใช้จ่ายด้านการศึกษา",
        },
        "structured_data": {
            "case_type":       "welfare_intake",
            "readiness_score": 50,
            "generated_at":    "2026-06-18T10:30:00.000Z",
            "officer_unit":    "หน่วยรับเรื่องสวัสดิการ",
        },
        "rag_context": {
            "summary":  "นักศึกษาที่อาศัยอยู่คนเดียว มีรายได้ไม่เพียงพอต่อค่าใช้จ่ายรายเดือน",
            "keywords": ["นักศึกษา", "อยู่ลำพัง", "รายได้น้อย"],
        },
    }

    result = run_pipeline(ui_input_json)

    if result:
        print("\n" + "=" * 60)
        print("✅ ผลลัพธ์สุดท้าย")
        print("=" * 60)

        # แสดง benefit analysis แบบอ่านง่าย
        if result.benefit_analysis:
            print(f"\n📊 วิเคราะห์ความคุ้มค่า ({len(result.benefit_analysis)} สิทธิ์ที่แนะนำ):")
            for i, b in enumerate(result.benefit_analysis, 1):
                print(f"\n  [{i}] {b.benefit_name} ({b.category})")
                print(f"      โอกาสได้รับ : {b.eligibility_chance}")
                print(f"      มูลค่าโดยประมาณ: {b.estimated_value}")
                print(f"      คะแนนแนะนำ  : {b.recommendation_score}/10")
                print(f"      ข้อดี       : {', '.join(b.pros)}")
                print(f"      ข้อจำกัด    : {', '.join(b.cons)}")
                print(f"      เอกสารที่ต้องใช้: {', '.join(b.required_documents)}")

        print(f"\n📝 สรุป: {result.summary_text}")
        print(f"\n💡 หมายเหตุสำหรับผู้รับบริการ:\n   {result.decision_note}")
        print(f"\n✅ การดำเนินการต่อ:")
        for action in result.recommended_actions:
            print(f"   • {action}")

        print("\n" + "=" * 60)
        print("JSON Output (สำหรับ UI):")
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    else:
        print("\n❌ Pipeline ไม่สำเร็จ กรุณาตรวจสอบ log ด้านบน")
