import cv2
import numpy as np
import base64
import os
import json
import re
import tempfile
from dotenv import load_dotenv
load_dotenv()


def safe_lap_var(gray: np.ndarray) -> float:
    try:
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        try:
            sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            return float((sx**2 + sy**2).mean())
        except Exception:
            return float(np.std(gray.astype(np.float64))**2)


def to_gray(frame: np.ndarray) -> np.ndarray:
    if frame is None:
        return np.zeros((100, 100), dtype=np.uint8)
    if len(frame.shape) == 2:
        return frame.copy()
    if frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def analyze_video(file_bytes: bytes, filename: str) -> dict:
    try:
        suffix = "." + filename.split(".")[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        frames, frame_times = extract_key_frames(tmp_path)

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if not frames:
            return {
                "verdict":"error", "confidence":0,
                "findings":["Could not extract frames — unsupported format or corrupted file"],
                "signals":[], "filename":filename, "engine":"video"
            }

        blink_score    = analyze_blink_patterns(frames)
        boundary_score = analyze_face_boundaries(frames)
        consistency    = analyze_temporal_consistency(frames)
        compression    = analyze_compression_artifacts(frames)

        groq_result = analyze_video_with_groq(frames, filename, frame_times)
        groq_score  = groq_result["risk_score"]
        groq_ok     = groq_result["groq_ok"]

        signals = [
            {"name":"Groq AI video scan",      "value":groq_score,    "color":score_color(groq_score)},
            {"name":"Face boundary artifacts", "value":boundary_score,"color":score_color(boundary_score)},
            {"name":"Temporal inconsistency",  "value":consistency,   "color":score_color(consistency)},
            {"name":"Compression artifacts",   "value":compression,   "color":score_color(compression)},
            {"name":"Blink pattern anomaly",   "value":blink_score,   "color":score_color(blink_score)},
        ]

        if groq_ok:
            # Groq is dominant — if it says real, verdict is real
            fake_score = (
                groq_score     * 0.55 +
                boundary_score * 0.15 +
                consistency    * 0.10 +
                compression    * 0.10 +
                blink_score    * 0.10
            )
        else:
            fake_score = (
                boundary_score * 0.30 +
                consistency    * 0.25 +
                compression    * 0.25 +
                blink_score    * 0.20
            )

        verdict, confidence = get_verdict(fake_score)

        findings = (
            groq_result["findings"]
            + [blink_finding(blink_score)]
            + [boundary_finding(boundary_score)]
            + [consistency_finding(consistency)]
            + [f"Analyzed {len(frames)} key frames from video"]
        )

        thumbnail_b64 = frame_to_b64(frames[0]) if frames else None

        return {
            "verdict":         verdict,
            "confidence":      confidence,
            "fake_score":      round(fake_score, 1),
            "signals":         signals,
            "findings":        [f for f in findings if f],
            "heatmap_b64":     thumbnail_b64,
            "filename":        filename,
            "engine":          "video",
            "ai_summary":      groq_result["summary"],
            "groq_active":     groq_ok,
            "frames_analyzed": len(frames),
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"verdict":"error", "confidence":0, "error":str(e),
                "findings":[f"Video engine error: {str(e)}"], "signals":[], "filename":filename, "engine":"video"}


def extract_key_frames(video_path: str, max_frames: int = 8) -> tuple:
    cap    = cv2.VideoCapture(video_path)
    frames = []
    times  = []

    if not cap.isOpened():
        return [], []

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps   = cap.get(cv2.CAP_PROP_FPS) or 30

    if total <= 0:
        for _ in range(max_frames * 10):
            ret, frame = cap.read()
            if not ret: break
            if len(frames) < max_frames:
                frames.append(frame)
                times.append(round(len(frames)/fps, 2))
        cap.release()
        return frames, times

    indices = np.linspace(0, total-1, min(max_frames, total), dtype=int)
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            if w > 640:
                scale = 640/w
                frame = cv2.resize(frame, (640, int(h*scale)))
            frames.append(frame)
            times.append(round(idx/fps, 2))

    cap.release()
    return frames, times


def analyze_blink_patterns(frames: list) -> int:
    if len(frames) < 3:
        return 15
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
        eye_cascade  = cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_eye.xml")
        eye_brightness = []
        for frame in frames:
            gray  = to_gray(frame)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60,60))
            if len(faces)==0: continue
            x,y,w,h = faces[0]
            face_roi = gray[y:y+h,x:x+w]
            eyes     = eye_cascade.detectMultiScale(face_roi, 1.1, 3)
            if len(eyes)>=1:
                ex,ey,ew,eh = eyes[0]
                eye_region  = face_roi[ey:ey+eh,ex:ex+ew]
                eye_brightness.append(float(eye_region.mean()))
        if len(eye_brightness)<2:
            return 15
        variance = np.std(eye_brightness)
        if variance < 2.0: return 70
        if variance < 5.0: return 40
        return 12
    except Exception as e:
        print(f"Blink error: {e}")
        return 15


def analyze_face_boundaries(frames: list) -> int:
    if not frames:
        return 15
    try:
        face_cascade   = cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
        boundary_scores= []
        for frame in frames:
            gray  = to_gray(frame)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60,60))
            if len(faces)==0: continue
            x,y,w,h = faces[0]
            bw = 8
            face_inner = gray[y+bw:y+h-bw,x+bw:x+w-bw]
            face_outer = gray[max(0,y-bw):y+bw,max(0,x-bw):x+w+bw]
            if face_inner.size==0 or face_outer.size==0: continue
            inner_std  = face_inner.std()
            outer_std  = face_outer.std()
            ratio      = abs(inner_std-outer_std)/(outer_std+1e-6)
            try:
                edges        = cv2.Canny(gray[y:y+h,x:x+w],50,150)
                edge_density = edges.sum()/(edges.shape[0]*edges.shape[1]+1e-6)
            except Exception:
                edge_density = 0.05
            score = min(100, int(ratio*40+edge_density*200))
            boundary_scores.append(score)
        return min(100, int(np.mean(boundary_scores))) if boundary_scores else 15
    except Exception as e:
        print(f"Boundary error: {e}")
        return 15


def analyze_temporal_consistency(frames: list) -> int:
    """
    Fixed: uses coefficient of variation so natural scene changes
    in real videos don't score as suspicious.
    """
    if len(frames) < 2:
        return 15
    try:
        diffs = []
        for i in range(1, len(frames)):
            prev = to_gray(frames[i-1]).astype(np.float32)
            curr = to_gray(frames[i]).astype(np.float32)
            if prev.shape != curr.shape:
                curr = cv2.resize(curr, (prev.shape[1], prev.shape[0]))
            diff = np.abs(prev-curr).mean()
            diffs.append(diff)

        if not diffs:
            return 15

        mean_diff = np.mean(diffs)
        std_diff  = np.std(diffs)

        # Coefficient of variation — normalized measure
        # Real videos: naturally high mean diff (scene changes) but proportional std
        # Deepfakes: unnatural spikes = disproportionately high std vs mean
        cv = std_diff / (mean_diff + 1e-6)

        if cv < 1.0:    return 10   # very consistent = real
        elif cv < 1.5:  return 25   # normal variation = real
        elif cv < 2.5:  return 45   # suspicious
        else:           return min(80, int(cv * 20))

    except Exception as e:
        print(f"Temporal consistency error: {e}")
        return 15


def analyze_compression_artifacts(frames: list) -> int:
    if not frames:
        return 15
    try:
        scores = []
        for frame in frames:
            gray       = to_gray(frame).astype(np.float32)
            h, w       = gray.shape
            block_size = 8
            block_vars = []
            for y in range(0, h-block_size, block_size*2):
                for x in range(0, w-block_size, block_size*2):
                    block = gray[y:y+block_size,x:x+block_size]
                    block_vars.append(float(block.var()))
            if block_vars:
                var_of_vars = np.std(block_vars)
                score       = min(100, int(100-min(100,var_of_vars/10)))
                scores.append(score)
        return min(100, int(np.mean(scores))) if scores else 15
    except Exception as e:
        print(f"Compression error: {e}")
        return 15


def analyze_video_with_groq(frames: list, filename: str, frame_times: list) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key=="your_groq_api_key_here":
        return {"risk_score":50,"groq_ok":False,"summary":"Groq API key not set","findings":["Set GROQ_API_KEY in .env"]}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
        frame_stats  = []
        for i, frame in enumerate(frames[:6]):
            gray    = to_gray(frame)
            lap_var = round(safe_lap_var(gray.astype(np.float32)), 1)
            mean_px = round(float(gray.mean()), 1)
            faces   = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60,60))
            t       = frame_times[i] if i < len(frame_times) else i
            frame_stats.append({
                "time_sec":    t,
                "sharpness":   lap_var,
                "brightness":  mean_px,
                "faces_found": len(faces),
            })

        prompt = f"""You are a deepfake video detection expert. Analyze these frame statistics and determine if the video is authentic or a deepfake.

Filename: {filename}
Total frames analyzed: {len(frames)}
Frame statistics:
{json.dumps(frame_stats, indent=2)}

IMPORTANT CONTEXT:
- These frames are sampled at EVEN INTERVALS across the entire video
- Real videos NATURALLY have high sharpness variation between non-consecutive frames
- Scene cuts, camera movements, and lighting changes are NORMAL in real videos
- Only flag as deepfake if you see UNNATURAL patterns

Signs of a REAL video:
- Variable sharpness between frames (normal for different scenes)
- Faces detected in some frames but not others (normal, person moves)
- Gradual brightness changes

Signs of a DEEPFAKE:
- Face present in every frame but facial geometry changes unnaturally
- Brightness is suspiciously IDENTICAL across all frames
- Sharpness is either TOO uniform or has random spikes without scene context

Scoring guide — BE CONSERVATIVE, most videos are authentic:
- Clearly authentic = 5-20
- Likely real with minor anomalies = 21-40
- Genuinely suspicious = 41-65
- Likely deepfake = 66-82
- Clear deepfake with strong evidence = 83-99

Return ONLY valid JSON:
{{
  "risk_score": <0-100>,
  "summary": "<one sentence verdict>",
  "findings": ["finding 1", "finding 2", "finding 3"]
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.1, max_tokens=400,
        )
        result            = parse_groq_response(response.choices[0].message.content)
        result["groq_ok"] = True
        print(f"Groq video OK — score: {result['risk_score']} | {result['summary']}")
        return result

    except Exception as e:
        print(f"Groq video error: {e}")
        return {"risk_score":50,"groq_ok":False,"summary":"Groq unavailable","findings":[f"Groq error: {str(e)}"]}


def frame_to_b64(frame: np.ndarray) -> str:
    try:
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return base64.b64encode(buf).decode("utf-8")
    except Exception:
        return ""


def parse_groq_response(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {
                "risk_score": max(0, min(100, int(data.get("risk_score", 50)))),
                "summary":    str(data.get("summary",   "Analysis complete")),
                "findings":   list(data.get("findings", [])),
            }
    except Exception as e:
        print(f"Parse error: {e}")
    return {"risk_score":50,"summary":"Could not parse response","findings":[]}


def get_verdict(fake_score: float) -> tuple:
    if fake_score >= 60:
        return "fake",       min(99, int(55 + fake_score*0.44))
    elif fake_score >= 38:
        return "suspicious", min(88, int(45 + fake_score*0.70))
    else:
        return "real",       min(99, int(95 - fake_score*0.80))

def score_color(value: int) -> str:
    if value >= 60: return "#EF4444"
    if value >= 35: return "#F59E0B"
    return "#22C55E"

def blink_finding(score: int) -> str:
    if score >= 60: return "Blink pattern abnormal — frequency inconsistent with natural eye movement"
    if score >= 35: return "Blink pattern slightly irregular"
    return "Blink pattern within normal human range"

def boundary_finding(score: int) -> str:
    if score >= 60: return "Face boundary artifacts detected — blending inconsistencies found"
    if score >= 35: return "Minor face boundary irregularities detected"
    return "Face boundaries appear natural and consistent"

def consistency_finding(score: int) -> str:
    if score >= 60: return "Temporal inconsistency detected — unnatural pixel changes between frames"
    if score >= 35: return "Moderate temporal variance between frames"
    return "Temporal consistency normal — smooth frame transitions"