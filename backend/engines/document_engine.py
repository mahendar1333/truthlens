import os, io, re, json, base64, zipfile
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
load_dotenv()


def analyze_document(file_bytes: bytes, filename: str) -> dict:
    try:
        ext = filename.split(".")[-1].lower()
        if ext in ["docx","doc"]:
            return analyze_docx(file_bytes, filename)
        elif ext == "pdf":
            return analyze_pdf(file_bytes, filename)
        else:
            return {"verdict":"error","confidence":0,"findings":[f"Unsupported format: {ext}"],"signals":[],"filename":filename,"engine":"document"}
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"verdict":"error","confidence":0,"error":str(e),"findings":[f"Document engine error: {str(e)}"],"signals":[],"filename":filename,"engine":"document"}


# ── DOCX Deep Analysis ────────────────────────────────────────────────

def analyze_docx(file_bytes: bytes, filename: str) -> dict:
    text_content   = ""
    metadata       = {}
    findings       = []
    font_names     = set()
    font_sizes     = set()
    revision_count = 0
    image_count    = 0
    para_count     = 0
    style_issues   = []

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            file_list = z.namelist()

            if "word/document.xml" in file_list:
                with z.open("word/document.xml") as f:
                    content_str = f.read().decode("utf-8", errors="ignore")
                    tree = ET.fromstring(content_str)
                    ns   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

                    texts = [t.text for t in tree.iter(f"{{{ns}}}t") if t.text]
                    text_content = " ".join(texts)
                    para_count   = len(list(tree.iter(f"{{{ns}}}p")))

                    # Deep font analysis — every run
                    for rpr in tree.iter(f"{{{ns}}}rPr"):
                        fonts_el = rpr.find(f"{{{ns}}}rFonts")
                        if fonts_el is not None:
                            for attr in fonts_el.attrib.values():
                                font_names.add(attr)
                        sz_el = rpr.find(f"{{{ns}}}sz")
                        if sz_el is not None:
                            val = sz_el.attrib.get(f"{{{ns}}}val","")
                            if val: font_sizes.add(val)

                    # Check for revision marks (tracked changes)
                    revision_count = content_str.count("<w:ins ") + content_str.count("<w:del ")

                    # Check for suspicious formatting patterns
                    run_count = len(list(tree.iter(f"{{{ns}}}r")))
                    if para_count > 0 and run_count/para_count > 20:
                        style_issues.append("Unusually high run-to-paragraph ratio — possible copy-paste from multiple sources")

            if "docProps/core.xml" in file_list:
                with z.open("docProps/core.xml") as f:
                    for child in ET.parse(f).getroot():
                        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        metadata[tag] = child.text

            if "docProps/app.xml" in file_list:
                with z.open("docProps/app.xml") as f:
                    for child in ET.parse(f).getroot():
                        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        metadata[f"app_{tag}"] = child.text

            image_count = sum(1 for fn in file_list if fn.startswith("word/media/"))

    except zipfile.BadZipFile:
        findings.append("File is not a valid DOCX — possibly corrupted or renamed")
        return _build_error_result("suspicious", 65, findings, filename)
    except Exception as e:
        findings.append(f"DOCX parsing warning: {str(e)}")

    # ── Score each signal ──

    # Font consistency score
    font_score = 0
    if len(font_names) > 6:
        font_score = min(90, len(font_names)*10)
        findings.append(f"HIGH RISK: {len(font_names)} different font families — text likely pasted from multiple sources")
    elif len(font_names) > 3:
        font_score = 40
        findings.append(f"Multiple font families ({len(font_names)}): {', '.join(list(font_names)[:4])}")
    elif font_names:
        findings.append(f"Font families: {', '.join(font_names)}")
    else:
        findings.append("No font metadata found")

    # Font size inconsistency
    size_score = 0
    if len(font_sizes) > 8:
        size_score = 50
        findings.append(f"Many font sizes detected ({len(font_sizes)}) — inconsistent formatting")

    # Metadata analysis
    meta_score = 0
    creator    = metadata.get("creator","")
    modifier   = metadata.get("lastModifiedBy","")
    created    = metadata.get("created","")
    modified   = metadata.get("modified","")
    app_name   = metadata.get("app_Application","")
    revision   = metadata.get("app_Revision","0")

    if creator:
        findings.append(f"Author: {creator}")
        # Check for generic/suspicious author names
        suspicious_names = ["admin","user","test","unknown","windows user","microsoft","owner"]
        if any(n in creator.lower() for n in suspicious_names):
            meta_score += 30
            findings.append(f"Suspicious author name: '{creator}'")
    else:
        findings.append("No author metadata — possibly stripped to hide origin")
        meta_score += 25

    if modifier and creator and modifier.strip() != creator.strip():
        findings.append(f"Last modified by different person: {modifier}")
        meta_score += 20

    if app_name:
        findings.append(f"Created with: {app_name}")
        # Check for unexpected software
        if any(x in app_name.lower() for x in ["online","web","google","libreoffice"]):
            meta_score += 10
            findings.append(f"Note: Created with {app_name} — not typical for formal documents")

    if created and modified:
        findings.append(f"Created: {created[:10]} | Modified: {modified[:10]}")

    try:
        rev_num = int(revision)
        if rev_num == 1:
            meta_score += 20
            findings.append("Document has only 1 revision — possibly created fresh rather than evolved naturally")
        elif rev_num > 50:
            findings.append(f"Document has {rev_num} revisions — heavily edited over time")
    except:
        pass

    # Revision tracking score
    revision_score = 0
    if revision_count > 5:
        revision_score = min(75, revision_count*8)
        findings.append(f"Tracked changes detected: {revision_count} revision marks — document was edited")
    elif revision_count > 0:
        findings.append(f"{revision_count} tracked change(s) found")

    # Style issues
    for issue in style_issues:
        findings.append(issue)
        meta_score += 15

    # Content analysis
    text_score = 0
    word_count = 0
    if text_content:
        word_count = len(text_content.split())
        findings.append(f"Document contains {word_count} words across {para_count} paragraphs")

        # Check for placeholder text
        placeholders = ["lorem ipsum","click here","your name","insert","placeholder","sample text","[name]","[date]","[company]"]
        hits = [p for p in placeholders if p.lower() in text_content.lower()]
        if hits:
            text_score = min(60, len(hits)*20)
            findings.append(f"Placeholder/template text found: {', '.join(hits)}")

        # Check for date inconsistencies in text
        import re as re2
        years = re2.findall(r'\b(19|20)\d{2}\b', text_content)
        if years:
            year_set = set(int(y) for y in years)
            if max(year_set) - min(year_set) > 10:
                text_score += 15
                findings.append(f"Wide year range in document ({min(year_set)}-{max(year_set)}) — check for inconsistencies")

    if image_count > 0:
        findings.append(f"{image_count} embedded image(s) found")

    # Groq deep analysis
    groq_result = analyze_doc_with_groq(text_content, metadata, filename, len(font_names), revision_count, word_count)
    groq_score  = groq_result["risk_score"]
    groq_ok     = groq_result["groq_ok"]

    signals = [
        {"name":"Groq AI doc scan",    "value":groq_score,    "color":score_color(groq_score)},
        {"name":"Font inconsistency",  "value":font_score,    "color":score_color(font_score)},
        {"name":"Metadata integrity",  "value":meta_score,    "color":score_color(meta_score)},
        {"name":"Revision marks",      "value":revision_score,"color":score_color(revision_score)},
        {"name":"Content anomaly",     "value":text_score,    "color":score_color(text_score)},
    ]

    if groq_ok:
        fake_score = (groq_score*0.45 + font_score*0.20 + meta_score*0.15 + revision_score*0.10 + text_score*0.10)
    else:
        fake_score = (font_score*0.35 + meta_score*0.30 + revision_score*0.20 + text_score*0.15)

    verdict, confidence = get_verdict(fake_score)

    return {
        "verdict":     verdict,
        "confidence":  confidence,
        "fake_score":  round(fake_score, 1),
        "signals":     signals,
        "findings":    [f for f in groq_result["findings"]+findings if f],
        "heatmap_b64": None,
        "filename":    filename,
        "engine":      "document",
        "ai_summary":  groq_result["summary"],
        "groq_active": groq_ok,
        "word_count":  word_count,
    }


# ── PDF Analysis ──────────────────────────────────────────────────────

def analyze_pdf(file_bytes: bytes, filename: str) -> dict:
    findings = []
    metadata = {}
    pdf_score = 0

    # Try PyMuPDF first for deep analysis
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        page_count = doc.page_count
        findings.append(f"PDF has {page_count} page(s)")

        # Extract metadata
        meta = doc.metadata
        if meta:
            if meta.get("author"):
                metadata["author"] = meta["author"]
                findings.append(f"Author: {meta['author']}")
            if meta.get("creator"):
                metadata["creator"] = meta["creator"]
                findings.append(f"Created with: {meta['creator']}")
            if meta.get("producer"):
                metadata["producer"] = meta["producer"]
            if meta.get("creationDate") and meta.get("modDate"):
                findings.append(f"Created: {meta['creationDate'][:10]} | Modified: {meta['modDate'][:10]}")
                if meta["creationDate"] != meta["modDate"]:
                    pdf_score += 15
                    findings.append("Creation and modification dates differ")

        # Font analysis across all pages
        all_fonts = set()
        for page in doc:
            for font in page.get_fonts():
                all_fonts.add(font[3])  # font name

        if len(all_fonts) > 8:
            pdf_score += 40
            findings.append(f"Many different fonts ({len(all_fonts)}) — possible content from multiple sources")
        else:
            findings.append(f"Fonts used: {len(all_fonts)}")

        # Check for JavaScript
        if "/JavaScript" in str(file_bytes[:5000]):
            pdf_score += 50
            findings.append("WARNING: JavaScript detected in PDF — potentially malicious")

        # Check for form fields
        for page in doc:
            widgets = page.widgets()
            if widgets:
                findings.append(f"Interactive form fields found — document may be a template")
                pdf_score += 10
                break

        doc.close()

    except ImportError:
        # Fallback to raw bytes parsing if PyMuPDF not installed
        findings.append("Note: Install pymupdf for deeper PDF analysis")
        content = file_bytes.decode("latin-1", errors="ignore")

        for field, pattern in [("Author","/Author\\s*\\(([^)]+)\\)"),("Creator","/Creator\\s*\\(([^)]+)\\)"),("Producer","/Producer\\s*\\(([^)]+)\\)")]:
            match = re.search(pattern, content)
            if match:
                metadata[field.lower()] = match.group(1)
                findings.append(f"{field}: {match.group(1)}")

        if "/JavaScript" in content or "/JS " in content:
            pdf_score += 50
            findings.append("WARNING: JavaScript detected in PDF")

    except Exception as e:
        findings.append(f"PDF parsing note: {str(e)}")

    groq_result = analyze_doc_with_groq(
        f"PDF document: {filename}\nMetadata: {json.dumps(metadata)}",
        metadata, filename, 0, 0, 0
    )
    groq_score = groq_result["risk_score"]
    groq_ok    = groq_result["groq_ok"]
    fake_score = groq_score*0.6 + pdf_score*0.4

    verdict, confidence = get_verdict(fake_score)
    signals = [
        {"name":"Groq AI scan",       "value":groq_score, "color":score_color(groq_score)},
        {"name":"Structure analysis", "value":pdf_score,  "color":score_color(pdf_score)},
        {"name":"Metadata check",     "value":min(100,pdf_score+20), "color":score_color(pdf_score)},
    ]

    return {
        "verdict":     verdict,
        "confidence":  confidence,
        "fake_score":  round(fake_score,1),
        "signals":     signals,
        "findings":    [f for f in groq_result["findings"]+findings if f],
        "heatmap_b64": None,
        "filename":    filename,
        "engine":      "document",
        "ai_summary":  groq_result["summary"],
        "groq_active": groq_ok,
    }


# ── Groq Document Analysis ────────────────────────────────────────────

def analyze_doc_with_groq(text: str, metadata: dict, filename: str, font_count: int, revision_count: int, word_count: int) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key=="your_groq_api_key_here":
        return {"risk_score":50,"groq_ok":False,"summary":"Groq API key not set","findings":["Set GROQ_API_KEY in .env"]}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        # Send more content to Groq for better analysis
        text_sample = text[:6000] if len(text) > 6000 else text

        prompt = f"""You are a forensic document examiner. Analyze this document for signs of forgery, fabrication, or suspicious content.

Filename: {filename}
Word count: {word_count}
Font families used: {font_count}
Tracked revision marks: {revision_count}
Metadata: {json.dumps(metadata, indent=2)}

Document content (first 6000 chars):
\"\"\"{text_sample}\"\"\"

Step by step analysis — check each of these:

1. AUTHOR CREDIBILITY: Does the stated author match the expertise shown in the content?
2. CONTENT CONSISTENCY: Are dates, names, facts internally consistent throughout?
3. LANGUAGE PATTERNS: Does the writing style suggest a single author or multiple?
4. CREDENTIAL CLAIMS: If this is a resume/CV, are the experience claims realistic?
5. TEMPORAL LOGIC: Do the dates and timeline make sense?
6. FORMATTING ANOMALIES: Are there signs of copy-paste from different sources?

Scoring guide:
- Legitimate authentic document = 5-25
- Minor inconsistencies but likely real = 26-45
- Suspicious — needs verification = 46-65
- Likely forged or significantly fabricated = 66-85
- Clear forgery = 86-99

Return ONLY valid JSON:
{{
  "risk_score": <0-100>,
  "summary": "<one sentence verdict>",
  "findings": ["specific finding 1", "specific finding 2", "specific finding 3", "specific finding 4"]
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.1, max_tokens=500,
        )
        result            = parse_groq_response(response.choices[0].message.content)
        result["groq_ok"] = True
        print(f"Groq doc OK — score: {result['risk_score']} | {result['summary']}")
        return result

    except Exception as e:
        print(f"Groq doc error: {e}")
        return {"risk_score":50,"groq_ok":False,"summary":"Groq unavailable","findings":[f"Groq error: {str(e)}"]}


# ── Helpers ───────────────────────────────────────────────────────────

def _build_error_result(verdict, fake_score, findings, filename):
    return {"verdict":verdict,"confidence":60,"fake_score":fake_score,"signals":[],"findings":findings,"heatmap_b64":None,"filename":filename,"engine":"document","ai_summary":"","groq_active":False}

def parse_groq_response(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {"risk_score":max(0,min(100,int(data.get("risk_score",50)))),"summary":str(data.get("summary","Analysis complete")),"findings":list(data.get("findings",[]))}
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