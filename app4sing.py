import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Real-time Adaptive Rhythm Guide",
    page_icon="🎵",
    layout="centered"
)

st.title("🎵 Rhythm Guide for Singers")
st.subheader("ระบบช่วยจับจังหวะเพลงและสั่นแบบ Real-time Continuous")

st.markdown("""
**วิธีใช้งาน:**
1. **กดปุ่ม 1 ครั้ง** เพื่อเริ่มเปิดไมโครโฟน -> ระบบจะจับจังหวะเพลงและ **สั่นตามจังหวะพร้อมปรับ BPM แบบ Real-time ตลอดเวลา**
2. **กดปุ่มอีกครั้ง (แตะ 1 ครั้ง)** เพื่อปิดระบบและหยุดสั่น
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
            touch-action: manipulation;
            transition: transform 0.1s ease, background 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 20px;
        }
        .main-btn.active {
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
            font-size: 38px;
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
    <button id="rhythmBtn" class="main-btn">กดเพื่อเริ่ม<br>จับจังหวะ</button>
    <div id="status" class="status">พร้อมใช้งาน</div>
    <div id="bpmDisplay" class="bpm-display">-- BPM</div>
</div>

<script>
    let isActive = false;

    let audioCtx = null;
    let analyser = null;
    let microphone = null;
    let scriptNode = null;

    let beatTimestamps = [];
    let lastBeatTime = 0;
    
    const btn = document.getElementById('rhythmBtn');
    const statusText = document.getElementById('status');
    const bpmDisplay = document.getElementById('bpmDisplay');

    const supportsVibration = "vibrate" in navigator;

    btn.addEventListener('click', toggleSystem);

    function toggleSystem() {
        if (!isActive) {
            startRealtimeTracking();
        } else {
            stopSystem();
        }
    }

    // --- เริ่มทำงานจับจังหวะและสั่นแบบ Real-time Continuous ---
    async function startRealtimeTracking() {
        isActive = true;
        beatTimestamps = [];
        lastBeatTime = 0;

        btn.classList.add('active');
        btn.innerHTML = "กำลังใช้งาน<br>(แตะเพื่อหยุด)";
        statusText.innerText = "กำลังฟังดนตรีและสั่นปรับตามจังหวะ...";
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

            let energyHistory = [];

            scriptNode.onaudioprocess = function() {
                if (!isActive) return;

                const array = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(array);
                
                // จับพลังงานช่วงเบส (Bass / Kick drum) Bins 0-7
                let sum = 0;
                for (let i = 0; i < 8; i++) {
                    sum += array[i];
                }
                const currentEnergy = sum / 8;
                const now = performance.now();

                // Dynamic Threshold เพื่อปรับตามความดังเบาของเพลงตลอดเวลา
                energyHistory.push(currentEnergy);
                if (energyHistory.length > 25) energyHistory.shift();
                const avgEnergy = energyHistory.reduce((a, b) => a + b, 0) / energyHistory.length;

                // ตรวจจับ Beat Peak และสั่นตามทันทีเมื่อเจอจังหวะ
                if (currentEnergy > 90 && currentEnergy > avgEnergy * 1.3) {
                    // ป้องกันการสั่นรัวเกินไป (เว้นระยะอย่างน้อย 250ms = รองรับได้สูงสุด 240 BPM)
                    if (now - lastBeatTime > 250) {
                        lastBeatTime = now;
                        beatTimestamps.push(now);

                        // เก็บข้อมูลย้อนหลัง 10 จังหวะล่าสุดเพื่อคำนวณ BPM ให้เสถียร
                        if (beatTimestamps.length > 10) beatTimestamps.shift();

                        // ⚡ สั่นทันทีตามจังหวะดนตรีที่จับได้ในขณะนั้น
                        if (supportsVibration) {
                            navigator.vibrate(60);
                        }

                        // คำนวณและอัปเดต BPM แสดงผลแบบ Real-time
                        calculateAndDisplayBPM();
                    }
                }
            };

        } catch (err) {
            alert("ไม่สามารถเข้าถึงไมโครโฟนได้: " + err.message);
            stopSystem();
        }
    }

    // คำนวณค่า BPM ล่าสุดแบบ Real-time
    function calculateAndDisplayBPM() {
        if (beatTimestamps.length < 3) return;

        let intervals = [];
        for (let i = 1; i < beatTimestamps.length; i++) {
            intervals.push(beatTimestamps[i] - beatTimestamps[i-1]);
        }

        // ใช้ค่ามัธยฐาน (Median) กรองค่าดิบเพื่อป้องกันจังหวะหลุด
        intervals.sort((a, b) => a - b);
        const mid = Math.floor(intervals.length / 2);
        const medianInterval = intervals.length % 2 !== 0 
            ? intervals[mid] 
            : (intervals[mid - 1] + intervals[mid]) / 2;

        const currentBPM = Math.round(60000 / medianInterval);

        if (currentBPM >= 50 && currentBPM <= 220) {
            bpmDisplay.innerText = currentBPM + " BPM";
        }
    }

    // --- หยุดทำงานทั้งหมด ---
    function stopSystem() {
        isActive = false;

        if (supportsVibration) {
            navigator.vibrate(0);
        }

        if (microphone && microphone.mediaStream) {
            microphone.mediaStream.getTracks().forEach(track => track.stop());
        }
        if (audioCtx) {
            audioCtx.close();
            audioCtx = null;
        }

        btn.className = "main-btn";
        btn.innerHTML = "กดเพื่อเริ่ม<br>จับจังหวะ";
        statusText.innerText = "พร้อมใช้งาน";
        bpmDisplay.innerText = "-- BPM";
    }
</script>
</body>
</html>
"""

# แสดงผล HTML ใน Streamlit
components.html(html_code, height=480)
