import { useState, useEffect, useRef } from "react";

const LOADING_MESSAGES = [
  "Fetching video...",
  "Grabbing subtitles...",
  "Reading the transcript...",
  "Identifying advanced vocabulary...",
  "Extracting key phrases...",
  "Almost done...",
];

const DIFFICULTY_COLORS = {
  intermediate: { bg: "#E0F7F4", color: "#0D9488", label: "Intermediate" },
  advanced: { bg: "#DBEAFE", color: "#2563EB", label: "Advanced" },
  sophisticated: { bg: "#EDE9FE", color: "#7C3AED", label: "Sophisticated" },
};

const REGISTER_COLORS = {
  formal: { bg: "#FEF3C7", color: "#D97706" },
  informal: { bg: "#FCE7F3", color: "#DB2777" },
  neutral: { bg: "#F3F4F6", color: "#4B5563" },
  academic: { bg: "#DBEAFE", color: "#1D4ED8" },
  professional: { bg: "#D1FAE5", color: "#065F46" },
};

const styles = {
  root: {
    fontFamily: "'Inter', sans-serif",
    background: "#F4F6FB",
    minHeight: "100vh",
    margin: 0,
  },
  header: {
    background: "#1A2035",
    padding: "0 24px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    height: 60,
  },
  logo: {
    color: "#fff",
    fontWeight: 700,
    fontSize: 20,
    letterSpacing: "-0.3px",
  },
  logoSpan: { color: "#60A5FA" },
  newFileBtn: {
    background: "transparent",
    border: "1px solid rgba(255,255,255,0.3)",
    color: "#fff",
    borderRadius: 8,
    padding: "6px 14px",
    cursor: "pointer",
    fontSize: 13,
    fontFamily: "'Inter', sans-serif",
  },
  main: {
    maxWidth: 780,
    margin: "0 auto",
    padding: "48px 24px 80px",
  },
  hero: {
    textAlign: "center",
    marginBottom: 40,
  },
  heroTitle: {
    fontSize: 36,
    fontWeight: 700,
    color: "#111827",
    margin: "0 0 12px",
    letterSpacing: "-0.5px",
  },
  heroSub: {
    fontSize: 16,
    color: "#6B7280",
    margin: 0,
    lineHeight: 1.6,
  },
  inputCard: {
    background: "#fff",
    borderRadius: 16,
    border: "1px solid #EAEDF2",
    padding: "32px 32px 28px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  label: {
    display: "block",
    fontSize: 13,
    fontWeight: 600,
    color: "#374151",
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  urlInputWrap: {
    display: "flex",
    gap: 10,
  },
  urlInput: {
    flex: 1,
    border: "1px solid #D1D5DB",
    borderRadius: 10,
    padding: "12px 16px",
    fontSize: 15,
    fontFamily: "'Inter', sans-serif",
    outline: "none",
    color: "#111827",
    transition: "border-color 0.15s",
  },
  extractBtn: {
    background: "#1A2035",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    padding: "12px 22px",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
    fontFamily: "'Inter', sans-serif",
    whiteSpace: "nowrap",
    transition: "background 0.15s",
  },
  hint: {
    fontSize: 12,
    color: "#9CA3AF",
    marginTop: 10,
  },
  errorBox: {
    background: "#FEF2F2",
    border: "1px solid #FECACA",
    borderRadius: 10,
    padding: "12px 16px",
    color: "#B91C1C",
    fontSize: 14,
    marginTop: 16,
  },
  loadingWrap: {
    textAlign: "center",
    padding: "80px 24px",
  },
  spinner: {
    width: 44,
    height: 44,
    border: "3px solid #E5E7EB",
    borderTop: "3px solid #1A2035",
    borderRadius: "50%",
    margin: "0 auto 24px",
    animation: "spin 0.8s linear infinite",
  },
  loadingMsg: {
    fontSize: 17,
    color: "#374151",
    fontWeight: 500,
    transition: "opacity 0.3s",
  },
  loadingSub: {
    fontSize: 13,
    color: "#9CA3AF",
    marginTop: 8,
  },
  summaryCard: {
    background: "linear-gradient(135deg, #1A2035 0%, #2D3A5E 100%)",
    borderRadius: 16,
    padding: "28px 32px",
    marginBottom: 28,
    color: "#fff",
  },
  summarySource: {
    fontSize: 12,
    color: "#93C5FD",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 10,
  },
  summaryText: {
    fontFamily: "'Lora', serif",
    fontSize: 16,
    lineHeight: 1.7,
    color: "#E5E7EB",
    marginBottom: 20,
  },
  summaryStats: {
    display: "flex",
    gap: 24,
    flexWrap: "wrap",
  },
  stat: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  statNum: {
    fontSize: 22,
    fontWeight: 700,
    color: "#60A5FA",
  },
  statLabel: {
    fontSize: 11,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  tabBar: {
    display: "flex",
    gap: 4,
    marginBottom: 20,
    background: "#fff",
    borderRadius: 12,
    padding: 4,
    border: "1px solid #EAEDF2",
    width: "fit-content",
  },
  tab: (active) => ({
    padding: "8px 20px",
    borderRadius: 9,
    border: "none",
    background: active ? "#1A2035" : "transparent",
    color: active ? "#fff" : "#6B7280",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    fontFamily: "'Inter', sans-serif",
    transition: "all 0.15s",
  }),
  cardList: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  card: (expanded) => ({
    background: "#fff",
    border: "1px solid #EAEDF2",
    borderRadius: 12,
    overflow: "hidden",
    boxShadow: expanded ? "0 4px 16px rgba(0,0,0,0.08)" : "0 1px 3px rgba(0,0,0,0.04)",
    transition: "box-shadow 0.2s",
    cursor: "pointer",
  }),
  cardHeader: {
    display: "flex",
    alignItems: "center",
    padding: "16px 20px",
    gap: 12,
  },
  cardIndex: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    background: "#F3F4F6",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    fontWeight: 700,
    color: "#6B7280",
    flexShrink: 0,
  },
  cardMeta: { flex: 1 },
  cardWord: {
    fontFamily: "'Lora', serif",
    fontSize: 17,
    fontWeight: 700,
    color: "#111827",
    margin: "0 0 2px",
  },
  cardPos: {
    fontSize: 12,
    color: "#9CA3AF",
    fontStyle: "italic",
  },
  cardDef: {
    fontSize: 14,
    color: "#4B5563",
    marginTop: 2,
    lineHeight: 1.5,
  },
  badge: (style) => ({
    background: style?.bg || "#F3F4F6",
    color: style?.color || "#374151",
    fontSize: 11,
    fontWeight: 600,
    padding: "3px 10px",
    borderRadius: 20,
    whiteSpace: "nowrap",
    flexShrink: 0,
  }),
  chevron: (expanded) => ({
    fontSize: 13,
    color: "#9CA3AF",
    transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
    transition: "transform 0.2s",
    flexShrink: 0,
  }),
  cardBody: {
    padding: "0 20px 18px",
    borderTop: "1px solid #F3F4F6",
  },
  quoteBlock: (borderColor) => ({
    borderLeft: `3px solid ${borderColor}`,
    padding: "10px 14px",
    background: "#F9FAFB",
    borderRadius: "0 8px 8px 0",
    margin: "12px 0 0",
  }),
  quoteLabel: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "#9CA3AF",
    marginBottom: 4,
  },
  quoteText: {
    fontFamily: "'Lora', serif",
    fontSize: 14,
    fontStyle: "italic",
    color: "#374151",
    lineHeight: 1.6,
  },
  tipRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: 8,
    marginTop: 12,
    fontSize: 13,
    color: "#4B5563",
    lineHeight: 1.5,
  },
  phraseWord: {
    fontFamily: "'Lora', serif",
    fontSize: 16,
    fontWeight: 700,
    color: "#111827",
    margin: "0 0 2px",
  },
  transcriptDetails: {
    marginTop: 32,
    background: "#fff",
    border: "1px solid #EAEDF2",
    borderRadius: 12,
    padding: "0",
    overflow: "hidden",
  },
  transcriptSummary: {
    padding: "14px 20px",
    fontSize: 13,
    fontWeight: 600,
    color: "#6B7280",
    cursor: "pointer",
    userSelect: "none",
    listStyle: "none",
  },
  transcriptText: {
    padding: "0 20px 16px",
    fontSize: 13,
    color: "#6B7280",
    lineHeight: 1.6,
    fontFamily: "'Lora', serif",
    borderTop: "1px solid #F3F4F6",
  },
  learningCard: (expanded) => ({
    background: "#fff",
    border: "1px solid #EAEDF2",
    borderRadius: 12,
    overflow: "hidden",
    boxShadow: expanded ? "0 4px 16px rgba(0,0,0,0.08)" : "0 1px 3px rgba(0,0,0,0.04)",
    cursor: "pointer",
  }),
  learningInsight: {
    fontSize: 15,
    fontWeight: 600,
    color: "#111827",
    lineHeight: 1.5,
    flex: 1,
  },
};

function VocabCard({ item, index }) {
  const [expanded, setExpanded] = useState(false);
  const diff = DIFFICULTY_COLORS[item.difficulty?.toLowerCase()] || DIFFICULTY_COLORS.intermediate;

  return (
    <div style={styles.card(expanded)} onClick={() => setExpanded((e) => !e)}>
      <div style={styles.cardHeader}>
        <div style={styles.cardIndex}>{index + 1}</div>
        <div style={styles.cardMeta}>
          <div style={styles.cardWord}>{item.word}</div>
          <div style={styles.cardPos}>{item.part_of_speech}</div>
          {!expanded && <div style={styles.cardDef}>{item.definition}</div>}
        </div>
        <span style={styles.badge(diff)}>{diff.label}</span>
        <span style={styles.chevron(expanded)}>▼</span>
      </div>
      {expanded && (
        <div style={styles.cardBody}>
          <div style={{ fontSize: 14, color: "#4B5563", lineHeight: 1.6 }}>{item.definition}</div>
          {item.example_from_audio && (
            <div style={styles.quoteBlock("#3B82F6")}>
              <div style={styles.quoteLabel}>From the audio</div>
              <div style={styles.quoteText}>"{item.example_from_audio}"</div>
            </div>
          )}
          {item.why_useful && (
            <div style={styles.tipRow}>
              <span>💡</span>
              <span>{item.why_useful}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PhraseCard({ item, index }) {
  const [expanded, setExpanded] = useState(false);
  const reg = REGISTER_COLORS[item.register?.toLowerCase()] || REGISTER_COLORS.neutral;

  return (
    <div style={styles.card(expanded)} onClick={() => setExpanded((e) => !e)}>
      <div style={styles.cardHeader}>
        <div style={styles.cardIndex}>{index + 1}</div>
        <div style={styles.cardMeta}>
          <div style={styles.phraseWord}>"{item.phrase}"</div>
          {!expanded && <div style={styles.cardDef}>{item.meaning}</div>}
        </div>
        <span style={styles.badge(reg)}>{item.register}</span>
        <span style={styles.chevron(expanded)}>▼</span>
      </div>
      {expanded && (
        <div style={styles.cardBody}>
          <div style={{ fontSize: 14, color: "#4B5563", lineHeight: 1.6 }}>{item.meaning}</div>
          {item.example_from_audio && (
            <div style={styles.quoteBlock("#10B981")}>
              <div style={styles.quoteLabel}>In context</div>
              <div style={styles.quoteText}>"{item.example_from_audio}"</div>
            </div>
          )}
          {item.usage_tip && (
            <div style={styles.tipRow}>
              <span>✏️</span>
              <span>{item.usage_tip}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LearningCard({ item, index }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div style={styles.learningCard(expanded)} onClick={() => setExpanded((e) => !e)}>
      <div style={styles.cardHeader}>
        <div style={{ ...styles.cardIndex, background: "#FEF3C7", color: "#D97706" }}>{index + 1}</div>
        <div style={styles.learningInsight}>{item.insight}</div>
        <span style={styles.chevron(expanded)}>▼</span>
      </div>
      {expanded && (
        <div style={styles.cardBody}>
          <div style={{ fontSize: 14, color: "#4B5563", lineHeight: 1.7 }}>{item.detail}</div>
          {item.quote && (
            <div style={styles.quoteBlock("#F59E0B")}>
              <div style={styles.quoteLabel}>From the podcast</div>
              <div style={styles.quoteText}>"{item.quote}"</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [state, setState] = useState("idle"); // idle | loading | result
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState("learnings");
  const [loadingMsgIdx, setLoadingMsgIdx] = useState(0);
  const [emailStatus, setEmailStatus] = useState("idle"); // idle | sending | sent | error
  const intervalRef = useRef(null);

  useEffect(() => {
    if (state === "loading") {
      intervalRef.current = setInterval(() => {
        setLoadingMsgIdx((i) => (i + 1) % LOADING_MESSAGES.length);
      }, 2200);
    } else {
      clearInterval(intervalRef.current);
      setLoadingMsgIdx(0);
    }
    return () => clearInterval(intervalRef.current);
  }, [state]);

  const handleExtract = async () => {
    if (!url.trim()) {
      setError("Please enter a YouTube URL.");
      return;
    }
    setError("");
    setState("loading");

    try {
      const res = await fetch("http://localhost:8000/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Something went wrong.");
      }
      setResult(data);
      setState("result");
    } catch (err) {
      setError(err.message);
      setState("idle");
    }
  };

  const handleReset = () => {
    setState("idle");
    setUrl("");
    setResult(null);
    setError("");
    setActiveTab("learnings");
    setEmailStatus("idle");
  };

  const handleSendEmail = async () => {
    if (!result) return;
    setEmailStatus("sending");
    try {
      const res = await fetch("http://localhost:8000/send-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: result.source,
          summary: result.summary,
          vocabulary: result.vocabulary || [],
          phrases: result.phrases || [],
          key_learnings: result.key_learnings || [],
          word_count: result.word_count,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to send");
      setEmailStatus("sent");
      setTimeout(() => setEmailStatus("idle"), 4000);
    } catch (err) {
      setEmailStatus("error");
      setTimeout(() => setEmailStatus("idle"), 4000);
    }
  };

  return (
    <div style={styles.root}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { box-sizing: border-box; }
        body { margin: 0; }
        input:focus { border-color: #1A2035 !important; box-shadow: 0 0 0 3px rgba(26,32,53,0.08); }
        button:hover { opacity: 0.88; }
        details summary::-webkit-details-marker { display: none; }
      `}</style>

      <header style={styles.header}>
        <div style={styles.logo}>
          Lexi<span style={styles.logoSpan}>Cast</span>
        </div>
        {state === "result" && (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              style={{
                ...styles.newFileBtn,
                background: emailStatus === "sent" ? "#065F46" : emailStatus === "error" ? "#7F1D1D" : "#1E40AF",
                border: "none",
                opacity: emailStatus === "sending" ? 0.6 : 1,
              }}
              onClick={handleSendEmail}
              disabled={emailStatus === "sending"}
            >
              {emailStatus === "sending" ? "Sending..." : emailStatus === "sent" ? "✓ Sent!" : emailStatus === "error" ? "Failed" : "✉ Send to email"}
            </button>
            <button style={styles.newFileBtn} onClick={handleReset}>
              ← New video
            </button>
          </div>
        )}
      </header>

      <main style={styles.main}>
        {state === "idle" && (
          <>
            <div style={styles.hero}>
              <h1 style={styles.heroTitle}>Learn from what you watch</h1>
              <p style={styles.heroSub}>
                Paste any YouTube link. LexiCast extracts advanced vocabulary
                <br />
                and key phrases worth studying — straight from the transcript.
              </p>
            </div>

            <div style={styles.inputCard}>
              <label style={styles.label}>YouTube URL</label>
              <div style={styles.urlInputWrap}>
                <input
                  style={styles.urlInput}
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleExtract()}
                />
                <button style={styles.extractBtn} onClick={handleExtract}>
                  Extract →
                </button>
              </div>
              <div style={styles.hint}>
                Works with podcasts, talks, interviews, lectures — any English video with speech.
              </div>
              {error && <div style={styles.errorBox}>{error}</div>}
            </div>
          </>
        )}

        {state === "loading" && (
          <div style={styles.loadingWrap}>
            <div style={styles.spinner} />
            <div style={styles.loadingMsg}>{LOADING_MESSAGES[loadingMsgIdx]}</div>
            <div style={styles.loadingSub}>This can take 30–90 seconds for longer videos</div>
          </div>
        )}

        {state === "result" && result && (
          <>
            <div style={styles.summaryCard}>
              <div style={styles.summarySource}>
                {result.method === "whisper" ? "🎙 Transcribed via Whisper" : "📄 From subtitles"} · {result.source}
              </div>
              <div style={styles.summaryText}>{result.summary}</div>
              <div style={styles.summaryStats}>
                <div style={styles.stat}>
                  <span style={styles.statNum}>{result.key_learnings?.length || 0}</span>
                  <span style={styles.statLabel}>Key learnings</span>
                </div>
                <div style={styles.stat}>
                  <span style={styles.statNum}>{result.vocabulary?.length || 0}</span>
                  <span style={styles.statLabel}>Vocab words</span>
                </div>
                <div style={styles.stat}>
                  <span style={styles.statNum}>{result.phrases?.length || 0}</span>
                  <span style={styles.statLabel}>Key phrases</span>
                </div>
                <div style={styles.stat}>
                  <span style={styles.statNum}>{result.word_count?.toLocaleString()}</span>
                  <span style={styles.statLabel}>Words processed</span>
                </div>
              </div>
            </div>

            <div style={styles.tabBar}>
              <button style={styles.tab(activeTab === "learnings")} onClick={() => setActiveTab("learnings")}>
                Key Learnings
              </button>
              <button style={styles.tab(activeTab === "vocab")} onClick={() => setActiveTab("vocab")}>
                Vocabulary
              </button>
              <button style={styles.tab(activeTab === "phrases")} onClick={() => setActiveTab("phrases")}>
                Phrases
              </button>
            </div>

            <div style={styles.cardList}>
              {activeTab === "learnings" &&
                (result.key_learnings || []).map((item, i) => (
                  <LearningCard key={i} item={item} index={i} />
                ))}
              {activeTab === "vocab" &&
                (result.vocabulary || []).map((item, i) => (
                  <VocabCard key={i} item={item} index={i} />
                ))}
              {activeTab === "phrases" &&
                (result.phrases || []).map((item, i) => (
                  <PhraseCard key={i} item={item} index={i} />
                ))}
            </div>

            {result.transcript_preview && (
              <details style={styles.transcriptDetails}>
                <summary style={styles.transcriptSummary}>▸ Transcript preview</summary>
                <div style={styles.transcriptText}>{result.transcript_preview}…</div>
              </details>
            )}
          </>
        )}
      </main>
    </div>
  );
}
