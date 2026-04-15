import os, re, json
from dotenv import load_dotenv
load_dotenv()


def analyze_text(text: str) -> dict:
    try:
        if not text or len(text.strip()) < 20:
            return {"verdict":"error","confidence":0,"findings":["Text too short — minimum 20 characters"],"signals":[],"engine":"text"}

        emotion_score   = analyze_emotional_manipulation(text)
        ai_text_score   = analyze_ai_generated_text(text)
        credibility     = analyze_credibility_signals(text)
        entity_score    = analyze_entity_consistency(text)
        structure       = analyze_structure(text)

        groq_result = analyze_with_groq(text, emotion_score, ai_text_score, credibility, entity_score)
        groq_score  = groq_result["risk_score"]
        groq_ok     = groq_result["groq_ok"]

        signals = [
            {"name":"Groq AI fact-check",     "value":groq_score,     "color":score_color(groq_score)},
            {"name":"Emotional manipulation",  "value":emotion_score,  "color":score_color(emotion_score)},
            {"name":"AI-text detection",       "value":ai_text_score,  "color":score_color(ai_text_score)},
            {"name":"Source credibility",      "value":100-credibility,"color":score_color(100-credibility)},
            {"name":"Entity consistency",      "value":entity_score,   "color":score_color(entity_score)},
        ]

        if groq_ok:
            fake_score = (groq_score*0.50 + emotion_score*0.20 + ai_text_score*0.10 + (100-credibility)*0.10 + entity_score*0.10)
        else:
            fake_score = (emotion_score*0.35 + (100-credibility)*0.30 + ai_text_score*0.20 + entity_score*0.15)

        verdict, confidence = get_verdict(fake_score)
        findings = groq_result["findings"] + get_text_findings(emotion_score, ai_text_score, credibility, entity_score, structure)

        return {
            "verdict":     verdict,
            "confidence":  confidence,
            "fake_score":  round(fake_score,1),
            "signals":     signals,
            "findings":    [f for f in findings if f],
            "filename":    "text analysis",
            "engine":      "text",
            "ai_summary":  groq_result["summary"],
            "groq_active": groq_ok,
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"verdict":"error","confidence":0,"error":str(e),"findings":[f"Text engine error: {str(e)}"],"signals":[],"engine":"text"}


def analyze_emotional_manipulation(text: str) -> int:
    text_lower = text.lower()
    score = 0

    urgency = ["breaking","urgent","alert","warning","must see","before it's deleted",
               "share immediately","act now","they don't want you to know","banned",
               "censored","suppressed","cover-up","they're hiding","wake up"]
    score += min(40, sum(1 for w in urgency if w in text_lower) * 12)

    conspiracy = ["big pharma","deep state","mainstream media refuses","wake up",
                  "government is lying","plandemic","fake news media","they want you",
                  "controlled opposition","globalist","new world order"]
    score += min(40, sum(1 for w in conspiracy if w in text_lower) * 15)

    words = text.split()
    caps_ratio = sum(1 for w in words if w.isupper() and len(w)>2) / max(len(words),1)
    if caps_ratio > 0.15:   score += 25
    elif caps_ratio > 0.08: score += 12

    exclaim = text.count("!") / max(len(text)/100, 1)
    if exclaim > 3:   score += 20
    elif exclaim > 1.5: score += 10

    absolutes = ["100%","proven","guaranteed","confirmed","definitive proof",
                 "nobody is talking about","impossible to deny"]
    score += min(20, sum(1 for w in absolutes if w in text_lower) * 10)

    return min(100, score)


def analyze_ai_generated_text(text: str) -> int:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10]
    if len(sentences) < 3:
        return 20

    score = 0

    lengths  = [len(s.split()) for s in sentences]
    mean_len = sum(lengths)/len(lengths)
    if mean_len > 0:
        variance = sum((l-mean_len)**2 for l in lengths)/len(lengths)
        cv = variance**0.5 / mean_len
        if cv < 0.15:   score += 40
        elif cv < 0.25: score += 20
        elif cv < 0.35: score += 10

    ai_transitions = ["furthermore","moreover","additionally","in conclusion",
                      "it is important to note","it is worth noting","in the realm of",
                      "it is imperative","one must consider","in contemporary",
                      "paradigmatic","multifaceted","leveraging","delve into",
                      "to summarize","as previously mentioned","it should be noted"]
    text_lower = text.lower()
    score += min(35, sum(1 for t in ai_transitions if t in text_lower) * 12)

    personal = ["i ","i'm","i've","my ","we ","our ","personally","in my opinion"]
    if not any(p in text_lower for p in personal) and len(text) > 200:
        score += 15

    words = re.findall(r'\b[a-z]+\b', text_lower)
    if len(words) > 50:
        ttr = len(set(words)) / len(words)
        if ttr < 0.4:   score += 20
        elif ttr < 0.5: score += 10

    return min(95, score)


def analyze_credibility_signals(text: str) -> int:
    score      = 30
    text_lower = text.lower()

    source_indicators = ["according to","published in","researchers at","study by",
                         "university of","journal of","dr.","professor","percent",
                         "data shows","statistics","survey of","peer-reviewed"]
    score += min(40, sum(1 for s in source_indicators if s in text_lower) * 8)

    if re.search(r'\d+\.?\d*\s*(%|percent|million|billion)', text_lower): score += 10
    if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}', text_lower): score += 10
    if re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', text): score += 8

    vague = ["sources say","some people","many believe","experts claim","they say",
             "whistleblower","anonymous source","insider","rumor has it"]
    score -= min(30, sum(1 for v in vague if v in text_lower) * 8)

    return max(0, min(100, score))


def analyze_entity_consistency(text: str) -> int:
    score = 0

    years = [int(y) for y in re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b', text)]
    if years and (max(years)-min(years)) > 15:
        score += 20

    caps_words = re.findall(r'\b[A-Z]{3,}\b', text)
    if len(caps_words) > 10:
        score += 15

    numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', text)
    if len(numbers) > 8:
        score += 10

    return min(80, score)


def analyze_structure(text: str) -> dict:
    word_count     = len(text.split())
    sentence_count = len(re.split(r'[.!?]+', text))
    avg_sent_len   = word_count / max(sentence_count, 1)
    return {
        "word_count":          word_count,
        "sentence_count":      sentence_count,
        "avg_sentence_length": round(avg_sent_len, 1),
        "reading_level":       "simple" if avg_sent_len < 12 else "complex" if avg_sent_len > 25 else "normal",
    }


def analyze_with_groq(text: str, emotion_score: int, ai_score: int, credibility: int, entity_score: int) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key=="your_groq_api_key_here":
        return {"risk_score":50,"groq_ok":False,"summary":"Groq API key not set","findings":["Set GROQ_API_KEY in environment"]}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        prompt = f"""You are an expert fact-checker. Analyze this text for misinformation, manipulation, or AI generation.

TEXT:
\"\"\"{text[:4000]}\"\"\"

LOCAL SCORES (context):
- Emotional manipulation: {emotion_score}/100
- AI-generated text: {ai_score}/100
- Source credibility: {credibility}/100
- Entity consistency: {entity_score}/100

Step by step:
1. CLAIMS: Are the main claims verifiable? Do they contradict known facts?
2. SOURCES: Are sources named and credible, or vague and anonymous?
3. LANGUAGE: Designed to inform or to provoke/manipulate?
4. CONSISTENCY: Do facts, dates, figures agree internally?

Scoring:
- Factual, well-sourced = 5-20
- Mostly accurate, minor issues = 21-40
- Misleading or lacking evidence = 41-65
- Clear misinformation = 66-85
- Obvious disinformation = 86-99

Return ONLY valid JSON:
{{
  "risk_score": <0-100>,
  "summary": "<one sentence>",
  "findings": ["finding 1", "finding 2", "finding 3", "finding 4"]
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.1, max_tokens=500,
        )
        result            = parse_groq_response(response.choices[0].message.content)
        result["groq_ok"] = True
        print(f"Groq text OK — score: {result['risk_score']} | {result['summary']}")
        return result

    except Exception as e:
        print(f"Groq text error: {e}")
        return {"risk_score":50,"groq_ok":False,"summary":"Groq unavailable","findings":[f"Groq error: {str(e)}"]}


def get_text_findings(emotion, ai, cred, entity, structure) -> list:
    findings = []
    if emotion >= 65:   findings.append(f"High emotional manipulation ({emotion}/100) — heavy use of fear and urgency language")
    elif emotion >= 35: findings.append(f"Moderate emotional manipulation ({emotion}/100) — some charged language")
    else:               findings.append(f"Low emotional manipulation ({emotion}/100) — neutral, measured tone")

    if ai >= 65:   findings.append(f"AI-generated patterns detected ({ai}/100) — uniform sentence structure")
    elif ai >= 35: findings.append(f"Possible AI content ({ai}/100) — some formulaic patterns")
    else:          findings.append(f"Human writing style ({ai}/100) — natural variation detected")

    if cred >= 65:   findings.append(f"Good credibility ({cred}/100) — specific sources and data cited")
    elif cred >= 35: findings.append(f"Mixed credibility ({cred}/100) — some sources cited")
    else:            findings.append(f"Low credibility ({cred}/100) — vague or anonymous sources")

    wc = structure.get("word_count",0)
    if wc: findings.append(f"Text: {wc} words, reading level: {structure.get('reading_level','normal')}")
    return findings


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