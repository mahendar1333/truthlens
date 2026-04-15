import { useState, useEffect } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

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

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);
  return isMobile;
}

export default function App() {
  const isMobile = useIsMobile();
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
  const PAD = isMobile ? "0 16px" : "0 60px";
  const SECTION_PAD = isMobile ? "56px 16px" : "96px 60px";

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

  const Navbar = ({ children }) => (
    <nav style={{ position:"sticky", top:0, zIndex:100, width:"100%", background:T.nav, height:isMobile?52:64, display:"flex", alignItems:"center", justifyContent:"space-between", padding:PAD, borderBottom:`1px solid ${T.border}`, boxSizing:"border-box" }}>
      <div style={{ display:"flex", alignItems:"center", gap:8, cursor:"pointer" }} onClick={goHome}>
        <div style={{ width:isMobile?30:36, height:isMobile?30:36, background:T.accent, borderRadius:8, display:"flex", alignItems:"center", justifyContent:"center", fontSize:isMobile?10:12, fontWeight:900, color:"#fff", flexShrink:0 }}>TL</div>
        <span style={{ fontSize:isMobile?14:17, fontWeight:800, color:"#fff", letterSpacing:"-0.5px" }}>TruthLens</span>
        {!isMobile && <span style={{ fontSize:9, background:T.bg2, color:T.accentX, padding:"3px 8px", borderRadius:4, border:`1px solid ${T.border}`, fontWeight:700, letterSpacing:".07em" }}>FORENSICS</span>}
      </div>
      {children}
    </nav>
  );

  /* ════════ HOME PAGE ════════ */
  if (page === "home") return (
    <div style={{ fontFamily:"-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif", background:T.bg, color:T.text, overflowX:"hidden", width:"100%" }}>

      <Navbar>
        {!isMobile && (
          <div style={{ display:"flex", gap:28 }}>
            {[["How it works","#howitworks"],["Features","#features"],["Use cases","#usecases"]].map(([l,h])=>(
              <a key={h} href={h} style={{ fontSize:13, color:"#94A3B8", textDecoration:"none", fontWeight:500 }}>{l}</a>
            ))}
          </div>
        )}
        <button onClick={goScan} style={{ padding:isMobile?"7px 14px":"10px 24px", background:T.accent, color:"#fff", border:"none", borderRadius:7, fontSize:isMobile?12:14, fontWeight:700, cursor:"pointer" }}>
          {isMobile?"Scan →":"Try TruthLens →"}
        </button>
      </Navbar>

      {/* HERO */}
      <div style={{ width:"100%", background:T.bg, padding:SECTION_PAD, borderBottom:`1px solid ${T.border2}`, boxSizing:"border-box" }}>
        <div style={{ maxWidth:1280, margin:"0 auto" }}>
          <div style={{ display:"inline-flex", alignItems:"center", gap:8, background:T.bg2, border:`1px solid ${T.border}`, borderRadius:20, padding:"5px 14px", fontSize:11, color:T.accentX, fontWeight:600, marginBottom:24, letterSpacing:".03em" }}>
            <span style={{ width:6, height:6, borderRadius:"50%", background:"#10B981", display:"inline-block" }}></span>
            Powered by Groq AI · 4 engines · Free
          </div>
          <div style={{ display:"grid", gridTemplateColumns:isMobile?"1fr":"1fr 1fr", gap:isMobile?32:80, alignItems:"center" }}>
            <div>
              <h1 style={{ fontSize:isMobile?"clamp(36px,10vw,52px)":"clamp(44px,5vw,72px)", fontWeight:900, color:"#fff", letterSpacing:"-2px", lineHeight:1.05, margin:"0 0 20px" }}>
                Is it real<br/>or <span style={{ color:T.accentL, fontStyle:"italic" }}>fake?</span><br/>
                <span style={{ fontSize:isMobile?"clamp(28px,8vw,42px)":"clamp(36px,4vw,58px)" }}>Find out in seconds.</span>
              </h1>
              <p style={{ fontSize:isMobile?15:18, color:"#94A3B8", lineHeight:1.8, margin:"0 0 32px", maxWidth:480 }}>
                TruthLens uses AI forensics to detect deepfakes, forged documents, manipulated images, and misinformation — instantly.
              </p>
              <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
                <button onClick={goScan} style={{ padding:isMobile?"13px 24px":"16px 36px", background:T.accent, color:"#fff", border:"none", borderRadius:9, fontSize:isMobile?14:16, fontWeight:700, cursor:"pointer" }}>
                  Start scanning free →
                </button>
                <a href="#howitworks" style={{ padding:isMobile?"13px 24px":"16px 36px", background:"transparent", color:"#94A3B8", border:`1px solid ${T.border}`, borderRadius:9, fontSize:isMobile?14:16, fontWeight:600, textDecoration:"none", display:"inline-flex", alignItems:"center" }}>
                  How it works
                </a>
              </div>
            </div>
            {/* Stats grid */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              {[["800K+","preventable deaths per year","#fff"],["90%","show prior warning signs","#fff"],["4","AI detection engines",T.accentL],["$0","forever free",T.accentL]].map(([n,l,c])=>(
                <div key={n} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:12, padding:isMobile?"18px 14px":"28px 24px" }}>
                  <div style={{ fontSize:isMobile?"clamp(24px,7vw,38px)":"clamp(28px,3vw,44px)", fontWeight:900, color:c, letterSpacing:"-1.5px", lineHeight:1, marginBottom:8 }}>{n}</div>
                  <div style={{ fontSize:isMobile?11:13, color:"#475569", lineHeight:1.5 }}>{l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* HOW IT WORKS */}
      <div id="howitworks" style={{ width:"100%", background:T.bg2, padding:SECTION_PAD, boxSizing:"border-box" }}>
        <div style={{ maxWidth:1280, margin:"0 auto" }}>
          <div style={{ marginBottom:40 }}>
            <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".14em", marginBottom:12 }}>HOW IT WORKS</div>
            <h2 style={{ fontSize:isMobile?"clamp(24px,8vw,38px)":"clamp(28px,4vw,46px)", fontWeight:900, color:"#fff", letterSpacing:"-1.5px", margin:"0 0 12px" }}>One upload. Full verdict.</h2>
            <p style={{ fontSize:isMobile?14:16, color:"#94A3B8", lineHeight:1.75, maxWidth:520 }}>Upload anything suspicious and get a detailed AI forensic report in seconds.</p>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:isMobile?"1fr":"repeat(3,1fr)", gap:16 }}>
            {[
              ["01","Upload your file","Drop any image, video, PDF, or document. Auto-detects type.",T.accent],
              ["02","AI forensics run","Four engines analyze simultaneously with Groq AI intelligence.",T.accentL],
              ["03","Get your verdict","Full verdict with confidence score, findings, and PDF report.",T.accentX],
            ].map(([n,t,d,c])=>(
              <div key={n} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:14, padding:isMobile?"22px 20px":"32px 28px", borderTop:`3px solid ${c}` }}>
                <div style={{ fontSize:isMobile?28:36, fontWeight:900, color:c, letterSpacing:"-1.5px", marginBottom:14, fontStyle:"italic" }}>{n}</div>
                <div style={{ fontSize:isMobile?15:17, fontWeight:700, color:"#fff", marginBottom:8 }}>{t}</div>
                <div style={{ fontSize:isMobile?13:14, color:"#94A3B8", lineHeight:1.75 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4 ENGINES */}
      <div id="features" style={{ width:"100%", background:T.bg, padding:SECTION_PAD, boxSizing:"border-box" }}>
        <div style={{ maxWidth:1280, margin:"0 auto" }}>
          <div style={{ marginBottom:40 }}>
            <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".14em", marginBottom:12 }}>DETECTION ENGINES</div>
            <h2 style={{ fontSize:isMobile?"clamp(24px,8vw,38px)":"clamp(28px,4vw,46px)", fontWeight:900, color:"#fff", letterSpacing:"-1.5px", margin:"0 0 12px" }}>4 engines. Every type of fake.</h2>
            <p style={{ fontSize:isMobile?14:16, color:"#94A3B8", lineHeight:1.75, maxWidth:520 }}>Each engine purpose-built for its media type, enhanced with Groq AI.</p>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:isMobile?"1fr":"repeat(2,1fr)", gap:16 }}>
            {[
              ["Image Forensics",T.accent,"ELA pixel forensics, EXIF metadata tampering, clone detection, DCT frequency, SPN noise analysis.","ELA · EXIF · Clone · DCT · SPN · Groq AI"],
              ["Deepfake Video",T.accentL,"Frame extraction, face boundary artifacts, blink patterns, temporal consistency detection.","Frames · Face · Blink · Temporal · Groq AI"],
              ["Document Forgery","#F59E0B","DOCX/PDF deep parse, font consistency, metadata timestamps, revision history analysis.","DOCX · PDF · Fonts · Metadata · Groq AI"],
              ["Text Fact-Check","#22C55E","Emotion scoring, AI-text patterns, source credibility, chain-of-thought Groq fact-check.","Emotion · AI-detect · Credibility · Groq CoT"],
            ].map(([t,c,d,tech])=>(
              <div key={t} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:14, padding:isMobile?"22px 20px":"32px 28px", borderTop:`3px solid ${c}` }}>
                <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:12 }}>
                  <div style={{ width:10, height:10, borderRadius:"50%", background:c }}></div>
                  <div style={{ fontSize:isMobile?15:18, fontWeight:700, color:"#fff" }}>{t}</div>
                </div>
                <p style={{ fontSize:isMobile?13:14, color:"#94A3B8", lineHeight:1.75, marginBottom:14 }}>{d}</p>
                <div style={{ fontSize:11, color:c, background:c+"18", padding:"7px 12px", borderRadius:7, fontWeight:600, border:`1px solid ${c}33`, wordBreak:"break-word" }}>{tech}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* USE CASES */}
      <div id="usecases" style={{ width:"100%", background:T.bg2, padding:SECTION_PAD, boxSizing:"border-box" }}>
        <div style={{ maxWidth:1280, margin:"0 auto" }}>
          <div style={{ marginBottom:40 }}>
            <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".14em", marginBottom:12 }}>WHO USES TRUTHLENS</div>
            <h2 style={{ fontSize:isMobile?"clamp(24px,8vw,38px)":"clamp(28px,4vw,46px)", fontWeight:900, color:"#fff", letterSpacing:"-1.5px", margin:"0 0 12px" }}>Built for everyone who needs the truth.</h2>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:isMobile?"1fr":"repeat(3,1fr)", gap:14 }}>
            {[
              ["Journalists","Verify images and videos before publishing. Detect AI-generated photos in fake news.",T.accent],
              ["Banks & Legal","Detect forged contracts and fraudulent documents before they cause damage.",T.accentL],
              ["Social Media","Before sharing viral content, verify it has not been manipulated.",T.accentX],
              ["HR & Recruiters","Verify resume documents and detect falsified credentials.",T.accent],
              ["Researchers","Detect AI-generated content and verify authenticity of research images.",T.accentL],
              ["Anyone","Something looks suspicious? Upload it and know in 10 seconds.",T.accentX],
            ].map(([t,d,c])=>(
              <div key={t} style={{ background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:10, padding:"22px 20px", borderLeft:`3px solid ${c}` }}>
                <div style={{ fontSize:isMobile?14:15, fontWeight:700, color:"#fff", marginBottom:8 }}>{t}</div>
                <div style={{ fontSize:isMobile?12:13, color:"#94A3B8", lineHeight:1.7 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* BUILT BY */}
      <div style={{ width:"100%", background:T.bg2, borderTop:`1px solid ${T.border2}`, borderBottom:`1px solid ${T.border2}`, boxSizing:"border-box" }}>
        <div style={{ maxWidth:1280, margin:"0 auto", padding:isMobile?"32px 16px":"48px 60px", display:"flex", flexDirection:isMobile?"column":"row", alignItems:isMobile?"flex-start":"center", justifyContent:"space-between", gap:20 }}>
          <div>
            <div style={{ fontSize:11, fontWeight:700, color:T.accentL, letterSpacing:".12em", marginBottom:10 }}>BUILT BY</div>
            <div style={{ fontSize:isMobile?20:26, fontWeight:800, color:"#fff", letterSpacing:"-0.5px", marginBottom:6 }}>{AUTHOR.name}</div>
            <div style={{ fontSize:isMobile?12:14, color:T.text3 }}>AI Engineering · Full-stack Development · Groq AI</div>
          </div>
          <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer"
            style={{ display:"inline-flex", alignItems:"center", gap:10, background:T.accent, color:"#fff", textDecoration:"none", padding:isMobile?"11px 20px":"14px 28px", borderRadius:9, fontSize:isMobile?13:15, fontWeight:700 }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="#fff"><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg>
            Connect on LinkedIn →
          </a>
        </div>
      </div>

      {/* CTA */}
      <div style={{ width:"100%", background:T.accent, padding:SECTION_PAD, boxSizing:"border-box" }}>
        <div style={{ maxWidth:1280, margin:"0 auto", display:"grid", gridTemplateColumns:isMobile?"1fr":"1fr 1fr", gap:isMobile?28:80, alignItems:"center" }}>
          <div>
            <h2 style={{ fontSize:isMobile?"clamp(28px,9vw,42px)":"clamp(32px,4vw,54px)", fontWeight:900, color:"#fff", letterSpacing:"-2px", margin:"0 0 16px", lineHeight:1.08 }}>Don't share until you verify.</h2>
            <p style={{ fontSize:isMobile?14:18, color:"rgba(255,255,255,0.8)", lineHeight:1.7, margin:0 }}>Full AI forensics verdict in under 10 seconds. Free, forever.</p>
          </div>
          <div>
            <button onClick={goScan} style={{ padding:isMobile?"14px 28px":"18px 44px", background:"#fff", color:T.accent, border:"none", borderRadius:9, fontSize:isMobile?15:18, fontWeight:800, cursor:"pointer", width:isMobile?"100%":"auto" }}>
              Start scanning now →
            </button>
            <div style={{ fontSize:12, color:"rgba(255,255,255,0.6)", marginTop:10 }}>No sign-up required · Works on any device</div>
          </div>
        </div>
      </div>

      {/* FOOTER */}
      <div style={{ width:"100%", background:T.nav, borderTop:`1px solid ${T.border}`, boxSizing:"border-box" }}>
        <div style={{ maxWidth:1280, margin:"0 auto", padding:isMobile?"24px 16px":"36px 60px" }}>
          <div style={{ display:"flex", flexDirection:isMobile?"column":"row", justifyContent:"space-between", alignItems:isMobile?"flex-start":"center", gap:16, marginBottom:20 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <div style={{ width:30, height:30, background:T.accent, borderRadius:6, display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:900, color:"#fff" }}>TL</div>
              <div>
                <div style={{ fontSize:14, fontWeight:700, color:"#fff" }}>TruthLens</div>
                <div style={{ fontSize:11, color:T.text3 }}>AI Authenticity Detection</div>
              </div>
            </div>
            {!isMobile && (
              <div style={{ display:"flex", gap:28 }}>
                {["Image detection","Video deepfakes","Document forgery","Text fact-check"].map(l=>(
                  <span key={l} style={{ fontSize:12, color:T.text3 }}>{l}</span>
                ))}
              </div>
            )}
          </div>
          <div style={{ borderTop:`1px solid ${T.border2}`, paddingTop:18, display:"flex", flexDirection:isMobile?"column":"row", justifyContent:"space-between", alignItems:isMobile?"flex-start":"center", gap:10 }}>
            <div style={{ fontSize:12, color:T.text4 }}>© 2026 TruthLens · AI Authenticity Detection</div>
            <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer"
              style={{ display:"flex", alignItems:"center", gap:6, fontSize:12, fontWeight:600, color:T.accentL, textDecoration:"none" }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill={T.accentL}><path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"/><circle cx="4" cy="4" r="2"/></svg>
              Built by {AUTHOR.name}
            </a>
          </div>
        </div>
      </div>
    </div>
  );

  /* ════════ SCAN PAGE ════════ */
  return (
    <div style={{ fontFamily:"-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',sans-serif", background:T.bg2, minHeight:"100vh", overflowX:"hidden" }}>
      <Navbar>
        <div style={{ display:"flex", gap:2 }}>
          {[["file","Scan"],["text","Check"],["history","History"]].map(([t,l])=>(
            <button key={t} onClick={()=>setScanTab(t)} style={{ padding:isMobile?"5px 10px":"6px 16px", borderRadius:6, border:"none", cursor:"pointer", fontSize:isMobile?11:13, fontWeight:scanTab===t?700:400, background:scanTab===t?T.bg2:"transparent", color:scanTab===t?T.accentL:T.text3 }}>{l}</button>
          ))}
        </div>
        <div style={{ display:"flex", gap:isMobile?12:20, alignItems:"center" }}>
          {!isMobile && [["Scanned",stats.total,"#F1F5F9"],["Fake",stats.fake,"#F87171"],["Real",stats.real,"#4ADE80"]].map(([l,n,c])=>(
            <div key={l} style={{ textAlign:"center" }}>
              <div style={{ fontSize:15, fontWeight:700, color:c, lineHeight:1 }}>{n}</div>
              <div style={{ fontSize:9, color:T.text4, letterSpacing:".06em" }}>{l.toUpperCase()}</div>
            </div>
          ))}
          <button onClick={goHome} style={{ padding:"5px 10px", background:"transparent", color:T.text3, border:`1px solid ${T.border2}`, borderRadius:6, fontSize:11, cursor:"pointer" }}>← Home</button>
        </div>
      </Navbar>

      <div style={{ maxWidth:860, margin:"0 auto", padding:isMobile?"16px 14px":"32px 40px" }}>

        {scanTab==="file" && (
          <div>
            {(preview||result?.heatmap_b64) && (
              <div style={{ display:"grid", gridTemplateColumns:preview&&result?.heatmap_b64&&!isMobile?"1fr 1fr":"1fr", gap:12, marginBottom:16 }}>
                {preview && (
                  <div style={{ background:T.bg3, borderRadius:10, border:`1px solid ${T.border2}`, overflow:"hidden" }}>
                    <div style={{ padding:"8px 14px", borderBottom:`1px solid ${T.border2}`, fontSize:9, fontWeight:700, color:T.text3, letterSpacing:".09em" }}>ORIGINAL</div>
                    <img src={preview} alt="original" style={{ width:"100%", maxHeight:200, objectFit:"contain", display:"block", padding:8 }} />
                  </div>
                )}
                {result?.heatmap_b64 && (
                  <div style={{ background:T.bg3, borderRadius:10, border:`1px solid ${T.border2}`, overflow:"hidden" }}>
                    <div style={{ padding:"8px 14px", borderBottom:`1px solid ${T.border2}`, fontSize:9, fontWeight:700, color:T.text3, letterSpacing:".09em" }}>
                      {result.engine==="video"?"FRAME THUMBNAIL":"ELA HEATMAP"}
                    </div>
                    <img src={`data:image/png;base64,${result.heatmap_b64}`} alt="heatmap" style={{ width:"100%", maxHeight:200, objectFit:"contain", display:"block", padding:8 }} />
                  </div>
                )}
              </div>
            )}

            <div style={{ background:T.bg3, borderRadius:12, border:`1px solid ${T.border2}`, overflow:"hidden", marginBottom:14 }}>
              <div style={{ padding:"12px 16px", borderBottom:`1px solid ${T.border2}`, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <span style={{ fontSize:14, fontWeight:600, color:"#F1F5F9" }}>Upload for analysis</span>
                <span style={{ fontSize:11, color:T.text3 }}>Image · Video · PDF · Doc</span>
              </div>
              <label style={{ display:"block", border:`2px dashed ${T.border}`, borderRadius:9, padding:isMobile?"20px 14px":"32px 24px", textAlign:"center", cursor:"pointer", margin:14, background:T.bg2 }}
                onDragOver={e=>{e.preventDefault();e.currentTarget.style.borderColor=T.accentL;}}
                onDragLeave={e=>{e.currentTarget.style.borderColor=T.border;}}
                onDrop={e=>{e.preventDefault();e.currentTarget.style.borderColor=T.border;onFile(e.dataTransfer.files[0]);}}>
                <input type="file" accept="image/*,video/*,.pdf,.doc,.docx" style={{ display:"none" }} onChange={e=>onFile(e.target.files[0])} />
                <div style={{ width:40, height:40, background:T.accent+"22", border:`1px solid ${T.border}`, borderRadius:9, display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 10px", fontSize:20, color:T.accentL, fontWeight:700 }}>↑</div>
                <div style={{ fontSize:13, fontWeight:600, color:file?T.accentL:"#F1F5F9", marginBottom:4 }}>{file?file.name:"Tap to browse or drop file"}</div>
                <div style={{ fontSize:11, color:T.text3 }}>{file?`${(file.size/1024).toFixed(0)} KB · ${getEngine(file.name)} engine`:"JPG, PNG, MP4, MOV, PDF, DOCX"}</div>
              </label>
              <div style={{ padding:"0 14px 14px" }}>
                <button onClick={result?()=>{setResult(null);setFile(null);setPreview(null);}:analyze} disabled={!file||loading}
                  style={{ width:"100%", padding:13, borderRadius:9, border:"none", background:result?T.bg2:(!file||loading)?T.bg2:T.accent, color:result?T.text3:(!file||loading)?T.text4:"#fff", fontSize:14, fontWeight:700, cursor:file&&!loading?"pointer":"not-allowed", outline:result||(!file||loading)?`1px solid ${T.border}`:"none" }}>
                  {loading?step:result?"← Scan another file":file?`Analyze: ${file.name}`:"Upload a file to begin"}
                </button>
                {loading && (
                  <div style={{ marginTop:12 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, color:T.text3, marginBottom:6 }}>
                      <span>{step}</span><span style={{fontWeight:700,color:T.accentL}}>{progress}%</span>
                    </div>
                    <div style={{ height:3, background:T.bg, borderRadius:3, overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${progress}%`, background:T.accent, borderRadius:3, transition:"width .4s" }} />
                    </div>
                  </div>
                )}
              </div>
            </div>
            {result && !loading && <ResultCard result={result} isMobile={isMobile} />}
          </div>
        )}

        {scanTab==="text" && (
          <div>
            <div style={{ background:T.bg3, borderRadius:12, border:`1px solid ${T.border2}`, overflow:"hidden", marginBottom:14 }}>
              <div style={{ padding:"12px 16px", borderBottom:`1px solid ${T.border2}` }}>
                <div style={{ fontSize:14, fontWeight:600, color:"#F1F5F9" }}>Fact-check with Groq AI</div>
                <div style={{ fontSize:12, color:T.text3, marginTop:2 }}>Paste any news, social post, or claim</div>
              </div>
              <div style={{ padding:14 }}>
                <textarea value={textIn} onChange={e=>setTextIn(e.target.value)} placeholder="Paste text here..."
                  style={{ width:"100%", minHeight:110, padding:12, borderRadius:8, border:`1px solid ${T.border}`, fontSize:13, fontFamily:"inherit", resize:"vertical", boxSizing:"border-box", lineHeight:1.65, color:"#F1F5F9", background:T.bg2, outline:"none" }} />
                <div style={{ display:"flex", gap:6, margin:"10px 0 14px", flexWrap:"wrap" }}>
                  {[["Health misinfo","Doctors are hiding the truth about COVID vaccines! A study mainstream media REFUSES to report shows vaccine destroys immune system. Big Pharma paying scientists to cover this up!"],["Election claim","BREAKING: Voting machines in 6 swing states hacked remotely. Whistleblower has VIDEO PROOF but media COMPLICIT. The steal is happening RIGHT NOW!"],["Real news","The Federal Reserve raised interest rates 0.25 percentage points Wednesday. Jerome Powell said the committee needs more data before considering cuts."],["AI-written","In the contemporary landscape of digital communication, it is imperative to acknowledge the multifaceted dimensions of information dissemination."]].map(([l,t])=>(
                    <button key={l} onClick={()=>setTextIn(t)} style={{ fontSize:11, padding:"4px 10px", borderRadius:5, border:`1px solid ${T.border}`, background:T.bg2, cursor:"pointer", color:T.text3 }}>{l}</button>
                  ))}
                </div>
                <button onClick={analyzeText} disabled={textLoad||!textIn.trim()} style={{ width:"100%", padding:13, borderRadius:9, border:"none", background:!textLoad&&textIn.trim()?T.accent:T.bg2, color:!textLoad&&textIn.trim()?"#fff":T.text4, fontSize:14, fontWeight:700, cursor:!textLoad&&textIn.trim()?"pointer":"not-allowed", outline:!textLoad&&textIn.trim()?"none":`1px solid ${T.border}` }}>
                  {textLoad?"Groq AI analyzing...":"Fact-check text"}
                </button>
              </div>
            </div>
            {textRes && !textLoad && <ResultCard result={textRes} isMobile={isMobile} />}
          </div>
        )}

        {scanTab==="history" && (
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
              <div style={{ fontSize:16, fontWeight:700, color:"#F1F5F9" }}>Scan history</div>
              <div style={{ fontSize:12, color:T.text3 }}>{history.length} scans</div>
            </div>
            {history.length===0
              ? <div style={{ background:T.bg3, borderRadius:12, border:`1px solid ${T.border2}`, padding:"48px 20px", textAlign:"center" }}>
                  <div style={{ fontSize:14, fontWeight:600, color:"#F1F5F9", marginBottom:6 }}>No scans yet</div>
                  <div style={{ fontSize:12, color:T.text3 }}>Upload a file or fact-check text</div>
                </div>
              : history.map((h,i)=>(
                <div key={i} style={{ background:T.bg3, borderRadius:10, border:`1px solid ${T.border2}`, padding:"12px 14px", marginBottom:8, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                    <div style={{ width:32, height:32, borderRadius:6, background:VS[h.verdict]?.bg, border:`1px solid ${VS[h.verdict]?.border}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:14, fontWeight:700, color:VS[h.verdict]?.dot, flexShrink:0 }}>{VS[h.verdict]?.icon}</div>
                    <div>
                      <div style={{ fontSize:12, fontWeight:600, color:"#F1F5F9", maxWidth:isMobile?140:300, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{h.name}</div>
                      <div style={{ fontSize:10, color:T.text3, marginTop:1 }}>{h.engine} · {h.time}</div>
                    </div>
                  </div>
                  <div style={{ textAlign:"right", flexShrink:0 }}>
                    <span style={{ fontSize:10, fontWeight:600, padding:"3px 8px", borderRadius:4, background:VS[h.verdict]?.bg, color:VS[h.verdict]?.color, border:`1px solid ${VS[h.verdict]?.border}` }}>{VS[h.verdict]?.label}</span>
                    <div style={{ fontSize:10, color:T.text3, marginTop:3 }}>{h.conf}%</div>
                  </div>
                </div>
              ))
            }
          </div>
        )}
      </div>

      <div style={{ width:"100%", borderTop:`1px solid ${T.border2}`, padding:isMobile?"14px 16px":"16px 60px", display:"flex", justifyContent:"center", alignItems:"center", gap:6, background:T.nav, flexWrap:"wrap" }}>
        <span style={{ fontSize:12, color:T.text4 }}>Built by</span>
        <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer" style={{ fontSize:12, fontWeight:600, color:T.accentL, textDecoration:"none" }}>{AUTHOR.name}</a>
      </div>
    </div>
  );
}

function ResultCard({ result, isMobile }) {
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
        <div style={{ background:"#0C1A2E", borderLeft:"3px solid #0891B2", borderRadius:"0 8px 8px 0", padding:"10px 14px", fontSize:12, color:"#22D3EE", marginBottom:14, lineHeight:1.65 }}>
          <b>Groq AI — </b>{result.ai_summary}
        </div>
      )}
      {result?.groq_active===false && (
        <div style={{ background:"#1A1200", borderLeft:"3px solid #F59E0B", borderRadius:"0 8px 8px 0", padding:"10px 14px", fontSize:12, color:"#FCD34D", marginBottom:14 }}>
          <b>Local engines only</b> — Groq not responding.
        </div>
      )}
      <div style={{ background:vs.bg, border:`1px solid ${vs.border}`, borderRadius:12, padding:"14px 16px", display:"flex", alignItems:"center", gap:14, marginBottom:14 }}>
        <div style={{ width:42, height:42, borderRadius:8, background:vs.dot+"22", border:`2px solid ${vs.dot}55`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:20, fontWeight:900, color:vs.dot, flexShrink:0 }}>{vs.icon}</div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ fontSize:isMobile?17:20, fontWeight:800, color:vs.color }}>{vs.label}</div>
          <div style={{ display:"flex", gap:10, marginTop:4, flexWrap:"wrap" }}>
            {[`${result?.confidence||0}% confidence`, result?.fake_score!==undefined&&`Risk: ${result.fake_score}/100`, result?.engine&&`${result.engine}`].filter(Boolean).map((t,i)=>(
              <span key={i} style={{ fontSize:11, color:vs.color, opacity:.65, fontWeight:500 }}>{t}</span>
            ))}
          </div>
        </div>
      </div>

      {(result?.signals?.length>0||result?.findings?.length>0) && (
        <div style={{ display:"grid", gridTemplateColumns:isMobile?"1fr":"1fr 1fr", gap:12, marginBottom:14 }}>
          {result?.signals?.length>0 && (
            <div style={{ background:"#0C1A2E", border:"1px solid #0A2540", borderRadius:10, padding:"14px 16px" }}>
              <div style={{ fontSize:9, fontWeight:700, color:"#334155", letterSpacing:".09em", marginBottom:12 }}>SIGNAL BREAKDOWN</div>
              {result.signals.map((s,i)=>(
                <div key={i} style={{ marginBottom:10 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, marginBottom:4 }}>
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
            <div style={{ background:"#0C1A2E", border:"1px solid #0A2540", borderRadius:10, padding:"14px 16px" }}>
              <div style={{ fontSize:9, fontWeight:700, color:"#334155", letterSpacing:".09em", marginBottom:12 }}>KEY FINDINGS</div>
              {result.findings.map((f,i)=>(
                <div key={i} style={{ display:"flex", gap:8, marginBottom:8, paddingBottom:8, borderBottom:i<result.findings.length-1?"1px solid #0F1E35":"none" }}>
                  <div style={{ width:5, height:5, borderRadius:"50%", background:vs.dot, flexShrink:0, marginTop:4 }} />
                  <div style={{ fontSize:11, color:"#94A3B8", lineHeight:1.6 }}>{f}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={{ display:"flex", gap:8 }}>
        <button onClick={exportPDF} disabled={pdfLoad} style={{ flex:1, padding:11, borderRadius:9, background:pdfLoad?"#0891B2":"#0C1A2E", color:pdfLoad?"#fff":"#94A3B8", border:"1px solid #0A2540", fontSize:12, fontWeight:700, cursor:pdfLoad?"not-allowed":"pointer" }}>
          {pdfLoad?"Generating...":"↓ Export PDF report"}
        </button>
        <button onClick={()=>setShowDebug(d=>!d)} style={{ padding:"11px 14px", borderRadius:9, background:"#0C1A2E", border:"1px solid #0A2540", fontSize:11, cursor:"pointer", color:"#475569" }}>
          {showDebug?"Hide":"Debug"}
        </button>
      </div>
      {showDebug && (
        <pre style={{ fontSize:10, background:"#010B14", color:"#334155", padding:12, borderRadius:8, overflow:"auto", maxHeight:200, marginTop:8, lineHeight:1.55, border:"1px solid #0A2540" }}>
          {JSON.stringify(result,null,2)}
        </pre>
      )}
    </div>
  );
}