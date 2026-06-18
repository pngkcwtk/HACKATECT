# 🏛️ Welfare Gap Finder

ระบบ AI ผู้ช่วยเจ้าหน้าที่สังคมสงเคราะห์ สำหรับวิเคราะห์ **"ช่องว่างสวัสดิการ"** ของประชาชนแต่ละคน — ค้นหาว่าใครควรได้รับสิทธิ์อะไรเพิ่ม โดยใช้ Multi-Agent Pipeline ร่วมกับ RAG (Retrieval-Augmented Generation) และ Typhoon LLM

โปรเจกต์นี้พัฒนาขึ้นในงาน Hackathon (HACKATECT) เพื่อแก้ปัญหาประชาชนที่ "ตกหล่น" จากสวัสดิการที่ตนเองมีสิทธิ์ได้รับ แต่ไม่รู้ตัว หรือเจ้าหน้าที่ไม่มีเวลาตรวจสอบสิทธิ์ซ้ำซ้อนทีละราย

---

## ✨ ภาพรวมระบบ

ผู้ใช้ (เจ้าหน้าที่) กรอกข้อมูลประชาชนผ่านหน้าเว็บ → ระบบส่งข้อมูลไปยัง Backend → รัน Multi-Agent Pipeline 3 ขั้นตอน → คืนผลวิเคราะห์สวัสดิการที่แนะนำ พร้อมขั้นตอนการขอสิทธิ์ กลับมาแสดงผลที่หน้าเว็บ

```
┌─────────────┐      ┌──────────────────┐      ┌────────────────────────────┐
│   Frontend   │ ───▶ │  FastAPI Backend  │ ───▶ │   Multi-Agent Pipeline      │
│ (HTML/CSS/JS)│ ◀─── │     (main.py)     │ ◀─── │ (welfare_agent_pipeline.py) │
└─────────────┘      └──────────────────┘      └────────────────────────────┘
                                                          │
                                  ┌───────────────────────┼───────────────────────┐
                                  ▼                       ▼                       ▼
                          Agent 1: RAG          Agent 2: ตรวจสอบสิทธิ์      Agent 3: สรุปผล +
                       (จับคู่สวัสดิการ            ซ้ำซ้อนกับฐานข้อมูล         วิเคราะห์ความคุ้มค่า
                        ที่เกี่ยวข้อง)              สิทธิ์ที่มีอยู่             (Expected Value)
```

### Multi-Agent Pipeline

| Agent | หน้าที่ |
|---|---|
| **Agent 1 — RAG Retrieval** | ค้นหาสวัสดิการที่เกี่ยวข้องกับโปรไฟล์ประชาชน จากฐานข้อมูลสวัสดิการ (TF-IDF + Cosine Similarity) |
| **Agent 2 — DB Verification** | ตรวจสอบว่าประชาชนมีสิทธิ์ใดอยู่แล้ว เพื่อกรองรายการที่ซ้ำซ้อนออก |
| **Agent 3 — Summary & Value Analysis** | วิเคราะห์ความคุ้มค่า (ข้อดี/ข้อจำกัด/เอกสารที่ต้องใช้) และสรุปขั้นตอนการขอสิทธิ์แต่ละรายการ |

Pipeline ขับเคลื่อนด้วย **Typhoon LLM** (`typhoon-v2.5-30b-a3b-instruct`) ผ่าน [OpenTyphoon API](https://opentyphoon.ai/)

---

## 📂 โครงสร้างโปรเจกต์

```
HACKATECT/
├── main.py                      # FastAPI backend entry point
├── welfare_agent_pipeline.py    # Multi-Agent Pipeline หลัก (RAG + LLM agents)
├── example.env                  # ตัวอย่างไฟล์ environment variable
├── data/
│   ├── welfare_documents.csv        # ฐานข้อมูลสวัสดิการ (ใช้ทำ RAG)
│   └── benefit_source_mapping.csv   # mapping สิทธิ์ ↔ ระบบ/หน่วยงานต้นทาง
├── frontend/
│   ├── index.html               # หน้าเว็บฟอร์มกรอกข้อมูลประชาชน
│   ├── css/styles.css
│   └── js/
│       ├── app.js                # ฟอร์ม + เรียก API + แสดงผลวิเคราะห์
│       └── thai-address-data.js  # ข้อมูลจังหวัด/อำเภอ/ตำบลของไทย
└── Backend_backup/               # ไฟล์เวอร์ชันก่อนหน้า / เก็บสำรอง
```

---

## 🚀 วิธีติดตั้งและรัน

### 1. Clone และติดตั้ง dependencies

```bash
git clone -b tiya https://github.com/pngkcwtk/Welfare-Gap-Finder.git
cd Welfare-Gap-Finder
pip install fastapi uvicorn pydantic openai python-dotenv numpy scikit-learn
```

### 2. ตั้งค่า Environment Variable

คัดลอก `example.env` เป็น `.env` แล้วใส่ Typhoon API Key ของคุณ:

```bash
cp example.env .env
```

```env
TYPHOON_API_KEY="your_typhoon_api_key_here"
```

> สามารถขอ API Key ได้ที่ [opentyphoon.ai](https://opentyphoon.ai/)

### 3. รัน Backend

```bash
uvicorn main:app --reload --port 8000
```

เมื่อรันสำเร็จ ตรวจสอบได้ที่ `http://localhost:8000` ควรเห็นข้อความ `"status": "ok"`

### 4. เปิด Frontend

เปิดไฟล์ `frontend/index.html` ผ่าน Live Server หรือ local HTTP server (เช่น VS Code Live Server extension) — **ไม่แนะนำให้เปิดไฟล์ตรงๆแบบ `file://`** เพราะอาจมีปัญหา CORS

---

## 🔌 API Endpoint

### `POST /api/analyze`

วิเคราะห์ข้อมูลประชาชนและคืนคำแนะนำสวัสดิการ

**Request Body:**
```json
{
  "citizen_profile": { "...": "ข้อมูลส่วนตัว/ที่อยู่ของประชาชน" },
  "structured_data": { "...": "ข้อมูลโครงสร้าง เช่น รายได้ อาชีพ" },
  "rag_context": { "...": "บริบทเพิ่มเติมสำหรับค้นหาสวัสดิการ" }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "benefit_analysis": [ "...รายการสวัสดิการที่แนะนำ พร้อมคะแนนความคุ้มค่า..." ],
    "next_steps": [ "...ขั้นตอนการขอสิทธิ์แต่ละรายการ..." ],
    "recommended_actions": [ "...สิ่งที่เจ้าหน้าที่ควรทำต่อ..." ],
    "summary_text": "บทสรุปสำหรับเจ้าหน้าที่",
    "decision_note": "เหตุผลในการจัดลำดับความสำคัญของสิทธิ์"
  }
}
```

### `GET /`

Health check — ตรวจสอบว่า server พร้อมใช้งาน

---

## 🛠️ เทคโนโลยีที่ใช้

- **Backend:** FastAPI, Pydantic, Uvicorn
- **AI / LLM:** Typhoon (`typhoon-v2.5-30b-a3b-instruct`) ผ่าน OpenAI-compatible client
- **RAG:** TF-IDF Vectorization + Cosine Similarity (scikit-learn)
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Data:** CSV-based ฐานข้อมูลสวัสดิการ

---

## 🧪 การทดสอบ

ในไฟล์ `welfare_agent_pipeline.py` มี mock test case ตัวอย่าง (เช่น กรณี "สมชาย" ผู้สูงอายุที่มีเบี้ยยังชีพอยู่แล้ว) สามารถรันไฟล์ตรงๆ เพื่อทดสอบ pipeline แบบ standalone โดยไม่ต้องผ่าน frontend ได้:

```bash
python welfare_agent_pipeline.py
```

> 💡 Tip: เปิด Browser DevTools (กด `F12` → แท็บ Console) ขณะใช้งานหน้าเว็บ เพื่อดู payload JSON ที่ส่งไปยัง backend ผ่าน `console.log`

---

## 📄 License

โปรเจกต์นี้อยู่ภายใต้ [MIT License](LICENSE)
