import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI
from dotenv import load_dotenv

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
MODEL_NAME = "typhoon-v2.5-30b-a3b-instruct"

# ✅ FIX #7: Validate API Key ก่อนเริ่มระบบ
if not TYPHOON_API_KEY:
    raise EnvironmentError(
        "❌ TYPHOON_API_KEY ไม่ได้ถูกกำหนดค่า "
        "กรุณาสร้างไฟล์ .env และใส่ค่า TYPHOON_API_KEY=your_key_here"
    )

logger.info(f"✅ TYPHOON_API_KEY: พบค่าแล้ว (ความยาว {len(TYPHOON_API_KEY)} ตัวอักษร)")

client = OpenAI(api_key=TYPHOON_API_KEY, base_url=TYPHOON_BASE_URL)

# ---------------------------------------------------------------------------
# 2. BENEFIT DATABASE (จาก CSV จริง)
# ---------------------------------------------------------------------------

# ข้อมูลสวัสดิการทั้งหมด — โหลดจาก CSV (document_id, benefit_id, benefit_name, category, content)
# tags สร้างจาก category และคำสำคัญใน content เพื่อใช้ filter ใน mock_scraping_tool
ALL_POLICIES: List[Dict[str, Any]] = [
    {
        "benefit_id": 1,
        "benefit_name": "เบี้ยยังชีพผู้สูงอายุ",
        "category": "Elderly",
        "content": "ชื่อสิทธิ์: เบี้ยยังชีพผู้สูงอายุ กลุ่มเป้าหมาย: ผู้สูงอายุ คุณสมบัติ: อายุ 60 ปีขึ้นไป สัญชาติไทย มีชื่อในทะเบียนบ้าน เอกสาร: บัตรประชาชน ทะเบียนบ้าน หน่วยงาน: องค์กรปกครองส่วนท้องถิ่น",
        "tags": ["ผู้สูงอายุ", "elderly", "อายุ 60", "เบี้ย"]
    },
    {
        "benefit_id": 2,
        "benefit_name": "เบี้ยความพิการ",
        "category": "Disability",
        "content": "ชื่อสิทธิ์: เบี้ยความพิการ กลุ่มเป้าหมาย: คนพิการ คุณสมบัติ: มีบัตรประจำตัวคนพิการ สัญชาติไทย เอกสาร: บัตรคนพิการ บัตรประชาชน หน่วยงาน: กรมส่งเสริมและพัฒนาคุณภาพชีวิตคนพิการ",
        "tags": ["คนพิการ", "disability", "พิการ", "เบี้ย"]
    },
    {
        "benefit_id": 3,
        "benefit_name": "เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด",
        "category": "Child Welfare",
        "content": "ชื่อสิทธิ์: เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด กลุ่มเป้าหมาย: ครัวเรือนรายได้น้อยที่มีเด็กแรกเกิด คุณสมบัติ: เด็กแรกเกิดตามเกณฑ์ของรัฐ เอกสาร: สูติบัตร ทะเบียนบ้าน",
        "tags": ["เด็ก", "child", "แรกเกิด", "รายได้น้อย", "เงินอุดหนุน"]
    },
    {
        "benefit_id": 4,
        "benefit_name": "บัตรสวัสดิการแห่งรัฐ",
        "category": "Financial Support",
        "content": "ชื่อสิทธิ์: บัตรสวัสดิการแห่งรัฐ กลุ่มเป้าหมาย: ผู้มีรายได้น้อย คุณสมบัติ: ผ่านเกณฑ์รายได้และทรัพย์สินที่กำหนด สิทธิประโยชน์: ส่วนลดค่าน้ำ ค่าไฟ ค่าเดินทาง และวงเงินซื้อสินค้า",
        "tags": ["รายได้น้อย", "low income", "financial", "บัตรสวัสดิการ", "ค่าน้ำ", "ค่าไฟ"]
    },
    {
        "benefit_id": 5,
        "benefit_name": "สิทธิหลักประกันสุขภาพแห่งชาติ",
        "category": "Healthcare",
        "content": "ชื่อสิทธิ์: สิทธิหลักประกันสุขภาพแห่งชาติ กลุ่มเป้าหมาย: ประชาชนทั่วไป คุณสมบัติ: ไม่มีสิทธิรักษาพยาบาลอื่น สิทธิประโยชน์: รับบริการตามสิทธิบัตรทอง",
        "tags": ["สุขภาพ", "healthcare", "บัตรทอง", "รักษาพยาบาล"]
    },
    {
        "benefit_id": 6,
        "benefit_name": "สิทธิประกันสังคม",
        "category": "Healthcare",
        "content": "ชื่อสิทธิ์: สิทธิประกันสังคม กลุ่มเป้าหมาย: ผู้ประกันตน คุณสมบัติ: เป็นผู้ประกันตนมาตรา 33 39 หรือ 40 สิทธิประโยชน์: ค่ารักษาพยาบาล เงินทดแทน และสวัสดิการตามกฎหมาย",
        "tags": ["ประกันสังคม", "social security", "ผู้ประกันตน", "รักษาพยาบาล"]
    },
    {
        "benefit_id": 7,
        "benefit_name": "สิทธิรักษาพยาบาลข้าราชการ",
        "category": "Healthcare",
        "content": "ชื่อสิทธิ์: สิทธิรักษาพยาบาลข้าราชการ กลุ่มเป้าหมาย: ข้าราชการและครอบครัว คุณสมบัติ: มีสิทธิสวัสดิการรักษาพยาบาลข้าราชการ",
        "tags": ["ข้าราชการ", "government", "รักษาพยาบาล", "สวัสดิการ"]
    },
    {
        "benefit_id": 8,
        "benefit_name": "สถานพยาบาลประจำสิทธิรักษาพยาบาล",
        "category": "Healthcare",
        "content": "ข้อมูลสถานพยาบาลประจำตามสิทธิรักษาพยาบาลที่ประชาชนสังกัดอยู่ ใช้สำหรับการอ้างอิงและส่งต่อบริการ",
        "tags": ["สถานพยาบาล", "hospital", "รักษาพยาบาล", "สิทธิ"]
    },
    {
        "benefit_id": 9,
        "benefit_name": "สถานะผู้มีสิทธิบัตรสวัสดิการแห่งรัฐ 2569",
        "category": "Financial Support",
        "content": "ข้อมูลสถานะการผ่านเกณฑ์ผู้มีสิทธิในโครงการสวัสดิการแห่งรัฐ ปี 2569",
        "tags": ["รายได้น้อย", "บัตรสวัสดิการ", "สถานะ", "2569", "financial"]
    },
    {
        "benefit_id": 10,
        "benefit_name": "สถานะการลงทะเบียนสวัสดิการแห่งรัฐ 2569",
        "category": "Financial Support",
        "content": "ข้อมูลสถานะการลงทะเบียน การตรวจสอบ และผลการพิจารณาโครงการสวัสดิการแห่งรัฐ ปี 2569",
        "tags": ["รายได้น้อย", "บัตรสวัสดิการ", "ลงทะเบียน", "2569", "financial"]
    },
]

# ประวัติสิทธิ์ของแต่ละ Citizen ID — ใช้ benefit_name ตรงกับ ALL_POLICIES
# status: "Active" = กำลังได้รับสิทธิ์, "Expired" = หมดอายุแล้ว
MOCK_CITIZEN_BENEFITS_DB: Dict[str, List[Dict[str, Any]]] = {
    "1234567890123": [
        {
            "benefit_name": "เบี้ยยังชีพผู้สูงอายุ",
            "status": "Active",
            "approved_date": "2025-01-10"
        },
        {
            "benefit_name": "บัตรสวัสดิการแห่งรัฐ",
            "status": "Expired",
            "approved_date": "2024-01-01"
        }
    ]
}

# ---------------------------------------------------------------------------
# 3. PYDANTIC OUTPUT MODELS
# ---------------------------------------------------------------------------

class BenefitItem(BaseModel):
    """
    Model สำหรับรายการสวัสดิการ
    ใช้ field จาก CSV จริง: benefit_name, category, content
    คง criteria/amount ไว้เป็น optional เพื่อ backward compat
    """
    benefit_name: str
    category: str = ""
    content: str = ""
    # optional fields — อาจมีถ้า model สร้างขึ้นมาเอง
    criteria: str = ""
    amount: str = ""

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount_to_str(cls, v: Any) -> str:
        '''แปลง int/float → str อัตโนมัติ เช่น 700 → "700"'''
        if isinstance(v, (int, float)):
            return str(v)
        return str(v) if v is not None else ""


class ExistingBenefitItem(BaseModel):
    """model ย่อยสำหรับสวัสดิการที่มีอยู่แล้วใน DB"""
    benefit_name: str
    status: str = ""
    approved_date: str = ""


class Agent1Output(BaseModel):
    possible_benefits: List[BenefitItem] = Field(
        default=[],
        description="รายการสวัสดิการภายนอกที่สอดคล้องกับโปรไฟล์ผู้ใช้"
    )
    reasoning: str = Field(
        default="",
        description="เหตุผลประกอบในการเลือกสวัสดิการเหล่านี้"
    )


class Agent2Output(BaseModel):
    approved_new_benefits: List[BenefitItem] = Field(
        default=[],
        description="รายการสวัสดิการใหม่ที่ผ่านการตรวจสอบแล้วว่าไม่ทับซ้อนและมีสิทธิ์ได้รับ"
    )
    existing_active_benefits: List[ExistingBenefitItem] = Field(
        default=[],
        description="รายการสวัสดิการเดิมที่ระบบพบใน DB และยังมีผลอยู่"
    )


class FinalSummaryOutput(BaseModel):
    citizen_name: str
    status: str = Field(
        description="สรุปสถานะการดำเนินการ เช่น แนะนำสิทธิ์เพิ่มเติม / ข้อมูลครบถ้วน"
    )
    recommended_actions: List[str] = Field(
        default=[],
        description="สิ่งที่เจ้าหน้าที่ต้องดำเนินการต่อ"
    )
    summary_text: str = Field(
        description="บทสรุปภาษาไทยที่สละสลวยสำหรับแสดงผลบน UI"
    )

# ---------------------------------------------------------------------------
# 4. TOOLS
# ---------------------------------------------------------------------------

def mock_scraping_tool(keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Agent 1 Tool: กรองสวัสดิการจาก ALL_POLICIES (CSV data) ตาม keywords
    ค้นหาใน: benefit_name, category, content, tags
    ส่งให้ AI เฉพาะ field ที่จำเป็น (ไม่ส่ง tags)
    """
    logger.info(f"[Tool] Scraping สำหรับ keywords: {keywords}")

    # ถ้าไม่มี keyword ส่งทั้งหมด
    if not keywords:
        return [
            {k: v for k, v in p.items() if k != "tags"}
            for p in ALL_POLICIES
        ]

    matched = []
    keywords_lower = [kw.lower() for kw in keywords]

    for policy in ALL_POLICIES:
        # รวม text ทุก field ที่ค้นได้: benefit_name + category + content + tags
        searchable_text = " ".join([
            policy.get("benefit_name", ""),
            policy.get("category", ""),
            policy.get("content", ""),
            " ".join(policy.get("tags", []))
        ]).lower()

        if any(kw in searchable_text for kw in keywords_lower):
            # ส่งเฉพาะ field ที่ AI ต้องใช้ ไม่ส่ง tags (internal only)
            matched.append({
                "benefit_id":   policy["benefit_id"],
                "benefit_name": policy["benefit_name"],
                "category":     policy["category"],
                "content":      policy["content"],
            })

    logger.info(f"[Tool] พบนโยบายที่ตรงกัน {len(matched)} รายการ")
    return matched


def mock_db_check_tool(citizen_id: str) -> List[Dict[str, Any]]:
    """
    Agent 2 Tool: ดึงข้อมูลประวัติสิทธิ์จาก Database
    """
    logger.info(f"[Tool] ค้นหาข้อมูล Citizen ID: {citizen_id}")
    results = MOCK_CITIZEN_BENEFITS_DB.get(citizen_id, [])
    logger.info(f"[Tool] พบประวัติสิทธิ์ {len(results)} รายการ")
    return results

# ---------------------------------------------------------------------------
# 5. CORE API CALL HELPER (with Retry + JSON fallback)
# ---------------------------------------------------------------------------

def call_typhoon_api(
    system_prompt: str,
    user_prompt: str,
    output_model: type,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Any:
    """
    ✅ FIX #1: JSON mode + Pydantic parse (ไม่ใช้ .beta.parse)
    ✅ FIX #2: ตรวจสอบ response ก่อน parse
    ✅ FIX #6: Retry mechanism
    ✅ FIX ROOT CAUSE: แยก ValidationError ออกมา log ให้ชัดเจน
    """
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
                        "content": (
                            system_prompt
                            + "\n\nสำคัญ: ตอบกลับเป็น JSON เท่านั้น "
                            "ห้ามมี Markdown, backtick, หรือข้อความอื่น"
                        )
                    },
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=4096,  # ✅ FIX: เพิ่มเพื่อรองรับ JSON ภาษาไทยขนาดใหญ่
            )

            choice = response.choices[0]
            raw_content = choice.message.content or ""

            # ✅ FIX: ตรวจสอบว่า response ถูกตัดกลางคันหรือไม่
            if choice.finish_reason == "length":
                raise ValueError(
                    f"Response ถูกตัดกลางคัน (finish_reason=length) "
                    f"ได้รับ {len(raw_content)} chars — ลองลดขนาด prompt"
                )

            if not raw_content.strip():
                raise ValueError("Model ส่งกลับ response ว่างเปล่า")

            # ทำความสะอาด backtick ที่อาจติดมา
            clean_content = raw_content.strip()
            if clean_content.startswith("```"):
                parts = clean_content.split("```")
                clean_content = parts[1] if len(parts) > 1 else clean_content
                if clean_content.startswith("json"):
                    clean_content = clean_content[4:]
            clean_content = clean_content.strip()

            # Parse JSON
            parsed_dict = json.loads(clean_content)

            # ✅ สร้าง Pydantic model — ValidationError จะถูก catch แยกด้านล่าง
            result = output_model(**parsed_dict)

            logger.info(f"  ✅ API สำเร็จ (attempt {attempt})")
            return result

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"  ⚠️ JSON parse ล้มเหลว (attempt {attempt}): {e}")
            logger.warning(f"  Raw response (200 chars): {raw_content[:200]}")

        except ValidationError as e:
            # ✅ ROOT CAUSE FIX: แสดง field ที่ผิดพลาดให้ชัดเจน
            last_error = e
            logger.warning(f"  ⚠️ Pydantic ValidationError (attempt {attempt}):")
            for err in e.errors():
                logger.warning(f"     field={err['loc']} | type={err['type']} | msg={err['msg']}")
            logger.warning(f"  Raw response (200 chars): {raw_content[:200]}")

        except Exception as e:
            last_error = e
            # ✅ แสดง full error แทนที่จะซ่อน
            logger.warning(
                f"  ⚠️ เกิดข้อผิดพลาด (attempt {attempt}): "
                f"{type(e).__name__}: {e}"
            )

        if attempt < max_retries:
            logger.info(f"  รอ {retry_delay} วินาทีก่อน retry...")
            time.sleep(retry_delay)

    raise RuntimeError(
        f"API call ล้มเหลวหลังจาก {max_retries} attempts. "
        f"ข้อผิดพลาดล่าสุด: {type(last_error).__name__}: {last_error}"
    )

# ---------------------------------------------------------------------------
# 6. AGENT FUNCTIONS
# ---------------------------------------------------------------------------

def run_agent_1_scraping(ui_data: Dict[str, Any]) -> Agent1Output:
    """
    Agent 1: วิเคราะห์โปรไฟล์ผู้ใช้และแมตช์นโยบายสวัสดิการที่เข้าเกณฑ์
    """
    logger.info("\n" + "="*60)
    logger.info("🤖 Agent 1: Scraping & Policy Matching Agent")
    logger.info("="*60)

    keywords = (
        ui_data
        .get("rag_context", {})
        .get("keywords", ["ผู้สูงอายุ", "รายได้น้อย"])
    )

    scraped_policies = mock_scraping_tool(keywords)

    if not scraped_policies:
        logger.warning("ไม่พบนโยบายที่ตรงกับ keywords ที่กำหนด")
        return Agent1Output(
            possible_benefits=[],
            reasoning="ไม่พบสวัสดิการที่ตรงกับ keywords ที่ระบุ"
        )

    # ✅ FIX #3: เพิ่ม type hint ใน function signature (ดูด้านบน)
    citizen_profile = ui_data.get("citizen_profile", {})

    prompt = f"""
วิเคราะห์ข้อมูลผู้ลงทะเบียนและเลือกสวัสดิการที่เข้าเกณฑ์จริงๆ

ข้อมูลผู้ลงทะเบียน:
{json.dumps(citizen_profile, ensure_ascii=False, indent=2)}

รายการสวัสดิการที่ค้นพบ (แต่ละรายการมี benefit_name, category, content ที่อธิบายเกณฑ์คุณสมบัติ):
{json.dumps(scraped_policies, ensure_ascii=False, indent=2)}

คำสั่ง:
1. อ่าน content ของแต่ละสวัสดิการเพื่อดูเกณฑ์คุณสมบัติ
2. เลือกเฉพาะสวัสดิการที่ผู้ลงทะเบียนคนนี้มีคุณสมบัติตรงตามเกณฑ์จริงๆ
3. คัดลอก benefit_name และ category จากข้อมูลที่ได้รับมาทุกครั้ง (ห้ามแต่ง)
4. อธิบายเหตุผลประกอบว่าทำไมถึงเลือกหรือไม่เลือก

ตอบกลับในรูปแบบ JSON ดังนี้:
{{
  "possible_benefits": [
    {{
      "benefit_name": "ชื่อสวัสดิการ (คัดลอกจากข้อมูล)",
      "category": "หมวดหมู่ (คัดลอกจากข้อมูล)",
      "content": "รายละเอียดสวัสดิการ (คัดลอกจากข้อมูล)"
    }}
  ],
  "reasoning": "เหตุผลที่เลือกสวัสดิการเหล่านี้"
}}
"""

    return call_typhoon_api(
        system_prompt="คุณคือ AI ผู้เชี่ยวชาญด้านการคัดกรองสวัสดิการรัฐ ทำงานด้วยความถูกต้องและแม่นยำ",
        user_prompt=prompt,
        output_model=Agent1Output
    )


def run_agent_2_db_verification(citizen_id: str, agent1_result: Agent1Output) -> Agent2Output:
    """
    Agent 2: ตรวจสอบสิทธิ์ทับซ้อนกับฐานข้อมูล
    """
    logger.info("\n" + "="*60)
    logger.info("🤖 Agent 2: DB Verification Agent")
    logger.info("="*60)

    # ✅ FIX #8: Validate citizen_id ก่อนใช้งาน
    if not citizen_id:
        raise ValueError("citizen_id ไม่สามารถเป็นค่าว่างได้")

    existing_benefits = mock_db_check_tool(citizen_id)

    # กรณีไม่มีสิทธิ์ใหม่จาก Agent 1
    if not agent1_result.possible_benefits:
        return Agent2Output(
            approved_new_benefits=[],
            existing_active_benefits=[
                b for b in existing_benefits if b.get("status") == "Active"
            ]
        )

    prompt = f"""
ตรวจสอบสิทธิ์ทับซ้อนระหว่างสวัสดิการใหม่และสวัสดิการเดิมในระบบ

สวัสดิการใหม่ที่เสนอ:
{json.dumps([b.model_dump() for b in agent1_result.possible_benefits], ensure_ascii=False, indent=2)}

สวัสดิการเดิมในระบบ (Database):
{json.dumps(existing_benefits, ensure_ascii=False, indent=2)}

กฎการตรวจสอบ:
1. ถ้าสวัสดิการใหม่มีชื่อซ้ำกับสวัสดิการเดิมที่ status = "Active" → ตัดออก (ทับซ้อน)
2. ถ้าสวัสดิการเดิม status = "Expired" หรือไม่เคยมีในระบบ → ถือเป็นสิทธิ์ใหม่ที่รับได้
3. existing_active_benefits คือสวัสดิการเดิมที่ status = "Active" เท่านั้น

ตอบกลับในรูปแบบ JSON ดังนี้:
{{
  "approved_new_benefits": [
    {{
      "benefit_name": "ชื่อสวัสดิการ",
      "criteria": "เกณฑ์",
      "amount": "จำนวนเงิน"
    }}
  ],
  "existing_active_benefits": [
    {{
      "benefit_name": "ชื่อสวัสดิการ",
      "status": "Active",
      "approved_date": "วันที่อนุมัติ"
    }}
  ]
}}
"""

    return call_typhoon_api(
        system_prompt="คุณคือ AI ตรวจสอบฐานข้อมูลและสิทธิ์ซ้ำซ้อนอย่างแม่นยำ",
        user_prompt=prompt,
        output_model=Agent2Output
    )


def run_agent_3_summary(ui_data: Dict[str, Any], agent2_result: Agent2Output) -> FinalSummaryOutput:
    """
    Agent 3: สรุปผลลัพธ์สุดท้ายสำหรับเจ้าหน้าที่
    """
    logger.info("\n" + "="*60)
    logger.info("🤖 Agent 3: Summary Agent")
    logger.info("="*60)

    # ✅ FIX #4: ใช้ .get() พร้อม fallback ป้องกัน KeyError
    profile = (
        ui_data
        .get("citizen_profile", {})
        .get("personal_information", {})
    )
    first_name = profile.get("first_name", "ไม่ระบุ")
    last_name = profile.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip()

    prompt = f"""
สรุปผลการตรวจสอบสวัสดิการสำหรับเจ้าหน้าที่

ชื่อผู้ลงทะเบียน: {full_name}

สิทธิ์ปัจจุบันในระบบ (Active):
{json.dumps([b.model_dump() for b in agent2_result.existing_active_benefits], ensure_ascii=False, indent=2)}

สิทธิ์ใหม่ที่แนะนำให้ดำเนินการ:
{json.dumps([b.model_dump() for b in agent2_result.approved_new_benefits], ensure_ascii=False, indent=2)}

คำสั่ง:
1. สรุปเป็นภาษาไทยที่กระชับ ชัดเจน เป็นทางการ
2. ระบุสิ่งที่เจ้าหน้าที่ต้องทำต่อในรูปแบบรายการ
3. status: ถ้ามีสิทธิ์ใหม่ → "แนะนำสิทธิ์เพิ่มเติม" / ถ้าไม่มี → "ข้อมูลครบถ้วน ไม่มีสิทธิ์เพิ่มเติม"

ตอบกลับในรูปแบบ JSON ดังนี้:
{{
  "citizen_name": "{full_name}",
  "status": "สถานะการดำเนินการ",
  "recommended_actions": ["การดำเนินการที่ 1", "การดำเนินการที่ 2"],
  "summary_text": "บทสรุปสำหรับเจ้าหน้าที่..."
}}
"""

    return call_typhoon_api(
        system_prompt="คุณคือ AI สรุปเคสสำหรับเจ้าหน้าที่สังคมสงเคราะห์ ตอบเป็นภาษาไทยที่เป็นทางการและเข้าใจง่าย",
        user_prompt=prompt,
        output_model=FinalSummaryOutput
    )

# ---------------------------------------------------------------------------
# 7. MAIN WORKFLOW
# ---------------------------------------------------------------------------

def run_pipeline(ui_input_json: Dict[str, Any]) -> Optional[FinalSummaryOutput]:
    """
    รัน Multi-Agent Pipeline ตามลำดับ (Sequential Pattern)
    Returns: FinalSummaryOutput หรือ None ถ้าเกิดข้อผิดพลาด
    """
    # ✅ FIX #8: ดึง citizen_id ครั้งเดียว และ validate ก่อนใช้
    citizen_id = (
        ui_input_json
        .get("citizen_profile", {})
        .get("personal_information", {})
        .get("citizen_id")
    )

    if not citizen_id:
        raise ValueError("❌ ไม่พบ citizen_id ในข้อมูลที่ส่งมา กรุณาตรวจสอบ citizen_profile.personal_information.citizen_id")

    logger.info(f"\n🚀 เริ่มต้น Pipeline สำหรับ Citizen ID: {citizen_id}")

    try:
        # Step 1: ค้นหาและแมตช์นโยบาย
        agent1_res = run_agent_1_scraping(ui_input_json)
        logger.info("\n📋 [Agent 1 Output]:")
        logger.info(agent1_res.model_dump_json(indent=2, ensure_ascii=False))

        # Step 2: ตรวจสอบประวัติสิทธิ์จาก DB
        agent2_res = run_agent_2_db_verification(citizen_id, agent1_res)
        logger.info("\n📋 [Agent 2 Output]:")
        logger.info(agent2_res.model_dump_json(indent=2, ensure_ascii=False))

        # Step 3: สรุปผลลัพธ์
        final_report = run_agent_3_summary(ui_input_json, agent2_res)
        logger.info("\n📋 [Agent 3 - Final Summary]:")
        logger.info(json.dumps(final_report.model_dump(), indent=2, ensure_ascii=False))

        return final_report

    except RuntimeError as e:
        logger.error(f"❌ Pipeline ล้มเหลว: {e}")
        logger.error("โปรดตรวจสอบ TYPHOON_API_KEY และการเชื่อมต่ออินเทอร์เน็ต")
        return None
    except ValueError as e:
        logger.error(f"❌ ข้อมูลไม่ถูกต้อง: {e}")
        return None


if __name__ == "__main__":
    # ข้อมูล Input จาก UI
    ui_input_json = {
        "citizen_profile": {
            "personal_information": {
                "first_name": "สมชาย",
                "last_name": "ใจดี",
                "citizen_id": "1234567890123",
                "date_of_birth": "1958-10-09",
                "age": 68,
                "phone_number": "0812345678"
            },
            "address_information": {
                "province": "กรุงเทพมหานคร",
                "district": "จตุจักร",
                "subdistrict": "ลาดยาว",
                "postal_code": "10900",
                "full_address": "123/4 หมู่บ้านสุขใจ"
            },
            "household_information": {
                "household_members": 1,
                "elderly": 1,
                "children": 0,
                "disabled_persons": 0,
                "living_arrangement": "Living Alone"
            },
            "economic_information": {
                "occupation": "ว่างงาน",
                "monthly_income": 2000,
                "monthly_expense": 3500,
                "employment_status": "Unemployed"
            },
            "vulnerable_groups": ["Elderly", "Low Income"],
            "case_notes": "ต้องการความช่วยเหลือเรื่องค่าครองชีพ"
        },
        "structured_data": {
            "case_type": "welfare_intake",
            "readiness_score": 80,
            "generated_at": "2026-06-18T10:30:00.000Z",
            "officer_unit": "หน่วยรับเรื่องสวัสดิการ"
        },
        "rag_context": {
            "summary": "ผู้สูงอายุอยู่ลำพัง รายได้ไม่เพียงพอต่อค่าใช้จ่าย",
            "keywords": ["ผู้สูงอายุ", "อยู่ลำพัง", "รายได้น้อย"]
        }
    }

    result = run_pipeline(ui_input_json)

    if result:
        print("\n" + "="*60)
        print("✅ ผลลัพธ์สุดท้าย")
        print("="*60)
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    else:
        print("\n❌ Pipeline ไม่สำเร็จ กรุณาตรวจสอบ log ด้านบน")