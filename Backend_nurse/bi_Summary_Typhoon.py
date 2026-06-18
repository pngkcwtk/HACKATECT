from openai import OpenAI

client = OpenAI(
    api_key="sk-v6lYt8MFfKrqtCaTDbwAR3AjEDjZQQjM90uOZ2gMAjtdkdeh",
    base_url="https://api.opentyphoon.ai/v1"
)

# รับ Input จากผู้ใช้
user_input = input("ใส่ข้อความของคุณที่นี่: ")

# ==========================================
# AGENT 1: The Technical Analyst (วิเคราะห์และสรุป) แต่ว่าถ้้า
# ==========================================
print("\n--- Agent 1 กำลังวิเคราะห์และสรุปข้อมูล... ---\n")

agent1_system = """You are a professional analyst and technical writer.
Analyze the provided content and create a structured summary.
Focus on clarity, readability, and actionable insights. Use Markdown."""

messages_agent1 = [
    {"role": "system", "content": agent1_system},
    {"role": "user", "content": f"input text here: {user_input}"}
]

response_agent1 = client.chat.completions.create(
    model="typhoon-v2.5-30b-a3b-instruct",
    messages=messages_agent1,
    temperature=0.4, # ลด temp ลงเล็กน้อยเพื่อความแม่นยำในด่านแรก
    max_completion_tokens=1024,
    top_p=0.6,
    stream=False # เปลี่ยนเป็น False ก่อนเพื่อเก็บค่าไปส่งต่อ
)

summary_result = response_agent1.choices[0].message.content
print(summary_result) # แสดงผลลัพธ์ของ Agent 1 (เลือกเปิดดูหรือไม่ก็ได้)


# ==========================================
# AGENT 2: The Critical Reviewer & Editor (ตรวจทานและขัดเกลา)
# ==========================================
print("\n--- Agent 2 กำลังตรวจทานและขัดเกลาผลลัพธ์... ---\n")

agent2_system = """You are an expert editor and business consultant. 
Review the provided summary. Your job is to:
1. Improve the tone to be highly professional and engaging.
2. Ensure that 'Action Items' and 'Risks' are extremely sharp and realistic.
3. Fix any logical gaps or confusing language.
Output the final, polished version directly."""

messages_agent2 = [
    {"role": "system", "content": agent2_system},
    # ส่งผลลัพธ์ของ Agent 1 ให้ Agent 2 ตรวจสอบ
    {"role": "user", "content": f"Please review and polish this summary:\n\n{summary_result}"}
]

# ใช้ streaming สำหรับ Agent ตัวสุดท้ายเพื่อให้ผู้ใช้เห็นข้อความค่อยๆ ขึ้น
stream_agent2 = client.chat.completions.create(
    model="typhoon-v2.5-30b-a3b-instruct",
    messages=messages_agent2,
    temperature=0.6,
    max_completion_tokens=1024,
    top_p=0.6,
    stream=True
)

# แสดงผลลัพธ์สุดท้ายจาก Agent 2
for chunk in stream_agent2:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()