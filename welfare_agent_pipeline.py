"""
welfare_agent_pipeline.py
Multi-Agent Welfare Analysis Pipeline
Agent 1: RAG + Real Scraping (ค้นสิทธิ์ที่ควรได้ + ดูว่ามีแล้วจากเว็บจริง)
Agent 2: เปรียบเทียบสิทธิ์ที่ควรได้ VS มีแล้ว → หาช่องว่าง
Agent 3: สรุป (มีอะไรแล้ว / แนะนำอะไรเพิ่ม / EV analysis)
"""

import os, json, logging, time
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

# ---------------------------------------------------------------------------
# 0. LOGGING & ENV
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
load_dotenv()

# ---------------------------------------------------------------------------
# 1. CONFIG
# ---------------------------------------------------------------------------
TYPHOON_API_KEY = os.environ.get("TYPHOON_API_KEY")
TYPHOON_BASE_URL = "https://api.opentyphoon.ai/v1"
MODEL_NAME    = "typhoon-v2.5-30b-a3b-instruct"
RAG_TOP_K     = 6
RAG_MIN_SCORE = 0.15

if not TYPHOON_API_KEY:
    raise EnvironmentError("❌ TYPHOON_API_KEY ไม่ได้ถูกกำหนดค่า กรุณาสร้างไฟล์ .env")

client = OpenAI(api_key=TYPHOON_API_KEY, base_url=TYPHOON_BASE_URL)
logger.info(f"✅ TYPHOON_API_KEY พบแล้ว (len={len(TYPHOON_API_KEY)})")

# ---------------------------------------------------------------------------
# 2. POLICY DATABASE (RAG Source)
# ---------------------------------------------------------------------------
ALL_POLICIES: List[Dict[str, Any]] = [
    {"benefit_id":1, "benefit_name":"เบี้ยยังชีพผู้สูงอายุ", "category":"Elderly",
     "content":"กลุ่มเป้าหมาย: ผู้สูงอายุ คุณสมบัติ: อายุ 60 ปีขึ้นไป สัญชาติไทย มีชื่อในทะเบียนบ้าน เอกสาร: บัตรประชาชน ทะเบียนบ้าน หน่วยงาน: อปท."},
    {"benefit_id":2, "benefit_name":"เบี้ยความพิการ", "category":"Disability",
     "content":"กลุ่มเป้าหมาย: คนพิการ คุณสมบัติ: มีบัตรประจำตัวคนพิการ สัญชาติไทย เอกสาร: บัตรคนพิการ บัตรประชาชน หน่วยงาน: กรมส่งเสริมคุณภาพชีวิตคนพิการ"},
    {"benefit_id":3, "benefit_name":"เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด", "category":"Child Welfare",
     "content":"กลุ่มเป้าหมาย: ครัวเรือนรายได้น้อยที่มีเด็กแรกเกิด คุณสมบัติ: เด็กแรกเกิดตามเกณฑ์รัฐ เอกสาร: สูติบัตร ทะเบียนบ้าน"},
    {"benefit_id":4, "benefit_name":"บัตรสวัสดิการแห่งรัฐ", "category":"Financial Support",
     "content":"กลุ่มเป้าหมาย: ผู้มีรายได้น้อย คุณสมบัติ: ผ่านเกณฑ์รายได้และทรัพย์สิน สิทธิ์: ส่วนลดค่าน้ำ ค่าไฟ ค่าเดินทาง วงเงินซื้อสินค้า"},
    {"benefit_id":5, "benefit_name":"สิทธิหลักประกันสุขภาพแห่งชาติ", "category":"Healthcare",
     "content":"กลุ่มเป้าหมาย: ประชาชนทั่วไป คุณสมบัติ: ไม่มีสิทธิ์รักษาพยาบาลอื่น สิทธิ์: บัตรทองรับบริการสาธารณสุข"},
    {"benefit_id":6, "benefit_name":"สิทธิประกันสังคม", "category":"Healthcare",
     "content":"กลุ่มเป้าหมาย: ผู้ประกันตน คุณสมบัติ: มาตรา 33 39 หรือ 40 สิทธิ์: ค่ารักษาพยาบาล เงินทดแทน สวัสดิการ"},
    {"benefit_id":7, "benefit_name":"สิทธิรักษาพยาบาลข้าราชการ", "category":"Healthcare",
     "content":"กลุ่มเป้าหมาย: ข้าราชการและครอบครัว คุณสมบัติ: มีสิทธิ์สวัสดิการรักษาพยาบาลข้าราชการ"},
    {"benefit_id":8, "benefit_name":"สถานพยาบาลประจำสิทธิรักษาพยาบาล", "category":"Healthcare",
     "content":"ข้อมูลสถานพยาบาลประจำตามสิทธิ์ที่ประชาชนสังกัด ใช้อ้างอิงและส่งต่อบริการ"},
    {"benefit_id":9, "benefit_name":"สถานะผู้มีสิทธิบัตรสวัสดิการแห่งรัฐ 2569", "category":"Financial Support",
     "content":"สถานะการผ่านเกณฑ์ผู้มีสิทธิ์โครงการสวัสดิการแห่งรัฐ ปี 2569"},
    {"benefit_id":10, "benefit_name":"สถานะการลงทะเบียนสวัสดิการแห่งรัฐ 2569", "category":"Financial Support",
     "content":"สถานะการลงทะเบียน การตรวจสอบ และผลการพิจารณาโครงการสวัสดิการแห่งรัฐ ปี 2569"},
]

# ---------------------------------------------------------------------------
# 3. PYDANTIC MODELS
# ---------------------------------------------------------------------------

class BenefitItem(BaseModel):
    benefit_name: str
    category:     str = ""
    content:      str = ""
    criteria:     str = ""
    amount:       str = ""

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v: Any) -> str:
        if isinstance(v, (int, float)): return str(v)
        return str(v) if v is not None else ""


class ScrapedBenefitItem(BaseModel):
    """สิทธิ์ที่ได้จาก scraping จริง"""
    benefit_name:  str
    source_system: str = ""           # eSocial / HealthcareRights / StateWelfare
    status:        str = ""           # มีสิทธิ์ / ไม่มีสิทธิ์ / เข้าไม่ได้
    raw_detail:    str = ""           # ข้อความดิบจากเว็บ (ถ้ามี)


class Agent1Output(BaseModel):
    """ผล Agent 1: สิทธิ์ที่ควรได้จาก RAG + สิทธิ์ที่มีอยู่แล้วจาก scraping"""
    eligible_benefits:  List[BenefitItem]        = Field(default=[], description="สิทธิ์ที่ RAG+AI คิดว่าน่าจะมีคุณสมบัติ")
    scraped_benefits:   List[ScrapedBenefitItem] = Field(default=[], description="สิทธิ์ที่ scraping พบจากเว็บจริง พร้อมสถานะ")
    reasoning:          str                       = Field(default="")


class Agent2Output(BaseModel):
    """ผล Agent 2: แยกเป็นมีแล้ว / แนะนำเพิ่ม / ไม่มีคุณสมบัติ"""
    already_have:     List[ScrapedBenefitItem] = Field(default=[], description="สิทธิ์ที่มีสถานะ 'มีสิทธิ์' จาก scraping")
    recommended_new:  List[BenefitItem]        = Field(default=[], description="สิทธิ์ที่ควรได้แต่ยังไม่มี")
    not_eligible:     List[BenefitItem]        = Field(default=[], description="สิทธิ์ที่ AI วิเคราะห์แล้วว่าไม่มีคุณสมบัติ")
    scrape_note:      str                       = Field(default="", description="หมายเหตุเรื่องการ scraping เช่น เว็บล่ม")


class BenefitValueScore(BaseModel):
    benefit_name:         str
    category:             str   = ""
    eligibility_pct:      float = Field(description="โอกาสได้รับสิทธิ์ % (0-100)")
    eligibility_label:    str   = Field(description="สูงมาก / สูง / ปานกลาง / ต่ำ")
    value_baht:           float = Field(description="มูลค่าโดยประมาณ บาท/เดือน")
    value_label:          str   = Field(description="มูลค่าอ่านง่าย เช่น 600-1,000 บาท/เดือน")
    expected_value_baht:  float = Field(description="EV = eligibility_pct/100 × value_baht")
    expected_value_label: str   = Field(description="EV อ่านง่าย เช่น ~720 บาท/เดือน (90%×800)")
    pros:                 List[str] = Field(default=[])
    cons:                 List[str] = Field(default=[])
    required_documents:   List[str] = Field(default=[])
    recommendation_score: int   = Field(description="1-10 จาก EV เทียบกันในกลุ่ม")


class FinalRecommendationStep(BaseModel):
    benefit_name: str
    steps:        List[str] = Field(default=[])


class FinalSummaryOutput(BaseModel):
    citizen_name:        str
    status:              str
    # ── ส่วนใหม่: สรุปสิทธิ์ที่มีอยู่แล้ว ──
    already_have_summary: List[Dict[str, str]] = Field(
        default=[],
        description="สิทธิ์ที่ประชาชนมีอยู่แล้ว พร้อมสถานะและแหล่งข้อมูล"
    )
    # ── สิทธิ์แนะนำใหม่พร้อม EV ──
    benefit_analysis:    List[BenefitValueScore]       = Field(default=[])
    next_steps:          List[FinalRecommendationStep] = Field(default=[])
    recommended_actions: List[str]                     = Field(default=[])
    summary_text:        str
    decision_note:       str = Field(default="")

# ---------------------------------------------------------------------------
# 4. RAG ENGINE (TF-IDF)
# ---------------------------------------------------------------------------
_tfidf_vectorizer: Optional[TfidfVectorizer] = None
_tfidf_matrix = None
_policy_rag_texts: List[str] = []


def _build_rag_text(p: Dict[str, Any]) -> str:
    return f"{p['benefit_name']} {p['category']} {p['content']}"


def build_policy_index() -> None:
    global _tfidf_vectorizer, _tfidf_matrix, _policy_rag_texts
    logger.info("[RAG] สร้าง TF-IDF index...")
    _policy_rag_texts = [_build_rag_text(p) for p in ALL_POLICIES]
    _tfidf_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2,3), sublinear_tf=True)
    _tfidf_matrix = _tfidf_vectorizer.fit_transform(_policy_rag_texts)
    logger.info(f"[RAG] ✅ {len(ALL_POLICIES)} policies, vocab={len(_tfidf_vectorizer.vocabulary_)}")


def rag_search(query: str, top_k: int=RAG_TOP_K, min_score: float=RAG_MIN_SCORE) -> List[Dict[str, Any]]:
    if _tfidf_vectorizer is None:
        raise RuntimeError("กรุณาเรียก build_policy_index() ก่อน")
    q_vec  = _tfidf_vectorizer.transform([query])
    scores = sk_cosine(q_vec, _tfidf_matrix)[0]
    ranked = np.argsort(scores)[::-1]
    results = []
    for idx in ranked[:top_k]:
        score = float(scores[idx])
        if score < min_score: break
        p = ALL_POLICIES[idx]
        results.append({"benefit_id":p["benefit_id"],"benefit_name":p["benefit_name"],
                         "category":p["category"],"content":p["content"],"rag_score":round(score,4)})
        logger.info(f"[RAG] #{len(results)} {p['benefit_name']} score={score:.3f}")
    return results

# ---------------------------------------------------------------------------
# 5. SCRAPING TOOLS (จากไฟล์ที่ให้มา — import หรือ inline)
# ---------------------------------------------------------------------------
def _run_scraping(citizen_id: str) -> List[ScrapedBenefitItem]:
    """
    รัน Playwright scraping จริง แล้วแปลงเป็น List[ScrapedBenefitItem]
    ถ้า playwright ไม่ได้ติดตั้ง จะ fallback เป็น mock data พร้อมแจ้ง warning
    """
    try:
        from playwright.sync_api import sync_playwright
        return _scrape_with_playwright(citizen_id)
    except ImportError:
        logger.warning("[Scraping] playwright ไม่ได้ติดตั้ง — ใช้ mock data แทน (pip install playwright)")
        return _mock_scraping(citizen_id)
    except Exception as e:
        logger.error(f"[Scraping] เกิดข้อผิดพลาด: {e} — ใช้ mock data แทน")
        return _mock_scraping(citizen_id)


def _safe_goto(page, url: str, max_retries: int=3, initial_delay: float=5) -> bool:
    """เปิดเว็บพร้อม retry/backoff"""
    delay = initial_delay
    for attempt in range(1, max_retries+1):
        try:
            if attempt > 1:
                logger.info(f"[Scraping] Retry {attempt}/{max_retries} รอ {delay}s...")
                time.sleep(delay); delay *= 2
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return True
        except Exception as e:
            logger.warning(f"[Scraping] goto {url} ล้มเหลว attempt={attempt}: {e}")
    return False


def _scrape_welfare(browser, citizen_id: str) -> List[ScrapedBenefitItem]:
    """ตรวจสอบสิทธิ์ e-Social Welfare"""
    logger.info("[Scraping] e-Social Welfare...")
    benefits = ["เบี้ยยังชีพผู้สูงอายุ","เบี้ยความพิการ","เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด","บัตรสวัสดิการแห่งรัฐ"]
    rows: List[ScrapedBenefitItem] = []

    page = browser.new_page(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        viewport={"width":1280,"height":800}
    )
    if _safe_goto(page, "https://govwelfare.cgd.go.th/welfare/check"):
        try:
            page.click("button:has-text('ปิด')", timeout=5000)
            page.fill("input[type='text']", citizen_id)
            page.click("button:has-text('ตรวจสอบ')")
            page.wait_for_timeout(2000)
            result_text = page.locator('.col-md-6.col-md-offset-3.edwell').inner_text()
            logger.info(f"[Scraping] eSocial result: {result_text[:100]}")
            has_right = "ไม่มีสิทธิ" not in result_text
            for b in benefits:
                status = "มีสิทธิ์" if (has_right and b in result_text) else "ไม่มีสิทธิ์"
                rows.append(ScrapedBenefitItem(benefit_name=b, source_system="eSocial",
                                               status=status, raw_detail=result_text[:200]))
        except Exception as e:
            logger.warning(f"[Scraping] eSocial error: {e}")
            for b in benefits:
                rows.append(ScrapedBenefitItem(benefit_name=b, source_system="eSocial", status="เข้าไม่ได้"))
    else:
        for b in benefits:
            rows.append(ScrapedBenefitItem(benefit_name=b, source_system="eSocial", status="เข้าไม่ได้"))
    page.close()
    return rows


def _scrape_med(browser, citizen_id: str) -> List[ScrapedBenefitItem]:
    """ตรวจสอบสิทธิ์รักษาพยาบาล"""
    logger.info("[Scraping] สิทธิ์รักษาพยาบาล...")
    benefits = ["สิทธิหลักประกันสุขภาพแห่งชาติ","สิทธิประกันสังคม","สิทธิรักษาพยาบาลข้าราชการ"]
    rows: List[ScrapedBenefitItem] = []

    page = browser.new_page(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        viewport={"width":1280,"height":800}
    )
    if _safe_goto(page, "https://cs8.chi.or.th/chkauth/e1"):
        try:
            page.fill("input[type='text']", citizen_id)
            page.click("button:has-text('ค้นหา')")
            page.wait_for_timeout(2000)
            result_el   = page.locator("div.fb700").nth(2)
            result_text = result_el.inner_text()
            logger.info(f"[Scraping] MedRight result: {result_text[:100]}")
            has_right = ("ไม่พบเลขบัตรประชาชน" not in result_text) and ("ไม่มีสิทธิ" not in result_text)
            for b in benefits:
                status = "มีสิทธิ์" if (has_right and b in result_text) else "ไม่มีสิทธิ์"
                rows.append(ScrapedBenefitItem(benefit_name=b, source_system="HealthcareRights",
                                               status=status, raw_detail=result_text[:200]))
        except Exception as e:
            logger.warning(f"[Scraping] MedRight error: {e}")
            for b in benefits:
                rows.append(ScrapedBenefitItem(benefit_name=b, source_system="HealthcareRights", status="เข้าไม่ได้"))
    else:
        for b in benefits:
            rows.append(ScrapedBenefitItem(benefit_name=b, source_system="HealthcareRights", status="เข้าไม่ได้"))
    page.close()
    return rows


def _scrape_state_welfare(browser, citizen_id: str) -> List[ScrapedBenefitItem]:
    """ตรวจสอบสวัสดิการแห่งรัฐ 2569"""
    logger.info("[Scraping] สวัสดิการแห่งรัฐ 2569...")
    benefits = ["สถานะผู้มีสิทธิบัตรสวัสดิการแห่งรัฐ 2569","สถานะการลงทะเบียนสวัสดิการแห่งรัฐ 2569"]
    rows: List[ScrapedBenefitItem] = []

    page = browser.new_page(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        viewport={"width":1280,"height":800}
    )
    if _safe_goto(page, "https://welfare2.mof.go.th/"):
        try:
            page.fill("input[type='text']", citizen_id)
            page.click("button:has-text('ตรวจสอบ')")
            page.wait_for_timeout(2000)
            result_text = page.locator('#result-box-3').inner_text()
            logger.info(f"[Scraping] StateWelfare result: {result_text[:100]}")
            no_right = "ท่านไม่ใช่กลุ่มเป้าหมาย" in result_text
            for b in benefits:
                status = "ไม่มีสิทธิ์" if no_right else ("มีสิทธิ์" if b in result_text else "ไม่มีสิทธิ์")
                rows.append(ScrapedBenefitItem(benefit_name=b, source_system="StateWelfare",
                                               status=status, raw_detail=result_text[:200]))
        except Exception as e:
            logger.warning(f"[Scraping] StateWelfare error: {e}")
            for b in benefits:
                rows.append(ScrapedBenefitItem(benefit_name=b, source_system="StateWelfare", status="เข้าไม่ได้"))
    else:
        for b in benefits:
            rows.append(ScrapedBenefitItem(benefit_name=b, source_system="StateWelfare", status="เข้าไม่ได้"))
    page.close()
    return rows


def _scrape_with_playwright(citizen_id: str) -> List[ScrapedBenefitItem]:
    """รัน scraping ทั้ง 3 แหล่งพร้อมกัน"""
    from playwright.sync_api import sync_playwright
    all_rows: List[ScrapedBenefitItem] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        logger.info(f"[Scraping] เริ่ม scraping สำหรับ citizen_id={citizen_id}")
        all_rows += _scrape_welfare(browser, citizen_id)
        all_rows += _scrape_med(browser, citizen_id)
        all_rows += _scrape_state_welfare(browser, citizen_id)
        browser.close()
    logger.info(f"[Scraping] รวม {len(all_rows)} รายการจาก 3 แหล่ง")
    return all_rows


def _mock_scraping(citizen_id: str) -> List[ScrapedBenefitItem]:
    """Mock scraping สำหรับทดสอบเมื่อไม่มี playwright"""
    logger.info("[Scraping] ใช้ mock data (playwright ไม่พร้อม)")
    MOCK_DB = {
        "1234567890123": [
            ScrapedBenefitItem(benefit_name="เบี้ยยังชีพผู้สูงอายุ",   source_system="eSocial",          status="มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="เบี้ยความพิการ",            source_system="eSocial",          status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด", source_system="eSocial", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="บัตรสวัสดิการแห่งรัฐ",     source_system="eSocial",          status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สิทธิหลักประกันสุขภาพแห่งชาติ", source_system="HealthcareRights", status="มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สิทธิประกันสังคม",          source_system="HealthcareRights", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สิทธิรักษาพยาบาลข้าราชการ",source_system="HealthcareRights", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สถานะผู้มีสิทธิบัตรสวัสดิการแห่งรัฐ 2569", source_system="StateWelfare", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สถานะการลงทะเบียนสวัสดิการแห่งรัฐ 2569",   source_system="StateWelfare", status="ไม่มีสิทธิ์"),
        ],
        "9876543210987": [
            ScrapedBenefitItem(benefit_name="เบี้ยยังชีพผู้สูงอายุ",   source_system="eSocial",          status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="เบี้ยความพิการ",            source_system="eSocial",          status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด", source_system="eSocial", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="บัตรสวัสดิการแห่งรัฐ",     source_system="eSocial",          status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สิทธิหลักประกันสุขภาพแห่งชาติ", source_system="HealthcareRights", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สิทธิประกันสังคม",          source_system="HealthcareRights", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สิทธิรักษาพยาบาลข้าราชการ",source_system="HealthcareRights", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สถานะผู้มีสิทธิบัตรสวัสดิการแห่งรัฐ 2569", source_system="StateWelfare", status="ไม่มีสิทธิ์"),
            ScrapedBenefitItem(benefit_name="สถานะการลงทะเบียนสวัสดิการแห่งรัฐ 2569",   source_system="StateWelfare", status="ไม่มีสิทธิ์"),
        ],
    }
    return MOCK_DB.get(citizen_id, [
        ScrapedBenefitItem(benefit_name=p["benefit_name"], source_system="mock", status="ไม่มีสิทธิ์")
        for p in ALL_POLICIES
    ])

# ---------------------------------------------------------------------------
# 6. CORE LLM HELPER
# ---------------------------------------------------------------------------
def call_typhoon_api(system_prompt: str, user_prompt: str, output_model: type,
                     max_retries: int=3, retry_delay: float=2.0) -> Any:
    from pydantic import ValidationError
    last_error: Optional[Exception] = None
    raw_content = ""

    for attempt in range(1, max_retries+1):
        try:
            logger.info(f"  → LLM call attempt {attempt}/{max_retries}")
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                response_format={"type":"json_object"},
                messages=[
                    {"role":"system","content": system_prompt+"\n\nสำคัญ: ตอบเป็น JSON เท่านั้น ห้ามมี Markdown หรือ backtick"},
                    {"role":"user",  "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            choice      = resp.choices[0]
            raw_content = choice.message.content or ""
            if choice.finish_reason == "length":
                raise ValueError(f"Response ถูกตัด (length) {len(raw_content)} chars")
            if not raw_content.strip():
                raise ValueError("Response ว่างเปล่า")
            clean = raw_content.strip()
            if clean.startswith("```"):
                parts = clean.split("```"); clean = parts[1] if len(parts)>1 else clean
                if clean.startswith("json"): clean = clean[4:]
            result = output_model(**json.loads(clean.strip()))
            logger.info(f"  ✅ LLM สำเร็จ attempt={attempt}")
            return result
        except json.JSONDecodeError as e:
            last_error=e; logger.warning(f"  ⚠️ JSON error attempt={attempt}: {e} | raw={raw_content[:200]}")
        except ValidationError as e:
            last_error=e; logger.warning(f"  ⚠️ Validation error attempt={attempt}:")
            for err in e.errors(): logger.warning(f"     {err['loc']} {err['type']}: {err['msg']}")
        except Exception as e:
            last_error=e; logger.warning(f"  ⚠️ {type(e).__name__} attempt={attempt}: {e}")
        if attempt < max_retries:
            logger.info(f"  รอ {retry_delay}s..."); time.sleep(retry_delay)

    raise RuntimeError(f"LLM ล้มเหลว {max_retries} attempts: {type(last_error).__name__}: {last_error}")

# ---------------------------------------------------------------------------
# 7. AGENT 1 — RAG + Scraping
# ---------------------------------------------------------------------------
def run_agent_1_rag_and_scrape(ui_data: Dict[str, Any]) -> Agent1Output:
    logger.info("\n" + "="*60)
    logger.info("🤖 Agent 1: RAG Retrieval + Real Scraping")
    logger.info("="*60)

    citizen_profile = ui_data.get("citizen_profile", {})
    rag_context     = ui_data.get("rag_context", {})
    citizen_id      = citizen_profile.get("personal_information", {}).get("citizen_id", "")

    # ── ส่วนที่ 1: RAG ค้นหาสิทธิ์ที่น่าจะมีคุณสมบัติ ──
    personal  = citizen_profile.get("personal_information",  {})
    economic  = citizen_profile.get("economic_information",  {})
    household = citizen_profile.get("household_information", {})
    groups    = citizen_profile.get("vulnerable_groups", [])
    query_parts = [rag_context.get("summary","")]
    if personal.get("age"):       query_parts.append(f"อายุ {personal['age']} ปี")
    if economic.get("occupation"):query_parts.append(f"อาชีพ {economic['occupation']}")
    if economic.get("monthly_income"): query_parts.append(f"รายได้ {economic['monthly_income']} บาท/เดือน")
    if household.get("living_arrangement"): query_parts.append(household["living_arrangement"])
    query_parts += rag_context.get("keywords", [])
    query_parts += groups
    query = " ".join(filter(None, query_parts))

    retrieved = rag_search(query)
    if not retrieved:
        logger.warning("[Agent1] RAG ไม่พบสิทธิ์ที่ relevant")

    # ── ส่วนที่ 2: Scraping จริง ──
    logger.info(f"[Agent1] เริ่ม scraping citizen_id={citizen_id}")
    scraped = _run_scraping(citizen_id)
    scrape_unavailable = [s.benefit_name for s in scraped if s.status == "เข้าไม่ได้"]
    if scrape_unavailable:
        logger.warning(f"[Agent1] เว็บล่ม/เข้าไม่ได้: {scrape_unavailable}")

    # ── LLM คัดสิทธิ์ที่มีคุณสมบัติจาก RAG ──
    if not retrieved:
        return Agent1Output(eligible_benefits=[], scraped_benefits=scraped,
                            reasoning="ไม่พบสิทธิ์ที่ relevant จาก RAG")

    prompt = f"""
วิเคราะห์ว่าผู้ลงทะเบียนคนนี้มีคุณสมบัติตรงกับสิทธิ์ใดบ้างจากรายการที่ RAG ค้นพบ

ข้อมูลผู้ลงทะเบียน:
{json.dumps(citizen_profile, ensure_ascii=False, indent=2)}

สิทธิ์ที่ RAG ค้นพบ (อ่าน content เพื่อตรวจเกณฑ์):
{json.dumps(retrieved, ensure_ascii=False, indent=2)}

คำสั่ง:
1. เลือกเฉพาะสิทธิ์ที่ผู้ลงทะเบียนมีคุณสมบัติตรงตามเกณฑ์จริงๆ
2. คัดลอก benefit_name และ category จากข้อมูล (ห้ามแต่ง)
3. อธิบายเหตุผลที่เลือก/ตัดออก

ตอบเป็น JSON:
{{
  "eligible_benefits": [
    {{"benefit_name":"ชื่อสิทธิ์","category":"หมวดหมู่","content":"รายละเอียด"}}
  ],
  "scraped_benefits": [],
  "reasoning": "เหตุผล..."
}}
"""
    result = call_typhoon_api(
        system_prompt="คุณคือ AI ผู้เชี่ยวชาญด้านคัดกรองสวัสดิการรัฐ ทำงานด้วยความถูกต้องและแม่นยำ",
        user_prompt=prompt,
        output_model=Agent1Output
    )
    # ใส่ scraped_benefits จากการ scraping จริง (ไม่ใช้จาก LLM)
    result.scraped_benefits = scraped
    return result

# ---------------------------------------------------------------------------
# 8. AGENT 2 — เปรียบเทียบ: มีแล้ว / แนะนำเพิ่ม
# ---------------------------------------------------------------------------
def run_agent_2_gap_analysis(agent1_result: Agent1Output) -> Agent2Output:
    logger.info("\n" + "="*60)
    logger.info("🤖 Agent 2: Gap Analysis (มีแล้ว vs แนะนำเพิ่ม)")
    logger.info("="*60)

    # จัดกลุ่ม scraped ก่อน
    have_set   = {s.benefit_name for s in agent1_result.scraped_benefits if s.status == "มีสิทธิ์"}
    unavailable= {s.benefit_name for s in agent1_result.scraped_benefits if s.status == "เข้าไม่ได้"}
    already_have = [s for s in agent1_result.scraped_benefits if s.status == "มีสิทธิ์"]

    scrape_note = ""
    if unavailable:
        scrape_note = f"เว็บไม่สามารถเข้าถึงได้ชั่วคราว: {', '.join(unavailable)} — ผลอาจไม่ครบถ้วน"

    if not agent1_result.eligible_benefits:
        return Agent2Output(already_have=already_have, recommended_new=[],
                            not_eligible=[], scrape_note=scrape_note)

    prompt = f"""
วิเคราะห์ช่องว่างสวัสดิการ: เปรียบเทียบสิทธิ์ที่ควรได้กับสิทธิ์ที่มีอยู่แล้ว

สิทธิ์ที่ AI คิดว่ามีคุณสมบัติ (จาก RAG):
{json.dumps([b.model_dump() for b in agent1_result.eligible_benefits], ensure_ascii=False, indent=2)}

สิทธิ์ที่มีอยู่แล้ว (จาก scraping จริง — status=มีสิทธิ์):
{json.dumps([s.model_dump() for s in already_have], ensure_ascii=False, indent=2)}

สิทธิ์ที่ scraping ยืนยันว่าไม่มี (status=ไม่มีสิทธิ์):
{json.dumps([s.model_dump() for s in agent1_result.scraped_benefits if s.status == "ไม่มีสิทธิ์"], ensure_ascii=False, indent=2)}

คำสั่ง:
1. recommended_new = สิทธิ์ที่มีคุณสมบัติแต่ยังไม่มีจาก scraping (ควรได้รับแต่ยังไม่ได้)
2. not_eligible = สิทธิ์ที่ AI เคยพิจารณาแต่จริงๆ ไม่มีคุณสมบัติ
3. already_have ให้ส่งเป็น [] เพราะระบบจะใส่ให้เอง

ตอบเป็น JSON:
{{
  "already_have": [],
  "recommended_new": [
    {{"benefit_name":"ชื่อสิทธิ์","category":"หมวดหมู่","content":"รายละเอียด"}}
  ],
  "not_eligible": [
    {{"benefit_name":"ชื่อสิทธิ์","category":"","content":""}}
  ],
  "scrape_note": "{scrape_note}"
}}
"""
    result = call_typhoon_api(
        system_prompt="คุณคือ AI วิเคราะห์ช่องว่างสวัสดิการ เปรียบเทียบสิทธิ์ที่ควรได้กับที่มีอยู่แล้วอย่างแม่นยำ",
        user_prompt=prompt,
        output_model=Agent2Output
    )
    # ใส่ already_have จาก scraping จริง (ไม่ใช้จาก LLM)
    result.already_have  = already_have
    result.scrape_note   = scrape_note
    return result

# ---------------------------------------------------------------------------
# 9. AGENT 3 — สรุป + EV Analysis
# ---------------------------------------------------------------------------
def run_agent_3_summary(ui_data: Dict[str, Any], agent2_result: Agent2Output) -> FinalSummaryOutput:
    logger.info("\n" + "="*60)
    logger.info("🤖 Agent 3: Summary + EV Analysis")
    logger.info("="*60)

    profile   = ui_data.get("citizen_profile",{}).get("personal_information",{})
    economic  = ui_data.get("citizen_profile",{}).get("economic_information",{})
    household = ui_data.get("citizen_profile",{}).get("household_information",{})
    full_name = f"{profile.get('first_name','ไม่ระบุ')} {profile.get('last_name','')}".strip()

    # สร้าง already_have_summary สำหรับแสดงผล
    already_summary = [
        {"benefit_name": s.benefit_name, "source": s.source_system, "status": s.status}
        for s in agent2_result.already_have
    ]

    prompt = f"""
สรุปและวิเคราะห์ความคุ้มค่าสวัสดิการสำหรับ: {full_name}

ข้อมูลเศรษฐกิจ:
- รายได้: {economic.get('monthly_income','ไม่ระบุ')} บาท/เดือน
- รายจ่าย: {economic.get('monthly_expense','ไม่ระบุ')} บาท/เดือน
- อาชีพ: {economic.get('occupation','ไม่ระบุ')}
- สมาชิก: {household.get('household_members','ไม่ระบุ')} คน

━━ สิทธิ์ที่มีอยู่แล้ว (ยืนยันจากระบบราชการ) ━━
{json.dumps(already_summary, ensure_ascii=False, indent=2)}

━━ สิทธิ์ใหม่ที่แนะนำให้ดำเนินการ (ยังไม่มี) ━━
{json.dumps([b.model_dump() for b in agent2_result.recommended_new], ensure_ascii=False, indent=2)}

{f"หมายเหตุ scraping: {agent2_result.scrape_note}" if agent2_result.scrape_note else ""}

คำสั่ง:
1. สรุปภาพรวม: ระบุว่ามีสิทธิ์อะไรแล้ว และยังขาดอะไร
2. วิเคราะห์ EV สำหรับสิทธิ์ใหม่แต่ละรายการ:
   - eligibility_pct: โอกาสได้รับ % (0-100)
   - value_baht: มูลค่า บาท/เดือน (ค่ากลาง)
   - expected_value_baht = eligibility_pct/100 × value_baht
   - expected_value_label: เช่น "~720 บาท/เดือน (90%×800)"
   - eligibility_label: สูงมาก(≥80%) / สูง(60-79%) / ปานกลาง(40-59%) / ต่ำ(<40%)
   - recommendation_score: 1-10 = round(EV/EV_max × 10), ขั้นต่ำ 1
   - pros, cons, required_documents
3. เรียง benefit_analysis จาก EV สูงสุดไปต่ำสุด
4. next_steps: ขั้นตอนสำหรับแต่ละสิทธิ์ใหม่ที่แนะนำ
5. decision_note: คำแนะนำให้ผู้รับบริการตัดสินใจ

ตอบเป็น JSON:
{{
  "citizen_name": "{full_name}",
  "status": "แนะนำสิทธิ์เพิ่มเติม",
  "already_have_summary": {json.dumps(already_summary, ensure_ascii=False)},
  "benefit_analysis": [
    {{
      "benefit_name":"ชื่อ","category":"หมวด",
      "eligibility_pct":90.0,"eligibility_label":"สูงมาก",
      "value_baht":800.0,"value_label":"600-1,000 บาท/เดือน",
      "expected_value_baht":720.0,"expected_value_label":"~720 บาท/เดือน (90%×800)",
      "pros":["ข้อดี"],"cons":["ข้อจำกัด"],"required_documents":["เอกสาร"],
      "recommendation_score":10
    }}
  ],
  "next_steps": [{{"benefit_name":"ชื่อ","steps":["ขั้นตอน 1","ขั้นตอน 2"]}}],
  "recommended_actions": ["สิ่งที่เจ้าหน้าที่ต้องทำ"],
  "summary_text": "บทสรุป...",
  "decision_note": "คำแนะนำ..."
}}
"""

    return call_typhoon_api(
        system_prompt="คุณคือ AI ที่ปรึกษาสวัสดิการ วิเคราะห์ความคุ้มค่าและสรุปผลเป็นภาษาไทยที่เข้าใจง่าย",
        user_prompt=prompt,
        output_model=FinalSummaryOutput
    )

# ---------------------------------------------------------------------------
# 10. MAIN PIPELINE
# ---------------------------------------------------------------------------
def run_pipeline(ui_input_json: Dict[str, Any]) -> Optional[FinalSummaryOutput]:
    citizen_id = (ui_input_json
                  .get("citizen_profile",{})
                  .get("personal_information",{})
                  .get("citizen_id"))
    if not citizen_id:
        raise ValueError("❌ ไม่พบ citizen_id")

    logger.info(f"\n🚀 Pipeline เริ่ม — citizen_id={citizen_id}")
    build_policy_index()

    try:
        # Agent 1: RAG + Scraping
        a1 = run_agent_1_rag_and_scrape(ui_input_json)
        logger.info("\n📋 [Agent 1]:\n" + a1.model_dump_json(indent=2, ensure_ascii=False))

        # Agent 2: Gap Analysis
        a2 = run_agent_2_gap_analysis(a1)
        logger.info("\n📋 [Agent 2]:\n" + a2.model_dump_json(indent=2, ensure_ascii=False))

        # Agent 3: Summary + EV
        final = run_agent_3_summary(ui_input_json, a2)
        logger.info("\n📋 [Agent 3 Final]:\n" + json.dumps(final.model_dump(), indent=2, ensure_ascii=False))
        return final

    except RuntimeError as e:
        logger.error(f"❌ Pipeline ล้มเหลว: {e}"); return None
    except ValueError as e:
        logger.error(f"❌ ข้อมูลไม่ถูกต้อง: {e}"); return None

# ---------------------------------------------------------------------------
# TEST CASES
# ---------------------------------------------------------------------------
CASE_MANEE = {
    "citizen_profile": {
        "personal_information": {"first_name":"มานี","last_name":"รักดี","citizen_id":"9876543210987",
                                  "date_of_birth":"1955-03-22","age":71,"phone_number":"0898765432"},
        "address_information":  {"province":"เชียงใหม่","district":"เมืองเชียงใหม่","subdistrict":"ช้างคลาน","postal_code":"50100","full_address":"99/1 ถนนนิมมาน"},
        "household_information":{"household_members":2,"elderly":2,"children":0,"disabled_persons":1,"living_arrangement":"With Spouse"},
        "economic_information": {"occupation":"ว่างงาน","monthly_income":1500,"monthly_expense":4000,"employment_status":"Unemployed"},
        "vulnerable_groups":    ["Elderly","Disability","Low Income"],
        "case_notes":           "ผู้สูงอายุพิการทางการเคลื่อนไหว ไม่มีสิทธิ์รักษาพยาบาล ไม่เคยลงทะเบียนสวัสดิการใดเลย",
    },
    "structured_data": {"case_type":"welfare_intake","readiness_score":90,"generated_at":"2026-06-18T10:30:00Z","officer_unit":"หน่วยรับเรื่องสวัสดิการ"},
    "rag_context":     {"summary":"ผู้สูงอายุพิการ รายได้น้อย ไม่มีสิทธิ์ใดเลย","keywords":["ผู้สูงอายุ","พิการ","รายได้น้อย","รักษาพยาบาล","บัตรสวัสดิการ"]},
}

CASE_SOMCHAI = {
    "citizen_profile": {
        "personal_information": {"first_name":"สมชาย","last_name":"ใจดี","citizen_id":"1234567890123",
                                  "date_of_birth":"1958-10-09","age":68,"phone_number":"0812345678"},
        "address_information":  {"province":"กรุงเทพมหานคร","district":"จตุจักร","subdistrict":"ลาดยาว","postal_code":"10900","full_address":"123/4 หมู่บ้านสุขใจ"},
        "household_information":{"household_members":1,"elderly":1,"children":0,"disabled_persons":0,"living_arrangement":"Living Alone"},
        "economic_information": {"occupation":"ว่างงาน","monthly_income":2000,"monthly_expense":3500,"employment_status":"Unemployed"},
        "vulnerable_groups":    ["Elderly","Low Income"],
        "case_notes":           "ต้องการความช่วยเหลือเรื่องค่าครองชีพ",
    },
    "structured_data": {"case_type":"welfare_intake","readiness_score":80,"generated_at":"2026-06-18T10:30:00Z","officer_unit":"หน่วยรับเรื่องสวัสดิการ"},
    "rag_context":     {"summary":"ผู้สูงอายุอยู่ลำพัง รายได้ไม่เพียงพอ","keywords":["ผู้สูงอายุ","อยู่ลำพัง","รายได้น้อย"]},
}

if __name__ == "__main__":
    ACTIVE_CASE = CASE_SOMCHAI   # เปลี่ยนเป็น CASE_SOMCHAI เพื่อทดสอบ overlap
    result = run_pipeline(ACTIVE_CASE)

    if result:
        print("\n" + "="*60)
        print("✅ ผลลัพธ์สุดท้าย")
        print("="*60)

        if result.already_have_summary:
            print(f"\n📌 สิทธิ์ที่มีอยู่แล้ว ({len(result.already_have_summary)} รายการ):")
            for s in result.already_have_summary:
                print(f"   ✓ {s['benefit_name']} ({s['source']}) — {s['status']}")

        if result.benefit_analysis:
            print(f"\n📊 สิทธิ์ที่แนะนำใหม่ — EV Ranking:")
            print(f"   {'สิทธิ์':<35} {'โอกาส':>7}  {'มูลค่า':>9}  {'EV':>12}  {'คะแนน':>6}")
            print("   " + "-"*75)
            for b in result.benefit_analysis:
                print(f"   {b.benefit_name:<35} {b.eligibility_pct:>5.0f}%  {b.value_baht:>7.0f}฿  {b.expected_value_baht:>10.1f}฿  {b.recommendation_score:>5}/10")
            print()
            for b in result.benefit_analysis:
                print(f"  ── {b.benefit_name} [{b.eligibility_label}] คะแนน {b.recommendation_score}/10")
                print(f"     EV: {b.expected_value_label}")
                print(f"     ✓ {' / '.join(b.pros)}")
                if b.cons: print(f"     ⚠ {' / '.join(b.cons)}")
                if b.required_documents: print(f"     📄 {', '.join(b.required_documents)}")

        if result.next_steps:
            print(f"\n🗂 ขั้นตอนการดำเนินการ:")
            for ns in result.next_steps:
                print(f"\n  📌 {ns.benefit_name}")
                for i,s in enumerate(ns.steps,1): print(f"     {i}. {s}")

        print(f"\n📝 {result.summary_text}")
        print(f"\n💡 {result.decision_note}")
    else:
        print("\n❌ Pipeline ไม่สำเร็จ")