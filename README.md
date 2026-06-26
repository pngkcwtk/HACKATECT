# Welfare Gap Finder

ระบบผู้ช่วยเจ้าหน้าที่สังคมสงเคราะห์สำหรับค้นหา "ช่องว่างสวัสดิการ" ของประชาชนแต่ละราย โดยรับข้อมูลจากหน้าเว็บ ส่งไปยัง FastAPI backend แล้วให้ Multi-Agent Pipeline วิเคราะห์สิทธิ์ที่เกี่ยวข้อง สิทธิ์ที่อาจซ้ำซ้อน และขั้นตอนแนะนำถัดไป

โปรเจกต์นี้พัฒนาสำหรับงาน HACKATECT เพื่อช่วยลดภาระการตรวจสอบสวัสดิการหลายรายการด้วยมือ และช่วยให้เจ้าหน้าที่เห็นภาพรวมของเคสได้เร็วขึ้น

## ภาพรวมระบบ

```text
Frontend (HTML/CSS/JS)
        |
        v
FastAPI Backend (main.py)
        |
        v
Multi-Agent Pipeline (Backend_backup/welfare_agent_pipeline.py)
        |
        +-- Agent 1: RAG Retrieval / Policy Matching
        +-- Agent 2: ตรวจสอบสิทธิ์ซ้ำซ้อน
        +-- Agent 3: สรุปผลและวิเคราะห์ความคุ้มค่า
```

Pipeline ใช้ Typhoon LLM ผ่าน OpenAI-compatible client และใช้ข้อมูลสวัสดิการจากไฟล์ CSV ในโฟลเดอร์ `data/`

## ความสามารถหลัก

- บันทึกข้อมูลประชาชนผ่านหน้าเว็บสำหรับเจ้าหน้าที่
- แสดง dashboard และรายการเคสตัวอย่าง
- วิเคราะห์สิทธิ์สวัสดิการจากข้อมูลส่วนบุคคล ครัวเรือน รายได้ และกลุ่มเปราะบาง
- ค้นหาสวัสดิการที่เกี่ยวข้องด้วย TF-IDF และ Cosine Similarity
- สรุปผลเป็นภาษาไทย พร้อมเหตุผลและขั้นตอนดำเนินการต่อ

## โครงสร้างโปรเจกต์

```text
HACKATECT/
├── main.py                         # FastAPI backend entry point
├── welfare_agent_pipeline.py       # pipeline เวอร์ชันหลักอีกชุดหนึ่ง
├── requirements.txt                # Python dependencies
├── example.env                     # ตัวอย่างไฟล์ environment variables
├── data/
│   ├── welfare_documents.csv       # ฐานข้อมูลสวัสดิการสำหรับ RAG
│   └── benefit_source_mapping.csv  # mapping สิทธิ์กับแหล่งข้อมูล/หน่วยงาน
├── frontend/
│   ├── index.html                  # หน้าเว็บหลัก
│   ├── css/styles.css              # stylesheet
│   └── js/
│       ├── app.js                  # frontend logic และ API call
│       └── thai-address-data.js    # ข้อมูลที่อยู่ไทย
└── Backend_backup/
    └── welfare_agent_pipeline.py   # pipeline ที่ main.py ใช้งานอยู่
```

> หมายเหตุ: `main.py` ปัจจุบัน import pipeline จาก `Backend_backup/welfare_agent_pipeline.py`

## การติดตั้ง

### 1. สร้าง virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. ติดตั้ง dependencies

```powershell
pip install -r requirements.txt
```

### 3. ตั้งค่า API key

คัดลอกไฟล์ตัวอย่างเป็น `.env`

```powershell
Copy-Item example.env .env
```

จากนั้นแก้ค่าใน `.env`

```env
TYPHOON_API_KEY="your_typhoon_api_key_here"
```

สามารถขอ API key ได้จาก [OpenTyphoon](https://opentyphoon.ai/)

## วิธีรัน

### รัน backend

```powershell
uvicorn main:app --reload --port 8000
```

ตรวจสอบ health check ได้ที่:

```text
http://localhost:8000/
```

ถ้าระบบพร้อมใช้งานจะได้ response ลักษณะนี้:

```json
{
  "status": "ok",
  "message": "Welfare Gap Finder API พร้อมใช้งาน"
}
```

### เปิด frontend

เปิดไฟล์ `frontend/index.html` ผ่าน local web server เช่น VS Code Live Server หรือรัน server แบบง่ายจากโฟลเดอร์ `frontend`

```powershell
cd frontend
python -m http.server 5500
```

จากนั้นเปิด:

```text
http://localhost:5500/
```

Frontend จะเรียก backend ที่ `http://localhost:8000` ตามค่าที่ตั้งไว้ใน `frontend/js/app.js`

## API

### `GET /`

ใช้ตรวจสอบว่า backend พร้อมทำงานหรือไม่

### `POST /api/analyze`

รับข้อมูลเคสจาก frontend แล้วส่งเข้า Multi-Agent Pipeline

ตัวอย่าง request body:

```json
{
  "citizen_profile": {
    "personal_information": {
      "first_name": "สมชาย",
      "last_name": "ประเสริฐ"
    }
  },
  "structured_data": {
    "monthly_income": 2000,
    "household_members": 1,
    "vulnerable_groups": ["Elderly", "Low Income"]
  },
  "rag_context": {
    "notes": "ผู้สูงอายุอยู่ลำพัง รายได้ต่ำ"
  }
}
```

ตัวอย่าง response:

```json
{
  "success": true,
  "data": {
    "citizen_name": "สมชาย ประเสริฐ",
    "status": "แนะนำสิทธิ์เพิ่มเติม",
    "benefit_analysis": [],
    "next_steps": [],
    "recommended_actions": []
  },
  "error": null
}
```

## การทดสอบแบบ standalone

สามารถรัน pipeline โดยตรงได้ด้วยคำสั่ง:

```powershell
python welfare_agent_pipeline.py
```

หรือทดสอบ backend ผ่าน Swagger UI หลังจากรัน `uvicorn` แล้ว:

```text
http://localhost:8000/docs
```

## เทคโนโลยีที่ใช้

- Backend: FastAPI, Uvicorn, Pydantic
- AI/LLM: Typhoon ผ่าน OpenAI-compatible API
- RAG: scikit-learn, TF-IDF, Cosine Similarity
- Data: CSV
- Frontend: HTML, CSS, Vanilla JavaScript, Tailwind CDN

## License

โปรเจกต์นี้เผยแพร่ภายใต้ [MIT License](LICENSE)
