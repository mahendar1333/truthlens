import cv2
import numpy as np
from PIL import Image, ExifTags
import io
import base64
import os
import json
import re
from dotenv import load_dotenv
load_dotenv()


def safe_laplacian_var(gray: np.ndarray) -> float:
    try:
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        try:
            sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            return float((sx**2 + sy**2).mean())
        except Exception:
            return float(np.std(gray.astype(np.float64))**2)


def to_gray(img_cv: np.ndarray) -> np.ndarray:
    if img_cv is None:
        return np.zeros((100,100), dtype=np.uint8)
    if len(img_cv.shape)==2:
        return img_cv.copy()
    if img_cv.shape[2]==4:
        return cv2.cvtColor(img_cv, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)


def analyze_image(file_bytes: bytes, filename: str) -> dict:
    try:
        img_pil = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        buf     = io.BytesIO()
        img_pil.save(buf, format="JPEG", quality=95)
        jpeg_bytes = buf.getvalue()

        img_cv = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img_cv is None:
            return {"verdict":"error","confidence":0,"findings":["Could not decode image"],"signals":[],"filename":filename,"engine":"image"}

        ela_score,   ela_heatmap, ela_raw = run_ela(jpeg_bytes, img_pil)
        exif_score,  exif_findings        = analyze_exif(img_pil)
        clone_score, clone_finding        = detect_clones(img_cv)
        ai_score                          = estimate_ai_generated(img_cv)
        dct_score                         = run_dct_analysis(img_cv)
        noise_score                       = run_noise_analysis(img_cv)

        img_b64     = base64.b64encode(jpeg_bytes).decode("utf-8")
        groq_result = analyze_with_groq(img_b64, filename, img_cv, ela_raw, ai_score, dct_score, noise_score)
        groq_score  = groq_result["risk_score"]
        groq_ok     = groq_result["groq_ok"]

        signals = [
            {"name":"Groq AI vision",       "value":groq_score,       "color":score_color(groq_score)},
            {"name":"ELA anomaly",          "value":ela_score,        "color":score_color(ela_score)},
            {"name":"DCT frequency",        "value":dct_score,        "color":score_color(dct_score)},
            {"name":"Noise pattern (SPN)",  "value":noise_score,      "color":score_color(noise_score)},
            {"name":"EXIF integrity loss",  "value":100-exif_score,   "color":score_color(100-exif_score)},
            {"name":"Clone detection",      "value":clone_score,      "color":score_color(clone_score)},
            {"name":"AI-gen estimate",      "value":ai_score,         "color":score_color(ai_score)},
        ]

        if groq_ok:
            fake_score = (
                groq_score       * 0.40 +
                ela_score        * 0.15 +
                dct_score        * 0.15 +
                noise_score      * 0.10 +
                clone_score      * 0.10 +
                (100-exif_score) * 0.05 +
                ai_score         * 0.05
            )
        else:
            fake_score = (
                ela_score        * 0.25 +
                dct_score        * 0.25 +
                noise_score      * 0.15 +
                clone_score      * 0.20 +
                (100-exif_score) * 0.10 +
                ai_score         * 0.05
            )

        verdict, confidence = get_verdict(fake_score)
        findings = groq_result["findings"] + exif_findings + [clone_finding] + ela_findings_text(ela_score, ela_raw) + dct_findings(dct_score) + noise_findings(noise_score)

        return {
            "verdict":     verdict,
            "confidence":  confidence,
            "fake_score":  round(fake_score, 1),
            "signals":     signals,
            "findings":    [f for f in findings if f],
            "heatmap_b64": ela_heatmap,
            "filename":    filename,
            "engine":      "image",
            "ai_summary":  groq_result["summary"],
            "groq_active": groq_ok,
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"verdict":"error","confidence":0,"error":str(e),"findings":[f"Engine error: {str(e)}"],"signals":[],"filename":filename,"engine":"image"}


# ── ELA ───────────────────────────────────────────────────────────────

def run_ela(file_bytes: bytes, img_pil: Image.Image, quality: int=90) -> tuple:
    try:
        rgb_pil = img_pil.convert("RGB")
        buf1    = io.BytesIO()
        rgb_pil.save(buf1, format="JPEG", quality=quality)
        buf1.seek(0)
        recompressed = Image.open(buf1).convert("RGB")

        orig     = np.array(rgb_pil,      dtype=np.float32)
        recom    = np.array(recompressed, dtype=np.float32)
        diff     = np.abs(orig - recom)
        diff_gray= diff.mean(axis=2)
        raw_mean = float(diff_gray.mean())

        if raw_mean < 3.0:   ela_score = int(raw_mean * 8)
        elif raw_mean < 8.0: ela_score = int(20 + raw_mean * 6)
        else:                ela_score = min(100, int(60 + raw_mean * 3))

        ela_u8  = np.clip(diff_gray * 15, 0, 255).astype(np.uint8)
        colored = np.zeros((*ela_u8.shape, 3), dtype=np.uint8)
        colored[:,:,0] = np.clip(ela_u8.astype(np.int32)*2,       0, 255).astype(np.uint8)
        colored[:,:,1] = np.clip(ela_u8.astype(np.int32)-64,      0, 255).astype(np.uint8)
        colored[:,:,2] = np.clip(255-ela_u8.astype(np.int32)*2,   0, 255).astype(np.uint8)

        heatmap_pil = Image.fromarray(colored, mode="RGB")
        buf2        = io.BytesIO()
        heatmap_pil.save(buf2, format="PNG")
        return ela_score, base64.b64encode(buf2.getvalue()).decode("utf-8"), raw_mean

    except Exception as e:
        print(f"ELA error: {e}")
        blank = Image.new("RGB",(100,100),(30,30,30))
        buf3  = io.BytesIO()
        blank.save(buf3, format="PNG")
        return 20, base64.b64encode(buf3.getvalue()).decode("utf-8"), 0.0


# ── DCT Frequency Analysis ────────────────────────────────────────────

def run_dct_analysis(img_cv: np.ndarray) -> int:
    """
    AI-generated images have unnaturally clean DCT frequency spectra.
    Real photos have organic high-frequency noise; AI images are too smooth.
    """
    try:
        gray    = to_gray(img_cv).astype(np.float32)
        h, w    = gray.shape

        # Tile DCT analysis on 8x8 blocks (like JPEG)
        block_energies = []
        for y in range(0, h-8, 16):
            for x in range(0, w-8, 16):
                block = gray[y:y+8, x:x+8]
                dct   = cv2.dct(block)
                # Ratio of high-freq to low-freq energy
                low_e  = float(np.abs(dct[:4, :4]).mean())
                high_e = float(np.abs(dct[4:, 4:]).mean())
                if low_e > 0:
                    block_energies.append(high_e / low_e)

        if not block_energies:
            return 30

        mean_ratio = np.mean(block_energies)
        std_ratio  = np.std(block_energies)

        # Real photos: variable high/low freq ratio across blocks
        # AI images: unnaturally uniform ratio (too smooth everywhere)
        # Very low mean_ratio + low std = AI-generated (too smooth)
        # Normal photos: mean_ratio 0.1-0.4, std > 0.05
        if mean_ratio < 0.05 and std_ratio < 0.02:
            return 85  # extremely smooth = AI generated
        elif mean_ratio < 0.10 and std_ratio < 0.04:
            return 65
        elif mean_ratio < 0.15:
            return 40
        else:
            return max(5, int(100 - mean_ratio * 200))

    except Exception as e:
        print(f"DCT error: {e}")
        return 25


# ── SPN Noise Analysis ────────────────────────────────────────────────

def run_noise_analysis(img_cv: np.ndarray) -> int:
    """
    Sensor Pattern Noise (SPN) — real cameras leave a unique noise fingerprint.
    AI-generated images have no camera noise or synthetic/uniform noise.
    """
    try:
        gray = to_gray(img_cv).astype(np.float32)

        # Extract noise residual using wavelet-like approach
        # Apply strong blur then subtract to get noise layer
        blurred = cv2.GaussianBlur(gray, (5,5), 0)
        noise   = gray - blurred

        noise_mean  = float(np.abs(noise).mean())
        noise_std   = float(noise.std())
        noise_kurt  = float(_kurtosis(noise.flatten()))

        # Real camera noise: gaussian-like (kurtosis near 3), std 1-8
        # AI images: either no noise (std<0.5) or synthetic patterned noise (high kurtosis)
        # Manipulated: noise inconsistency across regions

        # Check regional noise consistency
        h, w = noise.shape
        regions = [
            noise[:h//2, :w//2], noise[:h//2, w//2:],
            noise[h//2:, :w//2], noise[h//2:, w//2:],
        ]
        region_stds = [r.std() for r in regions]
        region_cv   = np.std(region_stds) / (np.mean(region_stds) + 1e-6)

        score = 20  # base

        # Very low noise = AI generated
        if noise_std < 0.8:
            score += 55
        elif noise_std < 2.0:
            score += 30

        # High kurtosis = synthetic/patterned noise
        if noise_kurt > 10:
            score += 20
        elif noise_kurt > 6:
            score += 10

        # High regional inconsistency = manipulation
        if region_cv > 0.5:
            score += 25
        elif region_cv > 0.3:
            score += 10

        return min(95, score)

    except Exception as e:
        print(f"Noise analysis error: {e}")
        return 25


def _kurtosis(data: np.ndarray) -> float:
    """Simple kurtosis calculation without scipy."""
    try:
        mu   = data.mean()
        std  = data.std()
        if std == 0: return 0
        return float(np.mean(((data - mu)/std)**4))
    except Exception:
        return 3.0


# ── EXIF ──────────────────────────────────────────────────────────────

def analyze_exif(img_pil: Image.Image) -> tuple:
    findings = []
    score    = 100
    try:
        exif_data = img_pil._getexif()
    except Exception:
        exif_data = None

    if not exif_data:
        findings.append("EXIF metadata absent — stripped, screenshot, or AI-generated")
        return 15, findings

    tags = {ExifTags.TAGS.get(k,k): v for k,v in exif_data.items()}

    make  = tags.get("Make",  "")
    model = tags.get("Model", "")
    if make or model:
        findings.append(f"Camera: {make} {model}".strip())
    else:
        findings.append("No camera hardware info in EXIF")
        score -= 20

    software      = str(tags.get("Software",""))
    editing_tools = ["photoshop","gimp","lightroom","affinity","canva","snapseed",
                     "pixlr","midjourney","stable diffusion","dall-e","firefly","runway"]
    if any(t in software.lower() for t in editing_tools):
        findings.append(f"Editing/AI software in EXIF: {software}")
        score -= 50
    elif software:
        findings.append(f"Software: {software}")

    if "DateTimeOriginal" in tags and "DateTime" in tags:
        if tags["DateTimeOriginal"] != tags["DateTime"]:
            findings.append("Timestamp mismatch: capture vs modified dates differ")
            score -= 15

    if "GPSInfo" in tags:
        findings.append("GPS location data intact")

    return max(0, score), findings


# ── Clone Detection ───────────────────────────────────────────────────

def detect_clones(img_cv: np.ndarray) -> tuple:
    try:
        gray = to_gray(img_cv)
        orb  = cv2.ORB_create(nfeatures=500)
        kps, descs = orb.detectAndCompute(gray, None)

        if descs is None or len(kps) < 10:
            return 5, "Not enough features for clone detection"

        bf      = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(descs, descs, k=3)
        suspicious = sum(1 for mg in matches for m in mg[1:] if m.distance < 30)

        ratio = suspicious / max(len(kps), 1)
        if ratio < 0.05:   score = int(ratio * 200)
        elif ratio < 0.15: score = int(20 + ratio * 200)
        else:              score = min(100, int(50 + ratio * 300))

        finding = (
            f"Clone-stamp: {suspicious} duplicate regions detected" if suspicious > 15
            else f"{suspicious} minor feature duplicates (within normal range)" if suspicious > 5
            else "No clone or copy-paste regions detected"
        )
        return score, finding

    except Exception as e:
        return 10, f"Clone detection skipped: {str(e)}"


# ── AI-Gen Estimator ──────────────────────────────────────────────────

def estimate_ai_generated(img_cv: np.ndarray) -> int:
    try:
        gray    = to_gray(img_cv).astype(np.float32)
        lap_var = safe_laplacian_var(gray)

        fft        = np.fft.fft2(gray)
        fft_mag    = np.abs(np.fft.fftshift(fft))
        h, w       = fft_mag.shape
        center     = fft_mag[h//4:3*h//4, w//4:3*w//4]
        freq_ratio = center.mean() / (fft_mag.mean() + 1e-6)

        if lap_var < 80:       noise_score = 75
        elif lap_var < 200:    noise_score = 45
        elif lap_var < 2000:   noise_score = 15
        else:                  noise_score = 30

        freq_score = max(0, min(60, int((freq_ratio - 0.5)*50)))
        return min(90, int(noise_score*0.65 + freq_score*0.35))

    except Exception as e:
        print(f"AI-gen error: {e}")
        return 30


# ── Groq Vision ───────────────────────────────────────────────────────

def analyze_with_groq(image_b64: str, filename: str, img_cv: np.ndarray,
                      ela_raw: float, ai_score: int, dct_score: int, noise_score: int) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key=="your_groq_api_key_here":
        return {"risk_score":50,"groq_ok":False,"summary":"Groq API key not set","findings":["Set GROQ_API_KEY in .env"]}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        img_bytes = base64.b64decode(image_b64)
        img_pil   = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h      = img_pil.size

        has_exif = False
        try: has_exif = img_pil._getexif() is not None
        except: pass

        gray    = to_gray(img_cv).astype(np.float32)
        lap_var = round(safe_laplacian_var(gray), 1)
        mean_px = round(float(gray.mean()), 1)
        std_px  = round(float(gray.std()),  1)

        # Color histogram entropy — AI images have unnaturally smooth histograms
        img_arr = np.array(img_pil)
        hist_r  = np.histogram(img_arr[:,:,0], bins=64)[0]
        hist_g  = np.histogram(img_arr[:,:,1], bins=64)[0]
        hist_b  = np.histogram(img_arr[:,:,2], bins=64)[0]
        def entropy(h):
            h = h[h>0].astype(np.float32)
            h /= h.sum()
            return float(-np.sum(h*np.log2(h+1e-10)))
        color_entropy = round((entropy(hist_r)+entropy(hist_g)+entropy(hist_b))/3, 2)

        # Edge density
        edges       = cv2.Canny(img_cv, 50, 150)
        edge_density= round(float(edges.sum())/(edges.shape[0]*edges.shape[1]*255), 4)

        hh, ww   = gray.shape
        quads    = [gray[:hh//2,:ww//2],gray[:hh//2,ww//2:],gray[hh//2:,:ww//2],gray[hh//2:,ww//2:]]
        quad_vars= [round(safe_laplacian_var(q),1) for q in quads]

        prompt = f"""You are a forensic image analyst. Analyze these measurements and determine if the image is authentic, manipulated, or AI-generated.

File: {filename}
Size: {w}x{h}px  |  Has EXIF: {has_exif}
Sharpness (Laplacian variance): {lap_var}
Brightness: mean={mean_px}, std={std_px}
Color histogram entropy: {color_entropy} (real photos: 4.5-5.5, AI images: often <4.0 or >5.8)
Edge density: {edge_density} (real photos: 0.02-0.15)
DCT frequency score: {dct_score}/100 (higher = more AI-like frequency pattern)
Noise pattern score: {noise_score}/100 (higher = more suspicious noise profile)
ELA mean: {ela_raw:.2f} (>8 = strong manipulation signal)
Quadrant variances: {quad_vars} (inconsistency = manipulation)
AI-gen estimate: {ai_score}/100

Reference for real photos:
- Laplacian 200-2000, has EXIF, color entropy 4.5-5.5, edge density 0.03-0.12
- Natural quadrant variance differences (lighting variation is normal)

Reference for AI-generated:
- No EXIF, Laplacian <150, very uniform quadrants, low color entropy
- DCT score >60, noise score >60

Reference for manipulated:
- Has some EXIF but inconsistent, high ELA mean, inconsistent quadrant variances
- Clone regions, timestamp mismatches

Scoring:
- Clearly real photo = 5-25
- Possibly edited but mostly real = 26-45
- Likely manipulated/AI = 46-70
- Clearly fake/AI-generated = 71-99

Return ONLY valid JSON:
{{
  "risk_score": <0-100>,
  "summary": "<one sentence verdict>",
  "findings": ["specific finding 1", "specific finding 2", "specific finding 3"]
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.1, max_tokens=500,
        )
        result            = parse_groq_response(response.choices[0].message.content)
        result["groq_ok"] = True
        print(f"Groq image OK — score: {result['risk_score']} | {result['summary']}")
        return result

    except Exception as e:
        print(f"Groq error: {e}")
        return {"risk_score":50,"groq_ok":False,"summary":"Groq unavailable","findings":[f"Groq error: {str(e)}"]}


# ── Helpers ───────────────────────────────────────────────────────────

def parse_groq_response(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {
                "risk_score": max(0, min(100, int(data.get("risk_score",50)))),
                "summary":    str(data.get("summary","Analysis complete")),
                "findings":   list(data.get("findings",[])),
            }
    except Exception as e:
        print(f"Parse error: {e}")
    return {"risk_score":50,"summary":"Could not parse response","findings":[]}

def get_verdict(fake_score: float) -> tuple:
    if fake_score >= 60:   return "fake",       min(99, int(55+fake_score*0.44))
    elif fake_score >= 35: return "suspicious", min(88, int(45+fake_score*0.70))
    else:                  return "real",       min(99, int(95-fake_score*0.80))

def score_color(value: int) -> str:
    if value >= 60: return "#EF4444"
    if value >= 35: return "#F59E0B"
    return "#22C55E"

def ela_findings_text(ela_score: int, raw_mean: float) -> list:
    if ela_score >= 60: return [f"ELA mean {raw_mean:.2f} — strong manipulation signal","Inconsistent recompression artifacts detected"]
    elif ela_score >= 35: return [f"ELA mean {raw_mean:.2f} — moderate anomaly, possible editing"]
    return [f"ELA mean {raw_mean:.2f} — consistent noise, no edits detected"]

def dct_findings(dct_score: int) -> list:
    if dct_score >= 65: return ["DCT frequency pattern unnaturally smooth — consistent with AI generation"]
    if dct_score >= 40: return ["DCT frequency shows slight uniformity — possible AI or heavy processing"]
    return ["DCT frequency pattern normal — consistent with real camera image"]

def noise_findings(noise_score: int) -> list:
    if noise_score >= 65: return ["Sensor noise pattern absent or synthetic — likely AI-generated or heavily edited"]
    if noise_score >= 40: return ["Noise pattern shows regional inconsistency — possible partial manipulation"]
    return ["Natural camera sensor noise detected — consistent with authentic photo"]