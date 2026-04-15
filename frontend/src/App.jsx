import { useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

const AUTHOR = {
  name:     "Mahendar Reddy Lakkireddy",
  linkedin: "https://www.linkedin.com/in/mahendar-reddy-lakkireddy-8576792b9/",
};

const T = {
  bg:"#020617", bg2:"#0C1A2E", bg3:"#0F1E35", nav:"#010B14",
  border:"#1E3A5F", border2:"#0E2440",
  accent:"#0891B2", accentL:"#06B6D4", accentX:"#22D3EE",
  text:"#F8FAFC", text2:"#CBD5E1", text3:"#64748B", text4:"#475569",
};

const VS = {
  fake:       { bg:"#1A0A0A", border:"#7F1D1D", color:"#FCA5A5", icon:"✕", label:"Fake / Manipulated", dot:"#EF4444" },
  suspicious: { bg:"#1A1200", border:"#78350F", color:"#FCD34D", icon:"?", label:"Suspicious",          dot:"#F59E0B" },
  real:       { bg:"#021A0A", border:"#14532D", color:"#86EFAC", icon:"✓", label:"Authentic",           dot:"#22C55E" },
  error:      { bg:"#0F172A", border:"#1E293B", color:"#94A3B8", icon:"!", label:"Error",               dot:"#64748B" },
};

// Full-width section wrapper
const Section = ({ bg, children, id, style }) => (
  <div id={id} style={{ width:"100vw", marginLeft:"calc(-50vw + 50%)", background:bg, ...style }}>
    <div style={{ maxWidth:1280, margin:"0 auto", padding:"96px 60px" }}>
      {children}
    </div>
  </div>
);

export default function App() {
  const [page, setPage]       = useState("home");
  const [file, setFile]       = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProg]   = useState(0);
  const [step, setStep]       = useState("");
  const [textIn, setTextIn]   = useState("");
  const [textRes, setTextRes] = useState(null);
  const [textLoad, setTLoad]  = useState(false);
  const [history, setHistory] = useState([]);
  const [stats, setStats]     = useState({ total:0, fake:0, real:0 });
  const [scanTab, setScanTab] = useState("file");

  const STEPS = ["Reading file...","Running ELA forensics...","Checking metadata...","Clone detection...","Groq AI analysis...","Compiling verdict..."];

  function getEngine(f) {
    if (!f) return "auto";
    const e = f.split(".").pop().toLowerCase();
    if (["jpg","jpeg","png","gif","webp","bmp"].includes(e)) return "image";
    if (["mp4","mov","avi","webm","mkv"].includes(e)) return "video";
    if (["pdf","doc","docx"].includes(e)) return "document";
    return "image";
  }

  function resetAll() {
    setResult(null); setFile(null); setPreview(null);
    setTextRes(null); setProg(0); setStep(""); setTextIn("");
  }
  function goHome() { resetAll(); setPage("home"); }
  function goScan() { resetAll(); setScanTab("file"); setPage("scan"); }

  function onFile(f) {
    if (!f) return;
    setFile(f); setResult(null); setProg(0); setStep("");
    if (f.type.startsWith("image/")) setPreview(URL.createObjectURL(f));
    else setPreview(null);
  }

  async function analyze() {
    if (!file) return;
    setLoading(true); setResult(null); setProg(0);
    let i = 0;
    const iv = setInterval(() => {
      i++; setProg(Math.round((i/STEPS.length)*85));
      setStep(STEPS[Math.min(i, STEPS.length-1)]);
      if (i >= STEPS.length-1) clearInterval(iv);
    }, 600);
    try {
      const form = new FormData(); form.append("file", file);
      const { data } = await axios.post(`${API}/analyze/auto`, form, { timeout:90000 });
      clearInterval(iv); setProg(100); setStep("Done!");
      setTimeout(() => { setResult(data); setLoading(false); updateStats(data); }, 300);
    } catch (err) {
      clearInterval(iv); setLoading(false);
      const msg = err.response?.data?.detail || err.message;
      setResult({ verdict:"error", confidence:0, findings:[`Error: ${msg}`], signals:[], filename:file?.name, engine:getEngine(file?.name||"") });
    }
  }

  async function analyzeText() {
    if (!textIn.trim()) return;
    setTLoad(true); setTextRes(null);
    try {
      const form = new FormData(); form.append("text", textIn);
      const { data } = await axios.post(`${API}/analyze/text`, form, { timeout:30000 });
      setTextRes(data); updateStats(data);
    } catch (err) {
      setTextRes({ verdict:"error", confidence:0, findings:[err.message], signals:[] });
    }
    setTLoad(false);
  }

  function updateStats(data) {
    if (!data?.verdict || data.verdict==="error") return;
    setStats(s => ({ total:s.total+1, fake:s.fake+(data.verdict!=="real"?1:0), real:s.real+(data.verdict==="real"?1:0) }));
    setHistory(h => [{ name:data.filename||"scan", verdict:data.verdict, conf:data.confidence||0, engine:data.engine||"auto", time:new Date().toLocaleTimeString() },...h.slice(0,19)]);
  }

  // ── Navbar: always 100vw ──
  const Navbar = ({ children }) => (
    <nav style={{
      position:"sticky", top:0, zIndex:100,
      width:"100vw", marginLeft:"calc(-50vw + 50%)",
      background:T.nav, height:64,
      display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"0 60px",
      borderBottom:`1px solid ${T.border}`,
    }}>
      <div style={{ display:"flex", alignItems:"center", gap:12, cursor:"pointer" }} onClick={goHome}>
        <div style={{ width:38, height:38, background:T.accent, borderRadius:9, display:"flex", alignItems:"center", justifyContent:"center", fontSize:13, fontWeight:900, color:"#fff" }}>TL</div>
        <span style={{ fontSize:18, fontWeight:800, color:"#fff", letterSpacing:"-0.5px" }}>TruthLens</span>
        <span style={{ fontSize:9, background:T.bg2, color:T.accentX, padding:"3px 8px", borderRadius:4, border:`1px solid ${T.border}`, fontWeight:700, letterSpacing:".07em" }}>FORENSICS</span>
      </div>
      {children}
    </nav>
  );

  /* ════════════ HOME PAGE ════════════ */
  if (page === "home") return (
    <div style={{ fontFamily:"-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif", background:T.bg, color:T.text, overflowX:"hidden" }}>

      <Navbar>
        <div style={{ display:"flex", gap:36 }}>
          {[["How it works","#howitworks"],["Features","#features"],["Use cases","#usecases"]].map(([l,h])=>(
            <a key={h} href={h} style={{ fontSize:14, color:"#94A3B8", textDecoration:"none", fontWeight:500, transition:"color .15s" }}
              onMouseEnter={e=>e.target.style.color=T.accentL}
              onMouseLeave={e=>e.target.style.color="#94A3B8"}>{l}</a>
          ))}
        </div>
        <button onClick={goScan} style={{ padding:"10px 26px", background:T.accent, color:"#fff", border:"none", borderRadius:8, fontSize:14, fontWeight:700, cursor:"pointer" }}>
          Try TruthLens →
        </button>
      </Navbar>

      {/* ── HERO — left aligned, full bleed ── */}
      <div style={{ width:"100vw", marginLeft:"calc(-50vw + 50%)", background:T.bg, borderBottom:`1px solid ${T.border2}` }}>
        <div style={{ maxWidth:1280, margin:"0 auto", padding:"110px 60px 100px" }}>
          <div style={{ display:"inline-flex", alignItems:"center", gap:8, background:T.bg2, border:`1px solid ${T.border}`, borderRadius:24, padding:"6px 20px", fontSize:12, color:T.accentX, fontWeight:600, marginBottom:32, letterSpacing:".03em" }}>
            <span style={{ width:7, height:7, borderRadius:"50%", background:"#10B981", display:"inline-block" }}></span>
            Powered by Groq AI · 4 detection engines · Free to use
          </div>
          {/* Left-aligned two-column layout */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:80, alignItems:"center" }}>
            <div>
              <h1 style={{ fontSize:"clamp(44px,5vw,72px)", fontWeight:900, color:"#fff", letterSpacing:"-3px", lineHeight:1.05, margin:"0 0 24px" }}>
                Is it real<br/>or <span style={{ color:T.accentL, fontStyle:"italic" }}>fake?</span><br/>
                <span style={{ fontSize:"clamp(36px,4vw,58px)" }}>Find out in seconds.</span>
              </h1>
              <p style={{ fontSize:18, color:"#94A3B8", lineHeight:1.8, maxWidth:480, margin:"0 0 40px" }}>
                TruthLens uses AI forensics to detect deepfakes, forged documents, manipulated images, and misinformation — instantly.
              </p>
              <div style={{ display:"flex", gap:14, flexWrap:"wrap" }}>
                <button onClick={goScan} style={{ padding:"16px 36px", background:T.accent, color:"#fff", border:"none", borderRadius:9, fontSize:16, fontWeight:700, cursor:"pointer" }}>
                  Start scanning free →
                </button>
                <a href="#howitworks" style={{ padding:"16px 36px", background:"transparent", color:"#94A3B8", border:`1px solid ${T.border}`, borderRadius:9, fontSize:16, fontWeight:600, textDecoration:"none", display:"inline-flex", alignItems:"center" }}>
                  See how it works
                </a>
              </div>
            </div>
            {/* Right column: stats */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
              {[["800K+","deepfake deaths preventable per year","#fff"],["90%","of fakes show prior warning signs","#fff"],["4","AI detection engines","#06B6D4"],["$0","always free to use","#06B6D4"]].map(([n,l,c])=>(
                <div key={n} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:14, padding:"28px 24px" }}>
                  <div style={{ fontSize:"clamp(28px,3vw,44px)", fontWeight:900, color:c, letterSpacing:"-2px", lineHeight:1, marginBottom:10 }}>{n}</div>
                  <div style={{ fontSize:13, color:"#475569", lineHeight:1.5 }}>{l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── HOW IT WORKS ── */}
      <Section id="howitworks" bg={T.bg2}>
        <div style={{ marginBottom:56 }}>
          <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".14em", marginBottom:12 }}>HOW IT WORKS</div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:48, alignItems:"end" }}>
            <h2 style={{ fontSize:"clamp(28px,4vw,46px)", fontWeight:900, color:"#fff", letterSpacing:"-1.5px", margin:0 }}>One upload.<br/>Full verdict.</h2>
            <p style={{ fontSize:16, color:"#94A3B8", lineHeight:1.75, margin:0 }}>Upload anything suspicious and get a detailed AI forensic report in seconds. No account needed.</p>
          </div>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:24 }}>
          {[
            ["01","Upload your file","Drop any image, video, PDF, or document. TruthLens auto-detects the type and routes to the right engine.",T.accent],
            ["02","AI forensics run","Four engines run simultaneously — ELA pixel forensics, EXIF metadata, clone detection, and Groq AI intelligence.",T.accentL],
            ["03","Get your verdict","Full verdict with confidence score, signal breakdown, key findings, and a downloadable PDF evidence report.",T.accentX],
          ].map(([n,t,d,c])=>(
            <div key={n} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:16, padding:"36px 32px", borderTop:`3px solid ${c}` }}>
              <div style={{ fontSize:40, fontWeight:900, color:c, letterSpacing:"-2px", marginBottom:20, fontStyle:"italic" }}>{n}</div>
              <div style={{ fontSize:18, fontWeight:700, color:"#fff", marginBottom:12 }}>{t}</div>
              <div style={{ fontSize:14, color:"#94A3B8", lineHeight:1.8 }}>{d}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── 4 ENGINES ── */}
      <Section id="features" bg={T.bg}>
        <div style={{ marginBottom:56 }}>
          <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".14em", marginBottom:12 }}>DETECTION ENGINES</div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:48, alignItems:"end" }}>
            <h2 style={{ fontSize:"clamp(28px,4vw,46px)", fontWeight:900, color:"#fff", letterSpacing:"-1.5px", margin:0 }}>4 engines.<br/>Every type of fake.</h2>
            <p style={{ fontSize:16, color:"#94A3B8", lineHeight:1.75, margin:0 }}>Each engine purpose-built for its media type, then enhanced with Groq AI for a combined intelligence verdict.</p>
          </div>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:24 }}>
          {[
            ["Image Forensics",T.accent,"Detects copy-paste manipulation, EXIF tampering, AI-generated images, and pixel anomalies using ELA, DCT frequency analysis, and SPN noise patterns.","ELA · EXIF metadata · Clone detection · DCT · SPN noise · Groq AI"],
            ["Deepfake Video",T.accentL,"Extracts key frames, analyzes face boundary artifacts, blink patterns, temporal consistency, and GAN fingerprints across the full video timeline.","Frame extraction · Face boundaries · Blink analysis · Temporal · Groq AI"],
            ["Document Forgery","#F59E0B","Reads DOCX and PDF structure directly — checks font consistency, metadata timestamps, revision history, and signature anomalies with PyMuPDF.","DOCX/PDF deep parse · Font analysis · Metadata · PyMuPDF · Groq AI"],
            ["Text Fact-Check","#22C55E","Scores emotional manipulation, detects AI text patterns, checks source credibility, extracts named entities with spaCy, and chain-of-thought Groq fact-check.","Emotion scoring · AI-text detect · spaCy NER · Credibility · Groq CoT"],
          ].map(([t,c,d,tech])=>(
            <div key={t} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:16, padding:"36px 32px", borderTop:`3px solid ${c}` }}>
              <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:16 }}>
                <div style={{ width:12, height:12, borderRadius:"50%", background:c }}></div>
                <div style={{ fontSize:19, fontWeight:700, color:"#fff" }}>{t}</div>
              </div>
              <p style={{ fontSize:14, color:"#94A3B8", lineHeight:1.8, marginBottom:20 }}>{d}</p>
              <div style={{ fontSize:12, color:c, background:c+"18", padding:"9px 14px", borderRadius:8, fontWeight:600, border:`1px solid ${c}33` }}>{tech}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── USE CASES ── */}
      <Section id="usecases" bg={T.bg2}>
        <div style={{ marginBottom:56 }}>
          <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".14em", marginBottom:12 }}>WHO USES TRUTHLENS</div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:48, alignItems:"end" }}>
            <h2 style={{ fontSize:"clamp(28px,4vw,46px)", fontWeight:900, color:"#fff", letterSpacing:"-1.5px", margin:0 }}>Built for everyone<br/>who needs the truth.</h2>
            <p style={{ fontSize:16, color:"#94A3B8", lineHeight:1.75, margin:0 }}>From journalists to banks to everyday people — anyone who needs to verify what is real before it spreads.</p>
          </div>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:20 }}>
          {[
            ["Journalists & Fact-checkers","Verify images and videos before publishing. Detect AI-generated photos planted in fake news stories.",T.accent],
            ["Banks & Legal Teams","Detect forged contracts, tampered signatures, and fraudulent documents before they cause financial damage.",T.accentL],
            ["Social Media Users","Before sharing any viral post or video, verify it has not been manipulated — takes under 10 seconds.",T.accentX],
            ["HR & Recruiters","Verify uploaded resume documents and detect falsified credentials and employment records.",T.accent],
            ["Researchers & Students","Detect AI-generated academic content and verify the authenticity of research images and data.",T.accentL],
            ["Anyone","If something looks suspicious — a screenshot, a document, a video — upload it and know instantly.",T.accentX],
          ].map(([t,d,c])=>(
            <div key={t} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:12, padding:"28px 26px", borderLeft:`3px solid ${c}` }}>
              <div style={{ fontSize:16, fontWeight:700, color:"#fff", marginBottom:10 }}>{t}</div>
              <div style={{ fontSize:14, color:"#94A3B8", lineHeight:1.75 }}>{d}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── SAMPLE VERDICTS ── */}
      <Section bg={T.bg}>
        <div style={{ marginBottom:56 }}>
          <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".14em", marginBottom:12 }}>SAMPLE VERDICTS</div>
          <h2 style={{ fontSize:"clamp(28px,4vw,46px)", fontWeight:900, color:"#fff", letterSpacing:"-1.5px", margin:0 }}>See what a real verdict looks like</h2>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:20 }}>
          {[
            { verdict:"fake",       conf:94, file:"profile_photo.jpg",   engine:"image",    score:71, summary:"ELA heatmap shows anomalies in 3 regions. EXIF stripped. 54 clone-stamp regions. DCT frequency unnaturally smooth — AI generated." },
            { verdict:"real",       conf:96, file:"temple_aerial.png",   engine:"image",    score:12, summary:"Consistent noise floor. EXIF intact with GPS. Natural DCT frequency. SPN noise consistent with real camera hardware." },
            { verdict:"suspicious", conf:82, file:"contract_signed.pdf", engine:"document", score:47, summary:"6 font families across pages. Metadata timestamp mismatch. Single revision only — likely assembled from multiple sources." },
          ].map((r,i)=>{
            const vs=VS[r.verdict];
            return (
              <div key={i} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:16, overflow:"hidden" }}>
                <div style={{ padding:"12px 20px", borderBottom:`1px solid ${T.border2}`, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <span style={{ fontSize:12, color:T.text3, fontFamily:"monospace" }}>{r.file}</span>
                  <span style={{ fontSize:11, background:vs.bg, color:vs.color, padding:"3px 10px", borderRadius:5, fontWeight:700, border:`1px solid ${vs.border}` }}>{vs.icon} {vs.label}</span>
                </div>
                <div style={{ padding:"20px" }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:10 }}>
                    <span style={{ fontSize:12, color:T.text3 }}>Confidence</span>
                    <span style={{ fontSize:16, fontWeight:800, color:vs.dot }}>{r.conf}%</span>
                  </div>
                  <div style={{ height:5, background:T.bg2, borderRadius:3, overflow:"hidden", marginBottom:14 }}>
                    <div style={{ height:"100%", width:`${r.conf}%`, background:vs.dot, borderRadius:3 }} />
                  </div>
                  <div style={{ fontSize:12, color:T.text2, marginBottom:10 }}>Risk: <b style={{color:"#F1F5F9"}}>{r.score}/100</b> · {r.engine}</div>
                  <p style={{ fontSize:13, color:T.text3, lineHeight:1.7, margin:0 }}>{r.summary}</p>
                </div>
              </div>
            );
          })}
        </div>
      </Section>

      {/* ── BUILT BY ── */}
      <div style={{ width:"100vw", marginLeft:"calc(-50vw + 50%)", background:T.bg2, borderTop:`1px solid ${T.border2}`, borderBottom:`1px solid ${T.border2}` }}>
        <div style={{ maxWidth:1280, margin:"0 auto", padding:"56px 60px", display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:24 }}>
          <div>
            <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".12em", marginBottom:10 }}>BUILT BY</div>
            <div style={{ fontSize:28, fontWeight:800, color:"#fff", letterSpacing:"-0.5px", marginBottom:8 }}>{AUTHOR.name}</div>
            <div style={{ fontSize:14, color:T.text3 }}>AI Engineering · Full-stack Development · Groq AI</div>
          </div>
          <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer"
            style={{ display:"inline-flex", alignItems:"center", gap:10, background:T.accent, color:"#fff", textDecoration:"none", padding:"14px 28px", borderRadius:9, fontSize:15, fontWeight:700 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg>
            Connect on LinkedIn →
          </a>
        </div>
      </div>

      {/* ── CTA ── */}
      <div style={{ width:"100vw", marginLeft:"calc(-50vw + 50%)", background:T.accent }}>
        <div style={{ maxWidth:1280, margin:"0 auto", padding:"100px 60px", display:"grid", gridTemplateColumns:"1fr 1fr", gap:80, alignItems:"center" }}>
          <div>
            <h2 style={{ fontSize:"clamp(32px,4vw,54px)", fontWeight:900, color:"#fff", letterSpacing:"-2px", margin:"0 0 20px", lineHeight:1.08 }}>Don't share until you verify.</h2>
            <p style={{ fontSize:18, color:"rgba(255,255,255,0.8)", lineHeight:1.75, margin:0 }}>
              Upload any file or paste any text. Full AI forensics verdict in under 10 seconds. Free, forever.
            </p>
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:16, alignItems:"flex-start" }}>
            <button onClick={goScan} style={{ padding:"18px 48px", background:"#fff", color:T.accent, border:"none", borderRadius:9, fontSize:18, fontWeight:800, cursor:"pointer" }}>
              Start scanning now →
            </button>
            <div style={{ fontSize:13, color:"rgba(255,255,255,0.6)" }}>No sign-up required · Works on any device · Results in seconds</div>
          </div>
        </div>
      </div>

      {/* ── FOOTER ── */}
      <div style={{ width:"100vw", marginLeft:"calc(-50vw + 50%)", background:T.nav, borderTop:`1px solid ${T.border}` }}>
        <div style={{ maxWidth:1280, margin:"0 auto", padding:"40px 60px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:20, marginBottom:28 }}>
            <div style={{ display:"flex", alignItems:"center", gap:12 }}>
              <div style={{ width:34, height:34, background:T.accent, borderRadius:7, display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, fontWeight:900, color:"#fff" }}>TL</div>
              <div>
                <div style={{ fontSize:16, fontWeight:700, color:"#fff" }}>TruthLens</div>
                <div style={{ fontSize:12, color:T.text3, marginTop:2 }}>AI Authenticity Detection Platform</div>
              </div>
            </div>
            <div style={{ display:"flex", gap:36 }}>
              {["Image detection","Video deepfakes","Document forgery","Text fact-check"].map(l=>(
                <span key={l} style={{ fontSize:13, color:T.text3, cursor:"pointer" }}
                  onMouseEnter={e=>e.target.style.color=T.accentL}
                  onMouseLeave={e=>e.target.style.color=T.text3}>{l}</span>
              ))}
            </div>
          </div>
          <div style={{ borderTop:`1px solid ${T.border2}`, paddingTop:22, display:"flex", justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:12 }}>
            <div style={{ fontSize:13, color:T.text4 }}>© 2026 TruthLens · AI Authenticity Detection</div>
            <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer"
              style={{ display:"flex", alignItems:"center", gap:7, fontSize:13, fontWeight:600, color:T.accentL, textDecoration:"none" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill={T.accentL}><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12"/><circle cx="4" cy="4" r="2"/></svg>
              Built by {AUTHOR.name}
            </a>
          </div>
        </div>
      </div>
    </div>
  );

  /* ════════════ SCAN PAGE ════════════ */
  return (
    <div style={{ fontFamily:"-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif", background:T.bg2, minHeight:"100vh", overflowX:"hidden" }}>

      <Navbar>
        <div style={{ display:"flex", gap:4 }}>
          {[["file","Scan file"],["text","Fact-check"],["history","History"]].map(([t,l])=>(
            <button key={t} onClick={()=>setScanTab(t)} style={{ padding:"6px 18px", borderRadius:6, border:"none", cursor:"pointer", fontSize:13, fontWeight:scanTab===t?700:400, background:scanTab===t?T.bg2:"transparent", color:scanTab===t?T.accentL:T.text3 }}>{l}</button>
          ))}
        </div>
        <div style={{ display:"flex", gap:24, alignItems:"center" }}>
          {[["Scanned",stats.total,"#F1F5F9"],["Fake",stats.fake,"#F87171"],["Real",stats.real,"#4ADE80"]].map(([l,n,c])=>(
            <div key={l} style={{ textAlign:"center" }}>
              <div style={{ fontSize:17, fontWeight:700, color:c, lineHeight:1 }}>{n}</div>
              <div style={{ fontSize:9, color:T.text4, letterSpacing:".06em" }}>{l.toUpperCase()}</div>
            </div>
          ))}
          <button onClick={goHome} style={{ padding:"6px 16px", background:"transparent", color:T.text3, border:`1px solid ${T.border2}`, borderRadius:7, fontSize:12, cursor:"pointer" }}>← Home</button>
        </div>
      </Navbar>

      <div style={{ maxWidth:960, margin:"0 auto", padding:"36px 40px" }}>

        {scanTab==="file" && (
          <div>
            {(preview||result?.heatmap_b64) && (
              <div style={{ display:"grid", gridTemplateColumns:preview&&result?.heatmap_b64?"1fr 1fr":"1fr", gap:16, marginBottom:20 }}>
                {preview && (
                  <div style={{ background:T.bg3, borderRadius:12, border:`1px solid ${T.border2}`, overflow:"hidden" }}>
                    <div style={{ padding:"10px 18px", borderBottom:`1px solid ${T.border2}`, fontSize:10, fontWeight:700, color:T.text3, letterSpacing:".09em" }}>ORIGINAL</div>
                    <img src={preview} alt="original" style={{ width:"100%", maxHeight:220, objectFit:"contain", display:"block", padding:10 }} />
                  </div>
                )}
                {result?.heatmap_b64 && (
                  <div style={{ background:T.bg3, borderRadius:12, border:`1px solid ${T.border2}`, overflow:"hidden" }}>
                    <div style={{ padding:"10px 18px", borderBottom:`1px solid ${T.border2}`, fontSize:10, fontWeight:700, color:T.text3, letterSpacing:".09em" }}>
                      {result.engine==="video"?"FRAME THUMBNAIL":"ELA HEATMAP"}
                    </div>
                    <img src={`data:image/png;base64,${result.heatmap_b64}`} alt="heatmap" style={{ width:"100%", maxHeight:220, objectFit:"contain", display:"block", padding:10 }} />
                  </div>
                )}
              </div>
            )}

            <div style={{ background:T.bg3, borderRadius:14, border:`1px solid ${T.border2}`, overflow:"hidden", marginBottom:16 }}>
              <div style={{ padding:"14px 22px", borderBottom:`1px solid ${T.border2}`, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <span style={{ fontSize:15, fontWeight:600, color:"#F1F5F9" }}>Upload for analysis</span>
                <span style={{ fontSize:12, color:T.text3 }}>Image · Video · PDF · Document</span>
              </div>
              <label style={{ display:"block", border:`2px dashed ${T.border}`, borderRadius:10, padding:"36px 28px", textAlign:"center", cursor:"pointer", margin:18, background:T.bg2, transition:"all .15s" }}
                onDragOver={e=>{e.preventDefault();e.currentTarget.style.borderColor=T.accentL;}}
                onDragLeave={e=>{e.currentTarget.style.borderColor=T.border;}}
                onDrop={e=>{e.preventDefault();e.currentTarget.style.borderColor=T.border;onFile(e.dataTransfer.files[0]);}}>
                <input type="file" accept="image/*,video/*,.pdf,.doc,.docx" style={{ display:"none" }} onChange={e=>onFile(e.target.files[0])} />
                <div style={{ width:48, height:48, background:T.accent+"22", border:`1px solid ${T.border}`, borderRadius:10, display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 14px", fontSize:24, color:T.accentL, fontWeight:700 }}>↑</div>
                <div style={{ fontSize:15, fontWeight:600, color:file?T.accentL:"#F1F5F9", marginBottom:6 }}>{file?file.name:"Drop your file here or click to browse"}</div>
                <div style={{ fontSize:13, color:T.text3 }}>{file?`${(file.size/1024).toFixed(0)} KB · ${getEngine(file.name)} engine`:"Supports JPG, PNG, MP4, MOV, PDF, DOCX"}</div>
              </label>
              {file && (
                <div style={{ display:"flex", gap:8, padding:"0 18px 14px", flexWrap:"wrap" }}>
                  {[["image",T.accent,"jpg png webp"],["video","#8B5CF6","mp4 mov avi"],["document","#F59E0B","pdf doc docx"]].map(([eng,col,exts])=>(
                    <div key={eng} style={{ fontSize:12, padding:"4px 12px", borderRadius:5, fontWeight:600, background:getEngine(file.name)===eng?col+"18":T.bg2, color:getEngine(file.name)===eng?col:T.text3, border:`1px solid ${getEngine(file.name)===eng?col+"44":T.border2}` }}>
                      {eng} · {exts}
                    </div>
                  ))}
                </div>
              )}
              <div style={{ padding:"0 18px 18px" }}>
                <button onClick={result?()=>{setResult(null);setFile(null);setPreview(null);}:analyze} disabled={!file||loading}
                  style={{ width:"100%", padding:14, borderRadius:10, border:"none", background:result?T.bg2:(!file||loading)?T.bg2:T.accent, color:result?T.text3:(!file||loading)?T.text4:"#fff", fontSize:15, fontWeight:700, cursor:file&&!loading?"pointer":"not-allowed", outline:result||(!file||loading)?`1px solid ${T.border}`:"none" }}>
                  {loading?step:result?"← Scan another file":file?`Analyze: ${file.name}`:"Upload a file to begin"}
                </button>
                {loading && (
                  <div style={{ marginTop:14 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", fontSize:13, color:T.text3, marginBottom:7 }}>
                      <span>{step}</span><span style={{fontWeight:700,color:T.accentL}}>{progress}%</span>
                    </div>
                    <div style={{ height:4, background:T.bg, borderRadius:4, overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${progress}%`, background:T.accent, borderRadius:4, transition:"width .4s" }} />
                    </div>
                  </div>
                )}
              </div>
            </div>
            {result && !loading && <ResultCard result={result} />}
          </div>
        )}

        {scanTab==="text" && (
          <div>
            <div style={{ background:T.bg3, borderRadius:14, border:`1px solid ${T.border2}`, overflow:"hidden", marginBottom:16 }}>
              <div style={{ padding:"14px 22px", borderBottom:`1px solid ${T.border2}` }}>
                <div style={{ fontSize:15, fontWeight:600, color:"#F1F5F9" }}>Fact-check with Groq AI</div>
                <div style={{ fontSize:13, color:T.text3, marginTop:3 }}>Paste any news article, social post, or claim</div>
              </div>
              <div style={{ padding:20 }}>
                <textarea value={textIn} onChange={e=>setTextIn(e.target.value)} placeholder="Paste text here..."
                  style={{ width:"100%", minHeight:140, padding:14, borderRadius:10, border:`1px solid ${T.border}`, fontSize:14, fontFamily:"inherit", resize:"vertical", boxSizing:"border-box", lineHeight:1.7, color:"#F1F5F9", background:T.bg2, outline:"none" }} />
                <div style={{ display:"flex", gap:8, margin:"12px 0 18px", flexWrap:"wrap" }}>
                  {[["Health misinfo","Doctors are hiding the truth about COVID vaccines! A study mainstream media REFUSES to report shows vaccine destroys immune system. Big Pharma paying scientists to cover this up!"],["Election claim","BREAKING: Voting machines in 6 swing states hacked remotely. Whistleblower has VIDEO PROOF but media COMPLICIT. The steal is happening RIGHT NOW!"],["Real news","The Federal Reserve raised interest rates 0.25 percentage points Wednesday, bringing the benchmark to a 22-year high. Jerome Powell said the committee needs more data before cuts."],["AI-written","In the contemporary landscape of digital communication, it is imperative to acknowledge the multifaceted dimensions of information dissemination across various paradigmatic frameworks."]].map(([l,t])=>(
                    <button key={l} onClick={()=>setTextIn(t)} style={{ fontSize:12, padding:"5px 13px", borderRadius:5, border:`1px solid ${T.border}`, background:T.bg2, cursor:"pointer", color:T.text3, fontWeight:500 }}>{l}</button>
                  ))}
                </div>
                <button onClick={analyzeText} disabled={textLoad||!textIn.trim()} style={{ width:"100%", padding:14, borderRadius:10, border:"none", background:!textLoad&&textIn.trim()?T.accent:T.bg2, color:!textLoad&&textIn.trim()?"#fff":T.text4, fontSize:15, fontWeight:700, cursor:!textLoad&&textIn.trim()?"pointer":"not-allowed", outline:!textLoad&&textIn.trim()?"none":`1px solid ${T.border}` }}>
                  {textLoad?"Groq AI analyzing...":"Fact-check text"}
                </button>
              </div>
            </div>
            {textRes && !textLoad && <ResultCard result={textRes} />}
          </div>
        )}

        {scanTab==="history" && (
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
              <div style={{ fontSize:18, fontWeight:700, color:"#F1F5F9" }}>Scan history</div>
              <div style={{ fontSize:13, color:T.text3 }}>{history.length} scans this session</div>
            </div>
            {history.length===0
              ? <div style={{ background:T.bg3, borderRadius:14, border:`1px solid ${T.border2}`, padding:"64px 28px", textAlign:"center" }}>
                  <div style={{ fontSize:16, fontWeight:600, color:"#F1F5F9", marginBottom:8 }}>No scans yet</div>
                  <div style={{ fontSize:13, color:T.text3 }}>Upload a file or fact-check text to get started</div>
                </div>
              : history.map((h,i)=>(
                <div key={i} style={{ background:T.bg3, borderRadius:12, border:`1px solid ${T.border2}`, padding:"14px 20px", marginBottom:10, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:14 }}>
                    <div style={{ width:36, height:36, borderRadius:8, background:VS[h.verdict]?.bg, border:`1px solid ${VS[h.verdict]?.border}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, fontWeight:700, color:VS[h.verdict]?.dot, flexShrink:0 }}>{VS[h.verdict]?.icon}</div>
                    <div>
                      <div style={{ fontSize:14, fontWeight:600, color:"#F1F5F9" }}>{h.name}</div>
                      <div style={{ fontSize:12, color:T.text3, marginTop:2 }}>{h.engine} · {h.time}</div>
                    </div>
                  </div>
                  <div style={{ textAlign:"right" }}>
                    <span style={{ fontSize:12, fontWeight:600, padding:"3px 11px", borderRadius:5, background:VS[h.verdict]?.bg, color:VS[h.verdict]?.color, border:`1px solid ${VS[h.verdict]?.border}` }}>{VS[h.verdict]?.label}</span>
                    <div style={{ fontSize:12, color:T.text3, marginTop:4 }}>{h.conf}% confidence</div>
                  </div>
                </div>
              ))
            }
          </div>
        )}
      </div>

      <div style={{ width:"100vw", marginLeft:"calc(-50vw + 50%)", borderTop:`1px solid ${T.border2}`, padding:"18px 60px", display:"flex", justifyContent:"center", alignItems:"center", gap:8, background:T.nav }}>
        <span style={{ fontSize:13, color:T.text4 }}>Built by</span>
        <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer" style={{ fontSize:13, fontWeight:600, color:T.accentL, textDecoration:"none" }}>{AUTHOR.name}</a>
        <span style={{ fontSize:13, color:T.text4 }}>· AI Authenticity Detection</span>
      </div>
    </div>
  );
}

function ResultCard({ result }) {
  const [showDebug, setShowDebug] = useState(false);
  const [pdfLoad,   setPdfLoad]   = useState(false);
  const v  = result?.verdict || "error";
  const vs = VS[v] || VS.error;

  async function exportPDF() {
    try {
      setPdfLoad(true);
      const resp = await axios.post(`${API}/report/pdf`, result, { headers:{"Content-Type":"application/json"}, responseType:"blob", timeout:45000 });
      const url  = window.URL.createObjectURL(new Blob([resp.data], { type:"application/pdf" }));
      const a    = document.createElement("a"); a.href=url;
      a.download = `TruthLens_${(result?.filename||"report").replace(/\s+/g,"_")}.pdf`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) { alert("PDF failed: "+err.message); }
    finally { setPdfLoad(false); }
  }

  return (
    <div>
      {result?.ai_summary && result.ai_summary!=="Groq API key not set" && (
        <div style={{ background:"#0C1A2E", borderLeft:"3px solid #0891B2", borderRadius:"0 10px 10px 0", padding:"12px 18px", fontSize:13, color:"#22D3EE", marginBottom:16, lineHeight:1.65 }}>
          <b>Groq AI — </b>{result.ai_summary}
        </div>
      )}
      {result?.groq_active===false && (
        <div style={{ background:"#1A1200", borderLeft:"3px solid #F59E0B", borderRadius:"0 10px 10px 0", padding:"12px 18px", fontSize:13, color:"#FCD34D", marginBottom:16 }}>
          <b>Local engines only</b> — Groq not responding. Check GROQ_API_KEY in .env.
        </div>
      )}
      <div style={{ background:vs.bg, border:`1px solid ${vs.border}`, borderRadius:14, padding:"20px 22px", display:"flex", alignItems:"center", gap:18, marginBottom:16 }}>
        <div style={{ width:50, height:50, borderRadius:10, background:vs.dot+"22", border:`2px solid ${vs.dot}55`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:24, fontWeight:900, color:vs.dot, flexShrink:0 }}>{vs.icon}</div>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:22, fontWeight:800, color:vs.color, letterSpacing:"-0.3px" }}>{vs.label}</div>
          <div style={{ display:"flex", gap:16, marginTop:5, flexWrap:"wrap" }}>
            {[`${result?.confidence||0}% confidence`, result?.fake_score!==undefined&&`Risk: ${result.fake_score}/100`, result?.engine&&`${result.engine} engine`, result?.frames_analyzed&&`${result.frames_analyzed} frames`].filter(Boolean).map((t,i)=>(
              <span key={i} style={{ fontSize:13, color:vs.color, opacity:.65, fontWeight:500 }}>{t}</span>
            ))}
          </div>
        </div>
      </div>
      {(result?.signals?.length>0||result?.findings?.length>0) && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14, marginBottom:16 }}>
          {result?.signals?.length>0 && (
            <div style={{ background:"#0C1A2E", border:"1px solid #0A2540", borderRadius:12, padding:"18px 20px" }}>
              <div style={{ fontSize:9, fontWeight:700, color:"#334155", letterSpacing:".09em", marginBottom:16 }}>SIGNAL BREAKDOWN</div>
              {result.signals.map((s,i)=>(
                <div key={i} style={{ marginBottom:12 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:6 }}>
                    <span style={{ color:"#94A3B8", fontWeight:500 }}>{s.name}</span>
                    <span style={{ fontWeight:700, color:"#F1F5F9" }}>{s.value}%</span>
                  </div>
                  <div style={{ height:4, background:"#020617", borderRadius:3, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:`${s.value}%`, background:s.color, borderRadius:3, transition:"width .7s" }} />
                  </div>
                </div>
              ))}
            </div>
          )}
          {result?.findings?.length>0 && (
            <div style={{ background:"#0C1A2E", border:"1px solid #0A2540", borderRadius:12, padding:"18px 20px" }}>
              <div style={{ fontSize:9, fontWeight:700, color:"#334155", letterSpacing:".09em", marginBottom:16 }}>KEY FINDINGS</div>
              {result.findings.map((f,i)=>(
                <div key={i} style={{ display:"flex", gap:9, marginBottom:10, paddingBottom:10, borderBottom:i<result.findings.length-1?"1px solid #0F1E35":"none" }}>
                  <div style={{ width:5, height:5, borderRadius:"50%", background:vs.dot, flexShrink:0, marginTop:5 }} />
                  <div style={{ fontSize:12, color:"#94A3B8", lineHeight:1.6 }}>{f}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <div style={{ display:"flex", gap:10 }}>
        <button onClick={exportPDF} disabled={pdfLoad} style={{ flex:1, padding:13, borderRadius:10, background:pdfLoad?"#0891B2":"#0C1A2E", color:pdfLoad?"#fff":"#94A3B8", border:"1px solid #0A2540", fontSize:13, fontWeight:700, cursor:pdfLoad?"not-allowed":"pointer" }}>
          {pdfLoad?"Generating PDF...":"↓  Export PDF evidence report"}
        </button>
        <button onClick={()=>setShowDebug(d=>!d)} style={{ padding:"13px 20px", borderRadius:10, background:"#0C1A2E", border:"1px solid #0A2540", fontSize:12, cursor:"pointer", color:"#475569" }}>
          {showDebug?"Hide":"Debug"}
        </button>
      </div>
      {showDebug && (
        <pre style={{ fontSize:10, background:"#010B14", color:"#334155", padding:16, borderRadius:10, overflow:"auto", maxHeight:220, marginTop:10, lineHeight:1.55, border:"1px solid #0A2540" }}>
          {JSON.stringify(result,null,2)}
        </pre>
      )}
    </div>
  );
}