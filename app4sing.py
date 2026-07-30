import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Rhythm Sync Guide for Singers",
    page_icon="🎵",
    layout="centered"
)

st.title("🎵 Rhythm Guide for Singers")
st.subheader("ระบบช่วยจับจังหวะเพลงด้วยการสั่น")

st.markdown("""
**วิธีใช้งาน:**
1. **กดปุ่มค้างไว้** เพื่อเริ่มฟังเสียงดนตรีผ่านไมโครโฟน
2. **ปล่อยปุ่ม** เมื่อต้องการคำนวณจังหวะ -> โทรศัพท์จะเริ่มสั่นตามจังหวะเพลงทันที
3. **กดปุ่มอีกครั้ง (แตะ 1 ครั้ง)** เพื่อหยุดการสั่น
""")

# JavaScript & HTML App
html_code = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: sans-serif;
            margin-top: 20px;
        }
        .main-btn {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            border: none;
            background-color: #2196F3;
            color: white;
            font-size: 18px;
            font-weight: bold;
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
            cursor: pointer;
            user-select: none;
            -webkit-user-select: none;
            touch-action: manipulation;
            transition: all 0.2s ease;
        }
        .main-btn:active, .main-btn.listening {
            background-color: #f44336;
            transform: scale(0.95);
        }
        .main-btn.vibrating {
            background-color: #4CAF50;
            animation: pulse 1s infinite;
        }
        .status {
            margin-top: 20px;
            font-size: 16px;
            color: #333;
            text-align: center;
        }
        .bpm-display {
            font-size: 28px;
            font-weight: bold;
            color: #1E88E5;
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
    <button id="rhythmBtn" class="main-btn">กดค้างเพื่อฟังจังหวะ</button>
    <div id="status" class="status">พร้อมใช้งาน</div>
    <div id="bpmDisplay" class="bpm-display">-- BPM</div>
</div>

<script>
    let audioCtx;
    let analyser;
    let microphone;
    let scriptNode;
    let isListening = false;
    let isVibrating = false;
    let energyBuffer = [];
    let intervalId = null;
    let calculatedBPM = 0;

    const btn = document.getElementById('rhythmBtn');
    const statusText = document.getElementById('status');
    const bpmDisplay = document.getElementById('bpmDisplay');

    // ตรวจสอบการรองรับการสั่น
    const supportsVibration = "vibrate" in navigator;

    // Event Listeners สำหรับ Desktop และ Mobile Touch
    btn.addEventListener('mousedown', startListening);
    btn.addEventListener('mouseup', stopListeningAndVibrate);
    btn.addEventListener('touchstart', (e) => { e.preventDefault(); startListening(); });
    btn.addEventListener('touchend', (e) => { e.preventDefault(); stopListeningAndVibrate(); });

    async function startListening() {
        if (isVibrating) {
            // ถ้ากำลังสั่นอยู่ แล้วกดซ้ำ ให้หยุดสั่นทันที
            stopVibration();
            return;
        }

        if (isListening) return;
        isListening = true;
        energyBuffer = [];

        btn.classList.add('listening');
        btn.innerText = "กำลังฟัง...";
        statusText.innerText = "กำลังตรวจจับเสียงดนตรี...";
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

            scriptNode.onaudioprocess = function() {
                const array = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(array);
                
                // คำนวณพลังงานเสียงย่าน Bass/Kick (ย่านความถี่ต่ำสุด)
                let sum = 0;
                for (let i = 0; i < 10; i++) {
                    sum += array[i];
                }
                const average = sum / 10;
                energyBuffer.push({ time: Date.now(), energy: average });
            };

        } catch (err) {
            alert("ไม่สามารถเข้าถึงไมโครโฟนได้: " + err.message);
            resetState();
        }
    }

    function stopListeningAndVibrate() {
        if (!isListening) return;
        isListening = false;
        btn.classList.remove('listening');

        // ปิดการทำงานไมโครโฟน
        if (microphone && microphone.mediaStream) {
            microphone.mediaStream.getTracks().forEach(track => track.stop());
        }
        if (audioCtx) {
            audioCtx.close();
        }

        statusText.innerText = "กำลังคำนวณจังหวะ (BPM)...";

        // คำนวณ BPM จาก Energy Peaks
        calculatedBPM = calculateBPM(energyBuffer);

        if (calculatedBPM > 0) {
            bpmDisplay.innerText = calculatedBPM + " BPM";
            startVibration(calculatedBPM);
        } else {
            statusText.innerText = "ไม่สามารถหาจังหวะได้ ชัดเจน ลองกดค้างใหม่อีกครั้ง";
            bpmDisplay.innerText = "-- BPM";
            resetState();
        }
    }

    function calculateBPM(buffer) {
        if (buffer.length < 50) return 0;

        // หาจุดที่มี Peak ของพลังงานเสียง (Peak Detection)
        let peaks = [];
        let threshold = 120; // ค่าพลังงานขั้นต่ำ
        
        for (let i = 1; i < buffer.length - 1; i++) {
            if (buffer[i].energy > threshold && 
                buffer[i].energy > buffer[i-1].energy && 
                buffer[i].energy > buffer[i+1].energy) {
                
                // เว้นระยะห่างระหว่าง Peak อย่างน้อย 250ms (เพื่อไม่ให้รัวเกินไป)
                if (peaks.length === 0 || (buffer[i].time - peaks[peaks.length - 1]) > 250) {
                    peaks.push(buffer[i].time);
                }
            }
        }

        if (peaks.length < 2) return 0;

        // หาค่าเฉลี่ย Interval ระหว่าง Peak
        let intervals = [];
        for (let i = 1; i < peaks.length; i++) {
            intervals.push(peaks[i] - peaks[i-1]);
        }

        const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
        const bpm = Math.round(60000 / avgInterval);

        // จำกัดขอบเขต BPM ของเพลงทั่วไป (60 - 180 BPM)
        if (bpm >= 60 && bpm <= 180) {
            return bpm;
        } else if (bpm > 180 && bpm <= 360) {
            return Math.round(bpm / 2); // ปรับจังหวะครึ่งหนึ่ง
        }
        
        return 120; // Default fallback BPM
    }

    function startVibration(bpm) {
        isVibrating = true;
        btn.classList.add('vibrating');
        btn.innerText = "แตะเพื่อหยุดสั่น";
        statusText.innerText = "กำลังสั่นตามจังหวะ...";

        const intervalMs = (60 / bpm) * 1000;

        // สั่งสั่นตามจังหวะ
        function triggerVibe() {
            if (supportsVibration) {
                navigator.vibrate(60); // สั่นเป็นเวลา 60ms ในแต่ละ Beat
            }
        }

        triggerVibe();
        intervalId = setInterval(triggerVibe, intervalMs);
    }

    function stopVibration() {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
        if (supportsVibration) {
            navigator.vibrate(0); // สั่งหยุดสั่น
        }
        resetState();
    }

    function resetState() {
        isListening = false;
        isVibrating = false;
        btn.className = "main-btn";
        btn.innerText = "กดค้างเพื่อฟังจังหวะ";
        statusText.innerText = "พร้อมใช้งาน";
    }
</script>
</body>
</html>
"""

# แสดงผล HTML ใน Streamlit
components.html(html_code, height=450)
