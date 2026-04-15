import os, re, json
from dotenv import load_dotenv
load_dotenv()


def analyze_text(text: str) -> dict:
    try:
        if not text or len(text.strip()) < 20:
            return {"verdict":"error","confidence":0,"findings":["Text too short — minimum 20 characters"],"signals":[],"engine":"text"}

        emotion_score  = analyze_emotional_manipulation(text)
        ai_text_score  = analyze_ai_generated_text(text)
        credibility    = analyze_credibility_signals(text)
        entity_score   = analyze_entity_consistency(text)
        structure_score= analyze_structure(text)

        groq_result = analyze_with_groq(text, emotion_score, ai_text_score, credibility, entity_score)
        groq_score  = groq_result["risk_score"]
        groq_ok     = groq_result["groq_ok"]

        signals = [
            {"name":"Groq AI fact-check",      "value":groq_score,    "color":score_color(groq_score)},
            {"name":"Emotional manipulation",   "value":emotion_score, "color":score_color(emotion_score)},
            {"name":"AI-text detection",        "value":ai_text_score, "color":score_color(ai_text_score)},
            {"name":"Source credibility",       "value":100-credibility,"color":score_color(100-credibility)},
            {"name":"Entity consistency",       "value":entity_score,  "color":score_color(entity_score)},
        ]

        if groq_ok:
            fake_score = (groq_score*0.50 + emotion_score*0.20 + ai_text_score*0.10 + (100-credibility)*0.10 + entity_score*0.10)
        else:
            fake_score = (emotion_score*0.35 + (100-credibility)*0.30 + ai_text_score*0.20 + entity_score*0.15)

        verdict, confidence = get_verdict(fake_score)

        findings = groq_result["findings"] + get_text_findings(emotion_score, ai_text_score, credibility, entity_score, structure_score)

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


# ── Emotional Manipulation ────────────────────────────────────────────

def analyze_emotional_manipulation(text: str) -> int:
    text_lower = text.lower()
    score      = 0

    # Urgency and fear triggers
    urgency = ["breaking","urgent","alert","warning","must see","before it's deleted",
               "share immediately","act now","time is running out","they don't want you to know",
               "banned","censored","suppressed","cover-up","they're hiding"]
    urgency_hits = sum(1 for w in urgency if w in text_lower)
    score += min(40, urgency_hits * 12)

    # Conspiracy language
    conspiracy = ["big pharma","deep state","new world order","mainstream media refuses",
                  "wake up","sheeple","globalist","they want you","government is lying",
                  "plandemic","scamdemic","fake news media","controlled opposition"]
    conspiracy_hits = sum(1 for w in conspiracy if w in text_lower)
    score += min(40, conspiracy_hits * 15)

    # Extreme capitalization (shouting)
    words     = text.split()
    caps_ratio= sum(1 for w in words if w.isupper() and len(w)>2) / max(len(words),1)
    if caps_ratio > 0.15: score += 25
    elif caps_ratio > 0.08: score += 12

    # Excessive punctuation
    exclaim_ratio = text.count("!") / max(len(text)/100, 1)
    if exclaim_ratio > 3: score += 20
    elif exclaim_ratio > 1.5: score += 10

    # Absolute claims
    absolutes = ["100%","proven","guaranteed","confirmed","definitive proof",
                 "nobody is talking about","what they don't want","impossible to deny"]
    abs_hits = sum(1 for w in absolutes if w in text_lower)
    score += min(20, abs_hits * 10)

    return min(100, score)


# ── AI-Text Detection ─────────────────────────────────────────────────

def analyze_ai_generated_text(text: str) -> int:
    """
    Improved AI text detection using multiple signals:
    - Sentence length uniformity (AI = very uniform)
    - Vocabulary diversity (AI = sometimes repetitive)
    - Transition word overuse (AI loves "furthermore", "moreover")
    - Passive voice ratio
    - Personal pronoun absence
    """
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10]
    if len(sentences) < 3:
        return 20

    score = 0

    # Sentence length uniformity
    lengths  = [len(s.split()) for s in sentences]
    mean_len = sum(lengths)/len(lengths)
    if mean_len > 0:
        cv = (sum((l-mean_len)**2 for l in lengths)/len(lengths))**0.5 / mean_len
        if cv < 0.15:   score += 40  # very uniform = AI
        elif cv < 0.25: score += 20
        elif cv < 0.35: score += 10

    # AI transition words overuse
    ai_transitions = ["furthermore","moreover","additionally","in conclusion","it is important to note",
                      "it is worth noting","in the realm of","it is imperative","one must consider",
                      "in contemporary","paradigmatic","multifaceted","leveraging","delve into",
                      "in essence","to summarize","as previously mentioned","it should be noted"]
    text_lower = text.lower()
    ai_trans_hits = sum(1 for t in ai_transitions if t in text_lower)
    score += min(35, ai_trans_hits * 12)

    # Lack of personal voice
    personal = ["i ","i'm","i've","my ","we ","our ","personally","in my opinion","from my"]
    has_personal = any(p in text_lower for p in personal)
    if not has_personal and len(text) > 200:
        score += 15

    # Vocabulary diversity (type-token ratio)
    words = re.findall(r'\b[a-z]+\b', text_lower)
    if len(words) > 50:
        ttr = len(set(words)) / len(words)
        if ttr < 0.4:    score += 20  # low diversity
        elif ttr < 0.5:  score += 10

    return min(95, score)


# ── Credibility Signals ───────────────────────────────────────────────

def analyze_credibility_signals(text: str) -> int:
    """Higher = more credible. Returns 0-100 credibility score."""
    score      = 30  # base
    text_lower = text.lower()

    # Sources and citations
    source_indicators = ["according to","published in","researchers at","study by",
                         "university of","journal of","dr.","professor","percent",
                         "data shows","statistics","survey of","peer-reviewed","cited"]
    source_hits = sum(1 for s in source_indicators if s in text_lower)
    score += min(40, source_hits * 8)

    # Specific verifiable details
    has_numbers = bool(re.search(r'\d+\.?\d*\s*(%|percent|million|billion)', text_lower))
    has_dates   = bool(re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}', text_lower))
    has_names   = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', text))
    has_org     = bool(re.search(r'\b(university|institute|department|agency|corporation|inc\.|ltd\.)\b', text_lower))

    if has_numbers: score += 10
    if has_dates:   score += 10
    if has_names:   score += 8
    if has_org:     score += 8

    # Anonymous / vague sources (credibility reducers)
    vague = ["sources say","some people","many believe","experts claim","they say",
             "whistleblower","anonymous source","insider","leaked documents","rumor has it"]
    vague_hits = sum(1 for v in vague if v in text_lower)
    score -= min(30, vague_hits * 8)

    return max(0, min(100, score))


# ── Named Entity Consistency ──────────────────────────────────────────

def analyze_entity_consistency(text: str) -> int:
    """
    Check for internal factual consistency using basic NLP.
    Tries spaCy if available, falls back to regex.
    """
    score = 0
    try:
        import spacy
        nlp  = spacy.load("en_core_web_sm")
        doc  = nlp(text[:5000])

        # Check date consistency
        dates = [ent.text for ent in doc.ents if ent.label_=="DATE"]
        years = []
        for d in dates:
            year_match = re.search(r'\b(19|20)\d{2}\b', d)
            if year_match:
                years.append(int(year_match.group()))

        if years and (max(years)-min(years)) > 15:
            score += 25

        # Check for contradictory numbers
        money = [ent.text for ent in doc.ents if ent.label_ in ["MONEY","PERCENT","QUANTITY"]]
        if len(set(money)) > len(money)*0.5 and len(money) > 5:
            score += 15

        # Check for too many unverifiable proper nouns
        proper_nouns = [ent.text for ent in doc.ents if ent.label_ in ["PERSON","ORG","GPE"]]
        unknown_ratio= sum(1 for p in proper_nouns if len(p.split())==1 and p.isupper()) / max(len(proper_nouns),1)
        if unknown_ratio > 0.5:
            score += 20

    except (ImportError, OSError):
        # Fallback without spaCy
        years = [int(y) for y in re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b', text)]
        if years and (max(years)-min(years)) > 15:
            score += 20

        # Too many ALL CAPS proper nouns = potential fake
        caps_words = re.findall(r'\b[A-Z]{3,}\b', text)
        if len(caps_words) > 10:
            score += 15

    return min(80, score)


# ── Text Structure Analysis ───────────────────────────────────────────

def analyze_structure(text: str) -> dict:
    """Returns structural metadata for Groq context."""
    word_count   = len(text.split())
    sentence_count = len(re.split(r'[.!?]+', text))
    avg_sent_len = word_count / max(sentence_count, 1)
    has_headline = bool(re.match(r'^[A-Z\s!:]+$', text[:100].split('\n')[0]))

    return {
        "word_count":     word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_sent_len, 1),
        "has_headline_style":  has_headline,
        "reading_level":       "simple" if avg_sent_len < 12 else "complex" if avg_sent_len > 25 else "normal",
    }


# ── Groq Chain-of-Thought Fact-Check ─────────────────────────────────

def analyze_with_groq(text: str, emotion_score: int, ai_score: int, credibility: int, entity_score: int) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key=="your_groq_api_key_here":
        return {"risk_score":50,"groq_ok":False,"summary":"Groq API key not set","findings":["Set GROQ_API_KEY in .env"]}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        prompt = f"""You are an expert fact-checker and misinformation analyst. Analyze this text carefully.

TEXT TO ANALYZE:
\"\"\"{text[:4000]}\"\"\"

LOCAL ENGINE SCORES (for context):
- Emotional manipulation score: {emotion_score}/100 (higher = more manipulative language)
- AI-generated text score: {ai_score}/100 (higher = more likely AI-written)
- Source credibility score: {credibility}/100 (higher = more credible sources cited)
- Entity consistency score: {entity_score}/100 (higher = more inconsistencies found)

Analyze step by step:

STEP 1 — CLAIM VERIFICATION: What are the main claims? Are they verifiable? Do they contradict known facts?
STEP 2 — SOURCE QUALITY: Are sources named and credible, or vague and anonymous?
STEP 3 — LANGUAGE ANALYSIS: Is the language designed to inform or to provoke/manipulate?
STEP 4 — INTERNAL CONSISTENCY: Do the facts, dates, and figures agree with each other?
STEP 5 — OVERALL VERDICT: Based on all signals, what is the risk score?

Scoring guide:
- Factual, well-sourced content = 5-20
- Mostly accurate with minor issues = 21-40
- Misleading or lacking evidence = 41-65
- Clear misinformation or propaganda = 66-85
- Obvious disinformation = 86-99

Return ONLY valid JSON:
{{
  "risk_score": <0-100>,
  "summary": "<one sentence verdict>",
  "findings": [
    "Claim verification: <what you found>",
    "Source quality: <what you found>",
    "Language: <what you found>",
    "Overall: <key concern or confirmation>"
  ]
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.1, max_tokens=600,
        )
        result            = parse_groq_response(response.choices[0].message.content)
        result["groq_ok"] = True
        print(f"Groq text OK — score: {result['risk_score']} | {result['summary']}")
        return result

    except Exception as e:
        print(f"Groq text error: {e}")
        return {"risk_score":50,"groq_ok":False,"summary":"Groq unavailable","findings":[f"Groq error: {str(e)}"]}


# ── Helpers ───────────────────────────────────────────────────────────

def get_text_findings(emotion: int, ai: int, cred: int, entity: int, structure: dict) -> list:
    findings = []

    if emotion >= 65:   findings.append(f"High emotional manipulation score ({emotion}/100) — heavy use of fear, urgency, and conspiracy language")
    elif emotion >= 35: findings.append(f"Moderate emotional manipulation ({emotion}/100) — some charged language detected")
    else:               findings.append(f"Low emotional manipulation ({emotion}/100) — neutral, measured language")

    if ai >= 65:   findings.append(f"AI-generated text patterns detected ({ai}/100) — unnaturally uniform sentence structure")
    elif ai >= 35: findings.append(f"Possible AI-generated content ({ai}/100) — some formulaic patterns")
    else:          findings.append(f"Writing style appears human ({ai}/100) — natural variation detected")

    if cred >= 65:   findings.append(f"Good credibility signals ({cred}/100) — specific sources, data, and named entities")
    elif cred >= 35: findings.append(f"Mixed credibility ({cred}/100) — some sources cited but verification recommended")
    else:            findings.append(f"Low credibility signals ({cred}/100) — vague sources, anonymous claims")

    if entity >= 40: findings.append(f"Entity inconsistencies detected ({entity}/100) — check dates, names, and figures")

    wc = structure.get("word_count", 0)
    if wc > 0:
        findings.append(f"Text length: {wc} words, reading level: {structure.get('reading_level','normal')}")

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