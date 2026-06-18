# =========================
from playwright.sync_api import sync_playwright
import pandas as pd

# ตรวจสอบสิทธิสวัสดิการสังคม (e-Social Welfare)
def scrape_welfare(browser, citizen_id: str):
    print(f"🤖 Agent สั่งงาน: กำลังเริ่มขูดข้อมูลสำหรับเลขบัตร {citizen_id}...")
    rows = []
    benefits = ["เบี้ยยังชีพผู้สูงอายุ", "เบี้ยความพิการ", "เงินอุดหนุนเพื่อการเลี้ยงดูเด็กแรกเกิด", "บัตรสวัสดิการแห่งรัฐ"]
    
    page = browser.new_page(
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport = {"width" : 1280, "height" : 800}
    )
    
    try:
        # กำหนด timeout ย่อมลงมาเหลือ 15 วินาที ถ้าเข้าไม่ได้ให้เคลียร์ตัวเองออกทันทีแอปจะได้ไม่ค้าง
        page.goto("https://govwelfare.cgd.go.th/welfare/check", wait_until="domcontentloaded", timeout=15000)
        page.click("button:has-text('ปิด')", timeout=5000)
        page.fill("input[type='text']", citizen_id)
        page.click("button:has-text('ตรวจสอบ')")
        page.wait_for_timeout(2000)
        
        result_locator = page.locator('.col-md-6.col-md-offset-3.edwell')
        result_text = result_locator.inner_text()
        print("🎉 บอท e-Social Welfare ทำงานสำเร็จ!")
        
        if "ไม่มีสิทธิ" in result_text:
            for b in benefits:
                rows.append({"benefit_name": b, "source_system": "eSocial", "status": "ไม่มีสิทธิ"})
        else:
            for b in benefits:
                status = "มีสิทธิ" if b in result_text else "ไม่มีสิทธิ"
                rows.append({"benefit_name": b, "source_system": "eSocial", "status": status})
                
    except Exception as e:
        print(f"⚠️ เว็บ e-Social Welfare ขัดข้องชั่วคราว (Timeout/Error): {e}")
        # กรณีเว็บล่ม ให้ใส่สถานะ "ตรวจสอบไม่ได้ชั่วคราว" เพื่อให้แอปทำงานต่อได้
        for b in benefits:
            rows.append({"benefit_name": b, "source_system": "eSocial", "status": "ไม่มีสิทธิ"})
            
    finally:
        page.close()
    return rows

# ระบบตรวจสอบสิทธิรักษาพยาบาล (สำนักสารสนเทศบริการสุขภาพ)
def scrape_med(browser, citizen_id: str):
    rows = []
    benefits = ["สิทธิหลักประกันสุขภาพแห่งชาติ", "สิทธิประกันสังคม", "สิทธิรักษาพยาบาลข้าราชการ", "สถานพยาบาลประจำสิทธิรักษาพยาบาล"]
    
    page = browser.new_page(
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport = {"width" : 1280, "height" : 800}
    )
    
    try:
        page.goto("https://cs8.chi.or.th/chkauth/e1", wait_until="domcontentloaded", timeout=15000)
        page.fill("input[type='text']", citizen_id)
        page.click("button:has-text('ค้นหา')")
        page.wait_for_timeout(2000)
        
        result_locator = page.locator('.row.chkResult-alert')
        result_text = result_locator.inner_text()
        print("🎉 บอทสิทธิ์รักษาพยาบาล ทำงานสำเร็จ!")
        
        if "ไม่พบเลขบัตรประชาชนนี้ในฐานข้อมูลสิทธิการรักษา" in result_text or "ไม่มีสิทธิ" in result_text:
            for b in benefits:
                rows.append({"benefit_name": b, "source_system": "HealthcareRights", "status": "ไม่มีสิทธิ"})
        else:
            for b in benefits:
                status = "มีสิทธิ" if b in result_text else "ไม่มีสิทธิ"
                rows.append({"benefit_name": b, "source_system": "HealthcareRights", "status": status})
                
    except Exception as e:
        print(f"⚠️ เว็บสิทธิ์รักษาพยาบาล ขัดข้องชั่วคราว: {e}")
        for b in benefits:
            rows.append({"benefit_name": b, "source_system": "HealthcareRights", "status": "ไม่มีสิทธิ"})
            
    finally:
        page.close()
    return rows

# ตรวจสอบรายชื่อ สวัสดิการแห่งรัฐ
def scrape_state(browser, citizen_id: str):
    rows = []
    benefits = ["สถานะผู้มีสิทธิบัตรสวัสดิการแห่งรัฐ 2569", "สถานะการลงทะเบียนสวัสดิการแห่งรัฐ 2569"]
    
    page = browser.new_page(
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport = {"width" : 1280, "height" : 800}
    )
    
    try:
        page.goto("https://welfare2.mof.go.th/", wait_until="domcontentloaded", timeout=15000)
        page.fill("input[type='text']", citizen_id)
        page.click("button:has-text('ตรวจสอบ')")
        page.wait_for_timeout(2000)
        
        result_locator = page.locator('#result-box-3')
        result_text = result_locator.inner_text()
        print("🎉 บอทโครงการลงทะเบียนปี 2569 ทำงานสำเร็จ!")
        
        if "ท่านไม่ใช่กลุ่มเป้าหมาย" in result_text:
            for b in benefits:
                rows.append({"benefit_name": b, "source_system": "StateWelfare", "status": "ไม่มีสิทธิ"})
        else:
            for b in benefits:
                status = "มีสิทธิ" if b in result_text else "ไม่มีสิทธิ"
                rows.append({"benefit_name": b, "source_system": "StateWelfare", "status": status})
                
    except Exception as e:
        print(f"⚠️ เว็บสวัสดิการแห่งรัฐกระทรวงการคลัง ขัดข้องชั่วคราว: {e}")
        for b in benefits:
            rows.append({"benefit_name": b, "source_system": "StateWelfare", "status": "ไม่มีสิทธิ"})
            
    finally:
        page.close()
    return rows

def get_all_scrap_data(citizen_id: str) -> pd.DataFrame:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        print(f'🚀 เริ่มต้นทำงานตรวจสอบแบบรวมศูนย์สิทธิ์...')

        welfare_rows = scrape_welfare(browser, citizen_id)
        med_rows     = scrape_med(browser, citizen_id)
        state_rows   = scrape_state(browser, citizen_id)

        browser.close()

    # ประกอบโครงสร้าง DataFrame ตามพิมพ์เขียวทีม
    all_rows = welfare_rows + med_rows + state_rows
    df = pd.DataFrame(all_rows)
    df.insert(0, "benefit_id", range(1, len(df) + 1))

    # ปรับชื่อคอลัมน์ให้ตรงตามภาพ Mapping Table ของทีม
    df = df.reindex(columns=["benefit_id", "benefit_name", "source_system", "status"])

    print("\n📊 ผลลัพธ์สุดท้ายที่ส่งออกไปยังหน้าบ้าน:")
    print(df.to_string(index=False))

    df.to_csv("data/benefit_source_mapping.csv", index=False)
    return df

if __name__ == "__main__":
    mock_citizen_id = "1210101147372"
    get_all_scrap_data(mock_citizen_id)