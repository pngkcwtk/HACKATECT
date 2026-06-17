# from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright



def scrape_welfare(citizen_id: str):
    print(f"🤖 Agent สั่งงาน: กำลังเริ่มขูดข้อมูลสำหรับเลขบัตร {citizen_id}...")
    
    with sync_playwright() as p:
        # 1. เปิดเบราว์เซอร์จำลอง (คืนนี้ตั้ง headless=False ก่อนเพื่อให้เห็นหน้าจอวิ่งจริง)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 2. วาร์ปไปยังหน้าเว็บ e-Social Welfare ตรงจุดตรวจสอบสิทธิ์
        page.goto("https://govwelfare.cgd.go.th/welfare/check")

        page.click("button:has-text('ปิด')")

        # 3. สั่งให้บอทเอาเลขบัตรประชาชนที่ Agent ส่งมา ไปพิมพ์ลงในช่องกรอก
        page.fill("input[type='text']", citizen_id)
        
        # 4. สั่งให้บอทกดปุ่ม "ตรวจสอบ"
        page.click("button:has-text('ตรวจสอบ')")
        
        # 5. รอให้หน้าเว็บโหลดผลลัพธ์สักครู่
        page.wait_for_timeout(2000)
        
        # 6. ดึงข้อความหรือตารางที่เด้งขึ้นมา
        result_locator = page.locator('.col-md-6.col-md-offset-3.edwell')
        result_text = result_locator.inner_text()
        
        print("🎉 บอททำงานเสร็จแล้ว! กำลังส่งข้อมูลกลับไปให้ Agent...")
        browser.close()

        print()
        print(result_text)
        print()

        return result_text



# --- ส่วนนี้เอาไว้ให้คุณกดรันเพื่อทดสอบบนเครื่องตัวเอง (Local Test) ---
if __name__ == "__main__":
    # จำลองเลขบัตรมั่ว ๆ เพื่อดูว่าบอทเปิดหน้าจอและพิมพ์ให้จริงไหม
    mock_citizen_id = "1210101147372" # 
    scrape_welfare(mock_citizen_id)
