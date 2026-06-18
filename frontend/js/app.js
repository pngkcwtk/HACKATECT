window.tailwind = window.tailwind || {};

// URL ของ FastAPI backend — เปลี่ยนเป็น domain จริงตอน deploy
const API_BASE_URL = 'http://localhost:8000';

// ตั้งค่า theme เพิ่มเติมให้ Tailwind CDN ใช้สีและเงาตามดีไซน์ของระบบ
tailwind.config = {
      theme: {
        extend: {
          colors: {
            mso: {
              primary: '#1E3A5F',
              secondary: '#3B82F6',
              bg: '#F8FAFC',
              success: '#22C55E',
              warning: '#F59E0B',
              danger: '#DC2626'
            }
          },
          boxShadow: {
            soft: '0 14px 35px rgba(30, 58, 95, 0.08)'
          }
        }
      }
    };

// เริ่มทำงานหลัง DOM พร้อมใช้งาน และล้างข้อมูล demo เก่าจากเวอร์ชันก่อน
document.addEventListener('DOMContentLoaded', () => {
      clearLegacyLocalData();
  
      // ตัวเลขตัวอย่างบน dashboard
      const baseStats = {
        totalCases: 1248,
        newCases: 36,
        pendingCases: 89,
        completedCases: 1123
      };

      // ชื่อขั้นตอนใน wizard ด้านซ้าย
      const steps = [
        'ข้อมูลส่วนบุคคล',
        'ข้อมูลที่อยู่',
        'ข้อมูลครัวเรือน',
        'ข้อมูลเศรษฐกิจ',
        'กลุ่มเปราะบาง',
        'บันทึกเจ้าหน้าที่',
        'ตรวจสอบข้อมูลก่อนส่ง'
      ];

      // ข้อมูลตัวอย่างสำหรับตารางเคสล่าสุด
      const recentCases = [
        {
          name: 'สมชาย ประเสริฐ',
          age: 68,
          province: 'เชียงใหม่',
          district: 'เมืองเชียงใหม่',
          subdistrict: 'ศรีภูมิ',
          postalCode: '50200',
          status: 'รอตรวจสอบ',
          updated: '17 มิ.ย. 2569',
          occupation: 'ผู้สูงอายุไม่ได้ประกอบอาชีพ',
          monthlyIncome: 2000,
          monthlyExpense: 3500,
          householdMembers: 1,
          elderlyCount: 1,
          childrenCount: 0,
          disabledCount: 0,
          livingArrangement: 'Living Alone',
          employmentStatus: 'Unemployed',
          vulnerableGroups: ['Elderly', 'Low Income'],
          gapSummary: 'ควรตรวจสอบว่ามีผู้ดูแลประจำหรือได้รับเบี้ยยังชีพครบถ้วนหรือไม่',
          followUps: ['มีผู้ดูแลหลักหรือไม่', 'ได้รับเบี้ยยังชีพผู้สูงอายุแล้วหรือไม่', 'มีรายจ่ายรักษาพยาบาลประจำหรือไม่']
        },
        {
          name: 'มาลี ศรีสุข',
          age: 44,
          province: 'ขอนแก่น',
          district: 'เมืองขอนแก่น',
          subdistrict: 'ศิลา',
          postalCode: '40000',
          status: 'พร้อมดำเนินการ',
          updated: '16 มิ.ย. 2569',
          occupation: 'รับจ้างทั่วไป',
          monthlyIncome: 6500,
          monthlyExpense: 7200,
          householdMembers: 4,
          elderlyCount: 1,
          childrenCount: 2,
          disabledCount: 0,
          livingArrangement: 'Family',
          employmentStatus: 'Employed',
          vulnerableGroups: ['Low Income'],
          gapSummary: 'รายจ่ายสูงกว่ารายได้ ควรประเมินภาระเด็กและผู้สูงอายุในครัวเรือน',
          followUps: ['มีเด็กอยู่ในวัยเรียนกี่คน', 'มีหนี้สินเร่งด่วนหรือไม่', 'ได้รับสวัสดิการเด็กหรือผู้สูงอายุครบหรือไม่']
        },
        {
          name: 'อนันต์ วงศ์ชัย',
          age: 72,
          province: 'กรุงเทพมหานคร',
          district: 'ดินแดง',
          subdistrict: 'ดินแดง',
          postalCode: '10400',
          status: 'เสร็จสิ้น',
          updated: '15 มิ.ย. 2569',
          occupation: 'ผู้สูงอายุไม่ได้ประกอบอาชีพ',
          monthlyIncome: 3000,
          monthlyExpense: 2800,
          householdMembers: 2,
          elderlyCount: 1,
          childrenCount: 0,
          disabledCount: 1,
          livingArrangement: 'Relatives',
          employmentStatus: 'Unemployed',
          vulnerableGroups: ['Elderly', 'Disabled'],
          gapSummary: 'มีผู้พิการในครัวเรือน ควรตรวจสอบทะเบียนผู้พิการและอุปกรณ์ช่วยเหลือ',
          followUps: ['ขึ้นทะเบียนผู้พิการแล้วหรือยัง', 'ต้องการอุปกรณ์ช่วยเหลือหรือไม่', 'มีผู้ดูแลในเวลากลางวันหรือไม่']
        },
        {
          name: 'ศิริพร แก้วใส',
          age: 31,
          province: 'นครราชสีมา',
          district: 'เมืองนครราชสีมา',
          subdistrict: 'ในเมือง',
          postalCode: '30000',
          status: 'ร่าง',
          updated: '14 มิ.ย. 2569',
          occupation: 'ค้าขาย',
          monthlyIncome: 5000,
          monthlyExpense: 6500,
          householdMembers: 3,
          elderlyCount: 0,
          childrenCount: 1,
          disabledCount: 0,
          livingArrangement: 'Family',
          employmentStatus: 'Employed',
          vulnerableGroups: ['Low Income'],
          gapSummary: 'ข้อมูลยังไม่ครบ ควรสอบถามภาระเลี้ยงดูเด็กและความมั่นคงของรายได้',
          followUps: ['มีรายได้สม่ำเสมอหรือไม่', 'เด็กได้รับเงินอุดหนุนหรือไม่', 'มีค่าเช่าหรือผ่อนที่อยู่อาศัยหรือไม่']
        }
      ];

      // ชุดข้อมูล dropdown แบบ cascade โหลดจาก thai-address-data.js เพื่อให้มีจังหวัด/อำเภอ/ตำบลครบทั้งประเทศ
      const addressCatalog = window.thaiAddressCatalog || {};

      // ตัวเลือกอาชีพที่ใช้บ่อย เพื่อช่วยลดเวลาพิมพ์ของเจ้าหน้าที่
      const occupations = [
        'ว่างงาน',
        'รับจ้างทั่วไป',
        'เกษตรกร',
        'ค้าขาย',
        'พนักงานบริษัท',
        'ข้าราชการ/รัฐวิสาหกิจ',
        'ผู้สูงอายุไม่ได้ประกอบอาชีพ',
        'นักเรียน/นักศึกษา',
        'อื่น ๆ'
      ];
  
      let currentStep = 1;
      let selectedRecentCaseIndex = 0;
      let isCaseInsightOpen = true;
      const form = document.getElementById('caseForm');
  
      // ล้าง localStorage เก่าที่เคยใช้ในเวอร์ชัน demo ก่อนหน้า เพื่อไม่ให้มีข้อมูลค้างในเครื่อง
      function clearLegacyLocalData() {
        try {
          localStorage.removeItem('msoWelfareCopilotDraft');
          localStorage.removeItem('msoWelfareCopilotSubmittedCases');
        } catch (error) {
          console.warn('ไม่สามารถล้างข้อมูล demo เดิมได้:', error);
        }
      }
  
      // สลับหน้าใน SPA โดยไม่ reload หน้าเว็บ
      function showPage(pageId) {
        document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
        document.getElementById(pageId).classList.add('active');
        document.querySelectorAll('.nav-link').forEach(link => {
          link.classList.toggle('nav-active', link.dataset.page === pageId);
        });
        closeMobileMenu();
        if (pageId === 'newCasePage') updateReview();
        if (pageId === 'dashboardPage') renderDashboard();
      }
  
      // คืนค่า class สี badge ตามสถานะเคสในตาราง
      function getStatusTone(status) {
        if (status === 'เสร็จสิ้น') return 'bg-green-50 text-green-700';
        if (status === 'พร้อมดำเนินการ') return 'bg-blue-50 text-blue-700';
        if (status === 'ร่าง') return 'bg-slate-100 text-slate-600';
        return 'bg-amber-50 text-amber-700';
      }
  
      // แสดงตัวเลขสถิติตัวอย่างบน dashboard
      function renderDashboardStats() {
        document.getElementById('totalCasesStat').textContent = baseStats.totalCases.toLocaleString();
        document.getElementById('newCasesStat').textContent = baseStats.newCases.toLocaleString();
        document.getElementById('pendingCasesStat').textContent = baseStats.pendingCases.toLocaleString();
        document.getElementById('completedCasesStat').textContent = baseStats.completedCases.toLocaleString();
      }
  
      // สร้างแถวตารางเคสล่าสุดจาก mock data
      function renderRecentCases() {
        document.getElementById('recentCasesBody').innerHTML = recentCases.map((row, index) => {
          const tone = getStatusTone(row.status);
          const active = index === selectedRecentCaseIndex ? 'case-row-active' : '';
          return `<tr class="case-row cursor-pointer transition hover:bg-blue-50 ${active}" data-case-index="${index}"><td class="px-5 py-4 font-bold text-slate-800">${row.name}</td><td class="px-5 py-4">${row.age}</td><td class="px-5 py-4">${row.province}</td><td class="px-5 py-4"><span class="rounded-full px-3 py-1 text-xs font-bold ${tone}">${row.status}</span></td><td class="px-5 py-4 text-slate-500">${row.updated}</td></tr>`;
        }).join('');
        bindRecentCaseRows();
        renderCaseInsight();
      }
  
      // render dashboard ทั้งส่วนสถิติและตารางเคสล่าสุด
      function renderDashboard() {
        renderDashboardStats();
        renderRecentCases();
      }

      // ผูก click ให้แต่ละแถวในตาราง เพื่อเลือกเคสและแสดงรายละเอียดด้านล่าง
      function bindRecentCaseRows() {
        document.querySelectorAll('[data-case-index]').forEach(row => {
          row.addEventListener('click', () => {
            selectedRecentCaseIndex = Number(row.dataset.caseIndex);
            isCaseInsightOpen = true;
            renderRecentCases();
          });
        });
      }

      // อัปเดตปุ่มและการแสดงผลของแผงรายละเอียดเคสล่าสุด ให้ผู้ใช้เปิด/ปิดพื้นที่ตัวอย่างได้
      function updateCaseInsightVisibility() {
        const panel = document.getElementById('caseInsightPanel');
        const toggleButton = document.getElementById('toggleCaseInsightBtn');
        panel.classList.toggle('hidden', !isCaseInsightOpen);
        toggleButton.textContent = isCaseInsightOpen ? 'ซ่อนรายละเอียด' : 'แสดงรายละเอียด';
        toggleButton.setAttribute('aria-expanded', String(isCaseInsightOpen));
      }

      // แสดง panel รายละเอียดของเคสล่าสุดที่เลือก พร้อมประเด็นที่ควรถามเพิ่ม
      function renderCaseInsight() {
        const caseItem = recentCases[selectedRecentCaseIndex];
        const panel = document.getElementById('caseInsightPanel');
        const followUps = caseItem.followUps.map(item => `<li class="flex gap-2"><span class="text-mso-secondary">•</span><span>${item}</span></li>`).join('');
        panel.innerHTML = `
          <div class="grid gap-5 lg:grid-cols-[1fr_320px]">
            <div>
              <p class="text-sm font-bold text-mso-secondary">รายละเอียดเคสที่เลือก</p>
              <h4 class="mt-1 text-lg font-black text-mso-primary">${caseItem.name}</h4>
              <p class="mt-3 leading-7 text-slate-700">${caseItem.gapSummary}</p>
              <ul class="mt-4 space-y-2 text-sm text-slate-700">${followUps}</ul>
            </div>
            <div class="rounded-lg border border-slate-200 bg-white p-4">
              <p class="text-sm font-black text-mso-primary">ข้อมูลย่อ</p>
              <dl class="mt-3 space-y-2 text-sm">
                <div class="flex justify-between gap-3"><dt class="text-slate-500">รายได้</dt><dd class="font-bold">${caseItem.monthlyIncome.toLocaleString()} บาท</dd></div>
                <div class="flex justify-between gap-3"><dt class="text-slate-500">รายจ่าย</dt><dd class="font-bold">${caseItem.monthlyExpense.toLocaleString()} บาท</dd></div>
                <div class="flex justify-between gap-3"><dt class="text-slate-500">สมาชิก</dt><dd class="font-bold">${caseItem.householdMembers} คน</dd></div>
              </dl>
              <button type="button" id="useCaseTemplateBtn" class="mt-4 w-full rounded-lg bg-mso-primary px-4 py-3 text-sm font-bold text-white shadow-soft">ใช้เป็นตัวอย่างกรอกฟอร์ม</button>
            </div>
          </div>
        `;
        document.getElementById('useCaseTemplateBtn').addEventListener('click', () => useRecentCaseAsTemplate(caseItem));
        updateCaseInsightVisibility();
      }

      // นำข้อมูลจากเคสล่าสุดที่เลือกมาเป็นตัวอย่างในฟอร์ม เพื่อให้เจ้าหน้าที่กรอกต่อได้เร็วขึ้น
      function useRecentCaseAsTemplate(caseItem) {
        const [firstName = '', ...lastNameParts] = caseItem.name.split(' ');
        form.reset();
        populateStaticDropdowns();

        form.elements.firstName.value = firstName;
        form.elements.lastName.value = lastNameParts.join(' ');
        form.elements.age.value = caseItem.age;
        form.elements.province.value = caseItem.province;
        populateDistrictOptions(caseItem.district);
        populateSubdistrictOptions(caseItem.subdistrict);
        updatePostalCode();

        form.elements.householdMembers.value = caseItem.householdMembers;
        form.elements.elderlyCount.value = caseItem.elderlyCount;
        form.elements.childrenCount.value = caseItem.childrenCount;
        form.elements.disabledCount.value = caseItem.disabledCount;
        form.elements.occupation.value = caseItem.occupation;
        form.elements.monthlyIncome.value = caseItem.monthlyIncome;
        form.elements.monthlyExpense.value = caseItem.monthlyExpense;
        form.elements.caseNotes.value = caseItem.gapSummary;

        setCheckedValue('livingArrangement', caseItem.livingArrangement);
        setCheckedValue('employmentStatus', caseItem.employmentStatus);
        setCheckedValues('vulnerableGroups', caseItem.vulnerableGroups);

        clearErrors();
        currentStep = 1;
        updateWizard();
        showPage('newCasePage');
      }

      // เลือก radio จากค่า value ที่ส่งมา ใช้กับข้อมูลตัวอย่างและฟอร์มจริง
      function setCheckedValue(name, value) {
        const field = form.querySelector(`input[name="${name}"][value="${value}"]`);
        if (field) field.checked = true;
      }

      // เลือก checkbox หลายค่า ใช้เติมกลุ่มเปราะบางจากเคสตัวอย่าง
      function setCheckedValues(name, values) {
        form.querySelectorAll(`input[name="${name}"]`).forEach(field => {
          field.checked = values.includes(field.value);
        });
      }
  
      // เติม option ให้ select element พร้อม placeholder
      function setSelectOptions(select, options, placeholder) {
        select.innerHTML = [`<option value="">${placeholder}</option>`, ...options.map(option => `<option value="${option}">${option}</option>`)].join('');
      }
  
      // เติม dropdown เริ่มต้น เช่น จังหวัด อาชีพ และเคลียร์อำเภอ/ตำบล
      function populateStaticDropdowns() {
        setSelectOptions(form.elements.province, Object.keys(addressCatalog), 'เลือกจังหวัด');
        setSelectOptions(form.elements.district, [], 'เลือกอำเภอ/เขต');
        setSelectOptions(form.elements.subdistrict, [], 'เลือกตำบล/แขวง');
        setSelectOptions(form.elements.occupation, occupations, 'เลือกอาชีพ');
      }
  
      // เติมอำเภอ/เขตตามจังหวัดที่เลือก และรีเซ็ต dropdown ตำบล
      function populateDistrictOptions(selectedDistrict = '') {
        const province = form.elements.province.value;
        const districts = province ? Object.keys(addressCatalog[province] || {}) : [];
        setSelectOptions(form.elements.district, districts, 'เลือกอำเภอ/เขต');
        if (selectedDistrict && districts.includes(selectedDistrict)) form.elements.district.value = selectedDistrict;
        populateSubdistrictOptions();
      }
  
      // เติมตำบล/แขวงตามจังหวัดและอำเภอที่เลือก
      function populateSubdistrictOptions(selectedSubdistrict = '') {
        const province = form.elements.province.value;
        const district = form.elements.district.value;
        const subdistricts = province && district ? Object.keys(addressCatalog[province]?.[district] || {}) : [];
        setSelectOptions(form.elements.subdistrict, subdistricts, 'เลือกตำบล/แขวง');
        if (selectedSubdistrict && subdistricts.includes(selectedSubdistrict)) form.elements.subdistrict.value = selectedSubdistrict;
        updatePostalCode();
      }
  
      // เติมรหัสไปรษณีย์อัตโนมัติจากจังหวัด/อำเภอ/ตำบล
      function updatePostalCode() {
        const province = form.elements.province.value;
        const district = form.elements.district.value;
        const subdistrict = form.elements.subdistrict.value;
        const postalCode = addressCatalog[province]?.[district]?.[subdistrict] || '';
        form.elements.postalCode.value = postalCode;
      }
  
      // แสดงรายการขั้นตอน wizard พร้อม highlight ขั้นตอนปัจจุบัน
      function renderStepList() {
        document.getElementById('stepList').innerHTML = steps.map((step, index) => {
          const number = index + 1;
          const state = number === currentStep ? 'bg-mso-primary text-white' : number < currentStep ? 'bg-mso-success text-white' : 'bg-slate-100 text-slate-500';
          return `<li class="flex items-center gap-3"><span class="grid h-7 w-7 place-items-center rounded-full text-xs font-black ${state}">${number}</span><span class="${number === currentStep ? 'font-black text-mso-primary' : 'font-bold text-slate-600'}">${step}</span></li>`;
        }).join('');
      }
  
      // อัปเดต step ปัจจุบัน, progress bar, ปุ่ม navigation และหน้า review
      function updateWizard() {
        document.querySelectorAll('.wizard-step').forEach(step => step.classList.toggle('active', Number(step.dataset.step) === currentStep));
        document.getElementById('progressBar').style.width = `${(currentStep / steps.length) * 100}%`;
        document.getElementById('stepIndicator').textContent = `ขั้นตอนที่ ${currentStep} จาก ${steps.length}`;
        document.getElementById('prevBtn').disabled = currentStep === 1;
        document.getElementById('prevBtn').classList.toggle('opacity-50', currentStep === 1);
        document.getElementById('nextBtn').classList.toggle('hidden', currentStep === steps.length);
        document.getElementById('sendBtn').classList.toggle('hidden', currentStep !== steps.length);
        renderStepList();
        if (currentStep === steps.length) updateReview();
      }
  
      // ล้างข้อความ error และ state สีแดงก่อน validate ใหม่
      function clearErrors() {
        form.querySelectorAll('.field-error').forEach(error => error.remove());
        form.querySelectorAll('.border-mso-danger').forEach(input => input.classList.remove('border-mso-danger'));
      }
  
      // ตรวจ required fields เฉพาะ step ปัจจุบันก่อนให้ไปขั้นตอนถัดไป
      function validateStep(stepNumber) {
        clearErrors();
        const step = form.querySelector(`[data-step="${stepNumber}"]`);
        const requiredFields = Array.from(step.querySelectorAll('[required]'));
        let valid = true;
        requiredFields.forEach(field => {
          if (field.type === 'radio') {
            const checked = form.querySelector(`input[name="${field.name}"]:checked`);
            if (!checked && !step.querySelector(`[data-radio-error="${field.name}"]`)) {
              const wrapper = field.closest('div');
              const message = document.createElement('p');
              message.className = 'field-error';
              message.dataset.radioError = field.name;
              message.textContent = 'กรุณาเลือกหนึ่งตัวเลือก';
              wrapper.after(message);
              valid = false;
            }
            return;
          }
          if (!field.value.trim()) {
            field.classList.add('border-mso-danger');
            const message = document.createElement('p');
            message.className = 'field-error';
            message.textContent = 'กรุณากรอกข้อมูลช่องนี้';
            field.after(message);
            valid = false;
          }
        });
        return valid;
      }
  
      // รวมค่าจากฟอร์มทั้งหมดเป็น object เดียว รวม checkbox กลุ่มเปราะบางด้วย
      function collectFormData() {
        const data = Object.fromEntries(new FormData(form).entries());
        data.vulnerableGroups = Array.from(form.querySelectorAll('input[name="vulnerableGroups"]:checked')).map(item => item.value);
        return data;
      }
  
      // คำนวณอายุจากวันเกิด โดยปรับตามเดือน/วันที่จริง
      function calculateAge(dateValue) {
        if (!dateValue) return '';
        const birth = new Date(dateValue);
        const today = new Date();
        let age = today.getFullYear() - birth.getFullYear();
        const monthDiff = today.getMonth() - birth.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) age--;
        return age >= 0 ? age : '';
      }
  
      // สร้างประเด็นสำคัญของเคสจากอายุ รายได้ ลักษณะการอยู่อาศัย และกลุ่มเปราะบาง
      function generateKeywords(data) {
        const keywords = new Set();
        const age = Number(data.age || 0);
        const income = Number(data.monthlyIncome || 0);
        const groupKeywordMap = {
          Elderly: 'ผู้สูงอายุ',
          Disabled: 'ผู้พิการ',
          Bedridden: 'ผู้ป่วยติดเตียง',
          Newborn: 'เด็กแรกเกิด',
          'Low Income': 'รายได้น้อย',
          Unemployed: 'ว่างงาน'
        };
        if (age >= 60) keywords.add('ผู้สูงอายุ');
        if (data.livingArrangement === 'Living Alone') keywords.add('อยู่ลำพัง');
        if (income > 0 && income <= 3000) keywords.add('รายได้น้อย');
        if (data.employmentStatus === 'Unemployed') keywords.add('ว่างงาน');
        data.vulnerableGroups.forEach(group => keywords.add(groupKeywordMap[group] || group));
        return Array.from(keywords);
      }
  
      // สร้างสรุปเคสเบื้องต้นจากข้อมูลที่กรอก เพื่อให้เจ้าหน้าที่ตรวจทานก่อนส่ง
      function generateSummary(data, keywords) {
        const arrangementMap = {
          'Living Alone': 'อยู่ลำพัง',
          Family: 'อยู่กับครอบครัว',
          Relatives: 'อยู่กับญาติ',
          Other: 'ลักษณะอื่น ๆ'
        };
        const name = [data.firstName, data.lastName].filter(Boolean).join(' ') || 'ประชาชนรายนี้';
        const age = data.age ? `อายุ ${data.age} ปี` : 'ยังไม่ได้ระบุอายุ';
        const arrangement = data.livingArrangement ? `ลักษณะการอยู่อาศัย: ${arrangementMap[data.livingArrangement] || data.livingArrangement}` : 'ยังไม่ได้ระบุลักษณะการอยู่อาศัย';
        const income = data.monthlyIncome ? `รายได้ต่อเดือนประมาณ ${Number(data.monthlyIncome).toLocaleString()} บาท` : 'ยังไม่ได้ระบุรายได้ต่อเดือน';
        const expense = data.monthlyExpense ? `รายจ่ายต่อเดือนประมาณ ${Number(data.monthlyExpense).toLocaleString()} บาท` : 'ยังไม่ได้ระบุรายจ่ายต่อเดือน';
        const vulnerability = keywords.length ? `สัญญาณความเปราะบางที่พบ ได้แก่ ${keywords.join(', ')}` : 'ยังไม่พบคีย์เวิร์ดกลุ่มเปราะบาง';
        const notes = data.caseNotes || 'ยังไม่มีบันทึกเพิ่มเติมจากเจ้าหน้าที่';
        return `${name} ${age}. ${arrangement}. ${income} และ${expense}. ${vulnerability}. บันทึกเจ้าหน้าที่: ${notes}`;
      }
  
      // รวมข้อมูลฟอร์มเป็น payload สำหรับส่งต่อระบบภายใน โดยไม่แสดงรายละเอียดเชิงเทคนิคบน UI
      function buildPayload() {
        const data = collectFormData();
        const keywords = generateKeywords(data);
        const summary = generateSummary(data, keywords);
        const citizenProfile = {
          personal_information: {
            first_name: data.firstName || '',
            last_name: data.lastName || '',
            citizen_id: data.citizenId || '',
            date_of_birth: data.dateOfBirth || '',
            age: Number(data.age || 0),
            phone_number: data.phone || ''
          },
          address_information: {
            province: data.province || '',
            district: data.district || '',
            subdistrict: data.subdistrict || '',
            postal_code: data.postalCode || '',
            full_address: data.fullAddress || ''
          },
          household_information: {
            household_members: Number(data.householdMembers || 0),
            elderly: Number(data.elderlyCount || 0),
            children: Number(data.childrenCount || 0),
            disabled_persons: Number(data.disabledCount || 0),
            living_arrangement: data.livingArrangement || ''
          },
          economic_information: {
            occupation: data.occupation || '',
            monthly_income: Number(data.monthlyIncome || 0),
            monthly_expense: Number(data.monthlyExpense || 0),
            employment_status: data.employmentStatus || ''
          },
          vulnerable_groups: data.vulnerableGroups,
          case_notes: data.caseNotes || ''
        };
        return {
          citizen_profile: citizenProfile,
          structured_data: {
            case_type: 'welfare_intake',
            readiness_score: calculateReadinessScore(data),
            generated_at: new Date().toISOString(),
            officer_unit: 'หน่วยรับเรื่องสวัสดิการ'
          },
          rag_context: { summary, keywords }
        };
      }
  
      // ตรวจว่าชุด field ที่กำหนดมีค่าครบทุกช่องหรือไม่
      function sectionComplete(names, data) {
        return names.every(name => {
          const value = data[name];
          return Array.isArray(value) ? value.length > 0 : Boolean(String(value || '').trim());
        });
      }
  
      // คำนวณคะแนนความครบถ้วนของข้อมูลจากแต่ละหมวดหลัก
      function calculateReadinessScore(data) {
        let score = 0;
        if (sectionComplete(['firstName', 'lastName', 'citizenId', 'age', 'phone'], data)) score += 20;
        if (sectionComplete(['province', 'district', 'subdistrict', 'postalCode'], data)) score += 20;
        if (sectionComplete(['householdMembers', 'elderlyCount', 'childrenCount', 'disabledCount', 'livingArrangement'], data)) score += 20;
        if (sectionComplete(['occupation', 'monthlyIncome', 'monthlyExpense', 'employmentStatus'], data)) score += 20;
        if ((data.caseNotes || '').trim().length >= 40) score += 20;
        else if ((data.caseNotes || '').trim().length > 0) score += 10;
        return score;
      }
  
      // อัปเดตหน้าตรวจสอบก่อนส่ง เช่น ความครบถ้วน คะแนน คำแนะนำ ประเด็นสำคัญ และสรุปเคส
      function updateReview() {
        const data = collectFormData();
        const payload = buildPayload();
        const checks = [
          ['ข้อมูลส่วนบุคคล', sectionComplete(['firstName', 'lastName', 'citizenId', 'age', 'phone'], data) ? 'ครบถ้วน' : 'ข้อมูลไม่ครบ'],
          ['ข้อมูลที่อยู่', sectionComplete(['province', 'district', 'subdistrict', 'postalCode'], data) ? 'ครบถ้วน' : 'ข้อมูลไม่ครบ'],
          ['ข้อมูลครัวเรือน', sectionComplete(['householdMembers', 'elderlyCount', 'childrenCount', 'disabledCount', 'livingArrangement'], data) ? 'ครบถ้วน' : 'ข้อมูลไม่ครบ'],
          ['ข้อมูลเศรษฐกิจ', sectionComplete(['occupation', 'monthlyIncome', 'monthlyExpense', 'employmentStatus'], data) ? 'ครบถ้วน' : 'ข้อมูลไม่ครบ'],
          ['บันทึกเจ้าหน้าที่', (data.caseNotes || '').trim().length >= 40 ? 'ครบถ้วน' : 'สั้นเกินไป']
        ];
        document.getElementById('completenessList').innerHTML = checks.map(([label, status]) => {
          const good = status === 'ครบถ้วน';
          return `<div class="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2"><span class="font-bold">${label}</span><span class="font-black ${good ? 'text-mso-success' : 'text-mso-warning'}">${good ? '✓' : '⚠'} ${status}</span></div>`;
        }).join('');
        const score = payload.structured_data.readiness_score;
        document.getElementById('readinessScore').textContent = `${score} / 100`;
        document.getElementById('readinessStatus').textContent = score >= 80 ? 'พร้อมส่งข้อมูล' : score >= 55 ? 'ควรตรวจสอบเพิ่มเติม' : 'ข้อมูลยังไม่ครบถ้วน';
        document.getElementById('keywordTags').innerHTML = payload.rag_context.keywords.length ? payload.rag_context.keywords.map(keyword => `<span class="tag">${keyword}</span>`).join('') : '<span class="text-sm text-slate-500">คีย์เวิร์ดจะแสดงหลังกรอกอายุ รายได้ ลักษณะการอยู่อาศัย หรือกลุ่มเปราะบาง</span>';
        document.getElementById('caseSummary').textContent = payload.rag_context.summary;
      }
  
      // เปิดให้ HTML inline onclick เรียกเปลี่ยนหน้าได้
      window.showPage = showPage;
      
      // ส่งข้อมูลไป FastAPI backend และแสดงผลลัพธ์ Multi-Agent Pipeline
      async function submitCase(payload) {
        // แสดง loading state บนปุ่มส่ง
        const sendBtn = document.getElementById('sendBtn');
        const originalText = sendBtn.textContent;
        sendBtn.disabled = true;
        sendBtn.textContent = '⏳ กำลังวิเคราะห์สิทธิ์...';

        try {
          const response = await fetch(`${API_BASE_URL}/api/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });

          if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Server error ${response.status}`);
          }

          const result = await response.json();

          if (!result.success || !result.data) {
            throw new Error('ได้รับข้อมูลไม่ครบถ้วนจากเซิร์ฟเวอร์');
          }

          // รีเซ็ตฟอร์มแล้วแสดงผลลัพธ์
          form.reset();
          populateStaticDropdowns();
          currentStep = 1;
          updateWizard();
          showResultModal(result.data);

        } catch (error) {
          console.error('submitCase error:', error);
          showErrorModal(error.message);
        } finally {
          sendBtn.disabled = false;
          sendBtn.textContent = originalText;
        }
      }

      // เผื่อระบบภายนอกหรือ console ต้องเรียกส่งข้อมูลซ้ำระหว่าง demo
      window.submitCase = submitCase;

      // ── แสดง modal ผลลัพธ์ Pipeline ──
      function showResultModal(data) {
        const modal = document.getElementById('resultModal');

        // Header
        document.getElementById('resultName').textContent = data.citizen_name || '';
        document.getElementById('resultStatus').textContent = data.status || '';

        // Benefit analysis cards
        const analysisContainer = document.getElementById('resultBenefitAnalysis');
        if (data.benefit_analysis && data.benefit_analysis.length > 0) {
          // เรียงจาก recommendation_score สูงสุด
          const sorted = [...data.benefit_analysis].sort((a, b) => b.recommendation_score - a.recommendation_score);
          analysisContainer.innerHTML = sorted.map((b, i) => {
            const scoreColor = b.recommendation_score >= 8 ? 'text-green-600' : b.recommendation_score >= 5 ? 'text-amber-600' : 'text-slate-500';
            const chanceBadge = b.eligibility_label === 'สูงมาก' ? 'bg-green-50 text-green-700' :
                                b.eligibility_label === 'สูง'    ? 'bg-blue-50 text-blue-700' :
                                b.eligibility_label === 'ปานกลาง'? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600';
            const pros  = (b.pros  || []).map(p => `<li class="flex gap-2"><span class="text-green-500 shrink-0">✓</span>${p}</li>`).join('');
            const cons  = (b.cons  || []).map(c => `<li class="flex gap-2"><span class="text-amber-500 shrink-0">⚠</span>${c}</li>`).join('');
            const docs  = (b.required_documents || []).map(d => `<span class="rounded bg-slate-100 px-2 py-0.5 text-xs">${d}</span>`).join('');
            return `
              <div class="rounded-lg border border-slate-200 bg-white p-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="font-black text-mso-primary">${i + 1}. ${b.benefit_name}</p>
                    <span class="mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-bold ${chanceBadge}">${b.eligibility_label} (${b.eligibility_pct}%)</span>
                  </div>
                  <div class="text-right shrink-0">
                    <p class="text-2xl font-black ${scoreColor}">${b.recommendation_score}<span class="text-sm font-bold text-slate-400">/10</span></p>
                    <p class="text-xs text-slate-500">คะแนนแนะนำ</p>
                  </div>
                </div>
                <div class="mt-3 rounded-lg bg-blue-50 px-3 py-2">
                  <p class="text-xs font-bold text-mso-secondary">Expected Value</p>
                  <p class="mt-0.5 font-black text-mso-primary">${b.expected_value_label}</p>
                  <p class="text-xs text-slate-500">${b.value_label}</p>
                </div>
                ${pros ? `<ul class="mt-3 space-y-1 text-sm text-slate-700">${pros}</ul>` : ''}
                ${cons ? `<ul class="mt-2 space-y-1 text-sm text-slate-700">${cons}</ul>` : ''}
                ${docs ? `<div class="mt-3 flex flex-wrap gap-1">${docs}</div>` : ''}
              </div>`;
          }).join('');
        } else {
          analysisContainer.innerHTML = '<p class="text-sm text-slate-500">ไม่พบสิทธิ์ใหม่ที่แนะนำ</p>';
        }

        // Next steps
        const stepsContainer = document.getElementById('resultNextSteps');
        if (data.next_steps && data.next_steps.length > 0) {
          stepsContainer.innerHTML = data.next_steps.map(ns => `
            <div class="rounded-lg border border-slate-200 bg-white p-4">
              <p class="font-black text-mso-primary">📌 ${ns.benefit_name}</p>
              <ol class="mt-3 space-y-2 text-sm text-slate-700 list-none">
                ${(ns.steps || []).map((s, i) => `
                  <li class="flex gap-3">
                    <span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-mso-primary text-xs font-black text-white">${i + 1}</span>
                    <span class="pt-0.5">${s}</span>
                  </li>`).join('')}
              </ol>
            </div>`).join('');
        } else {
          stepsContainer.innerHTML = '<p class="text-sm text-slate-500">ไม่มีขั้นตอนเพิ่มเติม</p>';
        }

        // Decision note + summary
        document.getElementById('resultDecisionNote').textContent = data.decision_note || '';
        document.getElementById('resultSummaryText').textContent  = data.summary_text  || '';

        modal.classList.remove('hidden');
        modal.classList.add('flex');
      }

      // ── แสดง error modal ──
      function showErrorModal(message) {
        const modal = document.getElementById('errorModal');
        document.getElementById('errorMessage').textContent = message || 'เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ';
        modal.classList.remove('hidden');
        modal.classList.add('flex');
      }
      
      // ปิด sidebar บนมือถือและ overlay
      function closeMobileMenu() {
        document.getElementById('sidebar').classList.add('-translate-x-full');
        document.getElementById('mobileOverlay').classList.add('hidden');
      }
  
      // ผูก event ของเมนู sidebar เพื่อสลับหน้า
      document.querySelectorAll('.nav-link').forEach(link => link.addEventListener('click', () => showPage(link.dataset.page)));
      
      // เปิดเมนูบนมือถือ
      document.getElementById('menuButton').addEventListener('click', () => {
        document.getElementById('sidebar').classList.remove('-translate-x-full');
        document.getElementById('mobileOverlay').classList.remove('hidden');
      });

      // กดพื้นหลังมืดเพื่อปิดเมนูบนมือถือ
      document.getElementById('mobileOverlay').addEventListener('click', closeMobileMenu);

      // ปุ่มย้อนกลับใน wizard
      document.getElementById('prevBtn').addEventListener('click', () => { if (currentStep > 1) { currentStep--; updateWizard(); } });

      // ปุ่มถัดไปใน wizard: validate ก่อนค่อยไป step ถัดไป
      document.getElementById('nextBtn').addEventListener('click', () => {
        if (currentStep < steps.length && validateStep(currentStep)) {
          currentStep++;
          updateWizard();
        }
      });

      // ปุ่มส่งข้อมูลในขั้นตอนสุดท้าย
      document.getElementById('sendBtn').addEventListener('click', () => {
        updateReview();
        submitCase(buildPayload());
      });

      // ปุ่มปิด modal ผลลัพธ์ (result modal)
      function closeResultModal() {
        document.getElementById('resultModal').classList.add('hidden');
        document.getElementById('resultModal').classList.remove('flex');
      }
      function closeErrorModal() {
        document.getElementById('errorModal').classList.add('hidden');
        document.getElementById('errorModal').classList.remove('flex');
      }
      window.closeResultModal = closeResultModal;
      window.closeErrorModal  = closeErrorModal;

      document.getElementById('closeResultModal').addEventListener('click', closeResultModal);
      document.getElementById('finishResultBtn').addEventListener('click', () => { closeResultModal(); showPage('dashboardPage'); });
      document.getElementById('closeErrorModal').addEventListener('click', closeErrorModal);

      // ปุ่มเปิด/ปิดแผงรายละเอียดเคสล่าสุด เพื่อลดสิ่งรบกวนบน dashboard
      document.getElementById('toggleCaseInsightBtn').addEventListener('click', () => {
        isCaseInsightOpen = !isCaseInsightOpen;
        updateCaseInsightVisibility();
      });

      // เมื่อเลือกจังหวัด ให้เติมอำเภอ/เขตที่สัมพันธ์กัน
      form.elements.province.addEventListener('change', () => {
        populateDistrictOptions();
      });

      // เมื่อเลือกอำเภอ/เขต ให้เติมตำบล/แขวงที่สัมพันธ์กัน
      form.elements.district.addEventListener('change', () => {
        populateSubdistrictOptions();
      });

      // เมื่อเลือกตำบล/แขวง ให้เติมรหัสไปรษณีย์อัตโนมัติ
      form.elements.subdistrict.addEventListener('change', () => {
        updatePostalCode();
      });

      // อัปเดตอายุจากวันเกิด และ refresh review ถ้าอยู่ขั้นตอนตรวจสอบ
      form.addEventListener('input', event => {
        if (event.target.name === 'dateOfBirth') form.elements.age.value = calculateAge(event.target.value);
        if (currentStep === steps.length) updateReview();
      });
      
      // ถ้ามีการเปลี่ยนค่าในฟอร์มขณะอยู่หน้า review ให้คำนวณผลใหม่ทันที
      form.addEventListener('change', () => {
        if (currentStep === steps.length) updateReview();
      });
  
      // เริ่มต้นหน้า: เติม dropdown, render dashboard และตั้งค่า wizard step แรก
      // เริ่มต้นหน้า: เติม dropdown, render dashboard และตั้งค่า wizard step แรก
      populateStaticDropdowns();
      renderDashboard();
      updateWizard();
});