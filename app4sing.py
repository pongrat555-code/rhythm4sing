import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Rhythm Sync Guide for Singers",
    page_icon="🎵",
    layout="centered"
)

st.title("🎵 Rhythm Guide for Singers")
st.subheader("ระบบช่วยจับจังหวะเพลงด้วยการสั่นแบบ Real-time")

st.markdown("""
**วิธีใช้งาน:**
1. **กดปุ่มค้างไว้** เพื่อฟังเสียงดนตรีผ่านไมโครโฟน -> **โทรศัพท์จะสั่นตามจังหวะเพลงจริงทันที**
2. **ปล่อยปุ่ม** เมื่อพอใจกับจังหวะ -> โทรศัพท์จะสั่นต่อด้วยจังหวะที่เสถียรอย่างต่อเนื่องโดยไม่สะดุด
3. **กดปุ่มอีกครั้ง (แตะ 1 ครั้ง)** เพื่อหยุดการสั่น
""")

# JavaScript & HTML App
html_code = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * {
            box-sizing: border-box;
            user-select: none;
            -webkit-user-select: none;
            -webkit-touch-callout: none;
        }
        body {
            margin: 0;
            padding: 0;
            background-color: transparent;
        }
        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: system-ui, -apple-system, sans-serif;
            padding: 20px 0;
        }
        .main-btn {
            width: 220px;
            height: 220px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(145deg, #2196F3, #1e88e5);
            color: white;
            font-size: 20px;
            font-weight: bold;
            box-shadow: 0 10px 25px rgba(33, 150, 243, 0.4);
            cursor: pointer;
            touch-action: none;
            transition: transform 0.1s ease, background 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 20px;
        }
        .main-btn:active, .main-btn.holding {
            background: linear-gradient(145deg, #ff5722, #f44336);
            transform: scale(0.95);
            box-shadow: 0 5px 15px rgba(244, 67, 54, 0.5);
        }
        .main-btn.vibrating {
            background: linear-gradient(145deg, #4CAF50, #43a047);
            animation: pulse 1s infinite;
        }
        .status {
            margin-top: 25px;
            font-size: 18px;
            font-weight: 500;
            color: #333;
            text-align: center;
            min-height: 27px;
        }
        .bpm-display {
            font-size: 36px;
            font-weight: 800;
            color: #1976D2;
            margin-top: 10px;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); }
            70% { box-shadow: 0 0 0 20px rgba(76, 175, 80, 0); }
            100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
        }
    </style>
</head>
<body>

<div class="container">
    <button id="rhythmBtn" class="main-btn">กดค้าง<br>เพื่อจับจังหวะ</button>
    <div id="status" class="status">พร้อมใช้งาน</div>
    <div id="bpmDisplay" class="bpm-display">-- BPM</div>
</div>

<script>
    // System States: 'IDLE', 'HOLDING', 'LOCKED'
    let currentState = 'IDLE';

    let audioCtx = null;
    let analyser = null;
    let microphone = null;
    let scriptNode = null;

    let beatTimestamps = [];
    let lastBeatTime = 0;
    let lockedIntervalMs = 0;
    
    let timerTimeout = null;
    let timerInterval = null;

    const btn = document.getElementById('rhythmBtn');
    const statusText = document.getElementById('status');
    const bpmDisplay = document.getElementById('bpmDisplay');

    const supportsVibration = "vibrate" in navigator;

    // --- Touch & Mouse Event Handling ---
    btn.addEventListener('pointerdown', handlePointerDown);
    btn.addEventListener('pointerup', handlePointerUp);
    btn.addEventListener('pointerleave', handlePointerUp);

    function handlePointerDown(e) {
        e.preventDefault();
        
        // ถ้ากำลังสั่นแบบ LOCKED อยู่ แล้วกดปุ่มซ้ำ -> ให้หยุดทำงาน
        if (currentState === 'LOCKED') {
            stopAll();
            return;
        }

        if (currentState === 'IDLE') {
            startHolding();
        }
    }

    function handlePointerUp(e) {
        e.preventDefault();
        if (currentState === 'HOLDING') {
            lockAndContinueVibrating();
        }
    }

    // --- 1. เริ่มกดค้าง (HOLDING) -> ฟังเสียง + สั่น Real-time ---
    async function startHolding() {
        currentState = 'HOLDING';
        beatTimestamps = [];
        lastBeatTime = 0;

        btn.classList.add('holding');
        btn.innerHTML = "กำลังฟัง & สั่น<br>ตามจังหวะ...";
        statusText.innerText = "กำลังตรวจจับจังหวะเสียงดนตรี...";
        bpmDisplay.innerText = "-- BPM";

        try {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            microphone = audioCtx.createMediaStreamSource(stream);
            scriptNode = audioCtx.createScriptProcessor(2048, 1, 1);
            
            microphone.connect(analyser);
            analyser.connect(scriptNode);
            scriptNode.connect(audioCtx.destination);

            // ตัวแปรสำหรับคำนวณ Peak Detection
            let energyHistory = [];

            scriptNode.onaudioprocess = function() {
                if (currentState !== 'HOLDING') return;

                const array = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(array);
                
                // เน้นย่านความถี่ต่ำ (Bass / Kick drum) Bins 0-8
                let sum = 0;
                for (let i = 0; i < 8; i++) {
                    sum += array[i];
                }
                const currentEnergy = sum / 8;
                const now = performance.now();

                // คำนวณค่าเฉลี่ยพลังงานย้อนหลังเพื่อทำ Dynamic Threshold
                energyHistory.push(currentEnergy);
                if (energyHistory.length > 20) energyHistory.shift();
                const avgEnergy = energyHistory.reduce((a, b) => a + b, 0) / energyHistory.length;

                // ตรวจจับ Beat Peak (พลังงานสูงกว่าค่าเฉลี่ย + เว้นระยะอย่างน้อย 250ms = ไม่เกิน 240 BPM)
                if (currentEnergy > 100 && currentEnergy > avgEnergy * 1.35) {
                    if (now - lastBeatTime > 250) {
                        lastBeatTime = now;
                        beatTimestamps.push(now);

                        // ⚡ สั่นทันทีแบบ Real-time ขนาดความยาว 50ms
                        if (supportsVibration) {
                            navigator.vibrate(50);
                        }

                        // คำนวณ BPM แสดงผลแบบคร่าวๆ ขณะกดค้าง
                        updateLiveBPMDisplay();
                    }
                }
            };

        } catch (err) {
            alert("ไม่สามารถเข้าถึงไมโครโฟนได้: " + err.message);
            stopAll();
        }
    }

    // แสดงผล BPM แบบ Real-time
    function updateLiveBPMDisplay() {
        if (beatTimestamps.length < 2) return;
        const recent = beatTimestamps.slice(-5);
        let intervals = [];
        for (let i = 1; i < recent.length; i++) {
            intervals.push(recent[i] - recent[i-1]);
        }
        const avgInt = intervals.reduce((a, b) => a + b, 0) / intervals.length;
        const bpm = Math.round(60000 / avgInt);
        if (bpm >= 50 && bpm <= 220) {
            bpmDisplay.innerText = bpm + " BPM";
        }
    }

    // --- 2. ปล่อยปุ่ม (RELEASE) -> คำนวณ BPM + สั่นต่อแบบไม่สะดุด ---
    function lockAndContinueVibrating() {
        currentState = 'LOCKED';
        btn.classList.remove('holding');

        // ปิดการทำงานไมโครโฟน
        stopMicrophone();

        // คำนวณค่า BPM สรุปผล
        const calculatedBPM = calculateFinalBPM();

        if (calculatedBPM > 0) {
            lockedIntervalMs = 60000 / calculatedBPM;
            bpmDisplay.innerText = calculatedBPM + " BPM";
            
            btn.classList.add('vibrating');
            btn.innerHTML = "แตะ 1 ครั้ง<br>เพื่อหยุดสั่น";
            statusText.innerText = "สั่นต่อตามจังหวะที่คำนวณได้";

            // 🔄 คำนวณเวลาสั่นครั้งต่อไปเพื่อให้จังหวะสืบต่ออย่างสมบูรณ์แบบ (Seamless Continuation)
            const now = performance.now();
            const timeSinceLastBeat = now - lastBeatTime;
            
            // เวลาที่ต้องรอสำหรับ Beat ถัดไป
            let delayToNextBeat = lockedIntervalMs - (timeSinceLastBeat % lockedIntervalMs);
            if (delayToNextBeat < 0) delayToNextBeat = 0;

            // ตั้งเวลาสำหรับ Beat แรกหลังปล่อยปุ่ม แล้วเข้าสู่ Loop สั่นแบบคงที่
            timerTimeout = setTimeout(() => {
                triggerVibe();
                timerInterval = setInterval(triggerVibe, lockedIntervalMs);
            }, delayToNextBeat);

        } else {
            statusText.innerText = "จับจังหวะไม่ได้ ลองกดค้างให้นานขึ้น";
            bpmDisplay.innerText = "-- BPM";
            setTimeout(stopAll, 1500);
        }
    }

    function triggerVibe() {
        if (currentState === 'LOCKED' && supportsVibration) {
            navigator.vibrate(50);
        }
    }

    // คำนวณ BPM จากลำดับ Beat ที่บันทึกไว้
    function calculateFinalBPM() {
        if (beatTimestamps.length < 3) return 0;

        let intervals = [];
        for (let i = 1; i < beatTimestamps.length; i++) {
            intervals.push(beatTimestamps[i] - beatTimestamps[i-1]);
        }

        // กรองค่ามั่ว (Outliers) ออก
        intervals.sort((a, b) => a - b);
        const mid = Math.floor(intervals.length / 2);
        const medianInterval = intervals.length % 2 !== 0 ? intervals[mid] : (intervals[mid - 1] + intervals[mid]) / 2;

        const bpm = Math.round(60000 / medianInterval);

        if (bpm >= 50 && bpm <= 200) {
            return bpm;
        }
        return 0;
    }

    function stopMicrophone() {
        if (microphone && microphone.mediaStream) {
            microphone.mediaStream.getTracks().forEach(track => track.stop());
        }
        if (audioCtx) {
            audioCtx.close();
            audioCtx = null;
        }
    }

    // --- 3. กดปุ่มอีกครั้ง (STOP) -> หยุดทำงานทั้งหมด ---
    function stopAll() {
        currentState = 'IDLE';

        if (timerTimeout) clearTimeout(timerTimeout);
        if (timerInterval) clearInterval(timerInterval);
        timerTimeout = null;
        timerInterval = null;

        if (supportsVibration) {
            navigator.vibrate(0);
        }

        stopMicrophone();

        btn.className = "main-btn";
        btn.innerHTML = "กดค้าง<br>เพื่อจับจังหวะ";
        statusText.innerText = "พร้อมใช้งาน";
        bpmDisplay.innerText = "-- BPM";
    }
</script>
</body>
</html>
"""

# แสดงผล HTML ใน Streamlit
components.html(html_code, height=480)
