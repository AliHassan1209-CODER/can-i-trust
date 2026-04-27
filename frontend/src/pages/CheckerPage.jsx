import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { analyzeAPI } from '../services/api'
import Navbar from '../components/Navbar'
import toast from 'react-hot-toast'
import './CheckerPage.css'

const STEPS = [
  'Extracting text...',
  'Checking source credibility...',
  'Running ML classifier...',
  'Calculating trust score...',
]

function TrustGauge({ score }) {
  const color = score >= 65 ? 'var(--green)' : score >= 35 ? 'var(--amber)' : 'var(--red)'
  const angle = (score / 100) * 180
  return (
    <div className="gauge-wrap">
      <svg viewBox="0 0 120 70" className="gauge-svg">
        {/* Track */}
        <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="var(--card2)" strokeWidth="10" strokeLinecap="round"/>
        {/* Fill */}
        <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray="157" strokeDashoffset={157 - (score/100)*157}
          style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34,1.56,0.64,1), stroke 0.5s' }}/>
        {/* Needle */}
        <line
          x1="60" y1="60"
          x2={60 + 40 * Math.cos(((angle - 180) * Math.PI) / 180)}
          y2={60 + 40 * Math.sin(((angle - 180) * Math.PI) / 180)}
          stroke={color} strokeWidth="2.5" strokeLinecap="round"
          style={{ transition: 'all 1.2s cubic-bezier(0.34,1.56,0.64,1)' }}/>
        <circle cx="60" cy="60" r="4" fill={color}/>
        {/* Labels */}
        <text x="8"  y="72" fill="var(--txt3)" fontSize="7">0</text>
        <text x="55" y="14" fill="var(--txt3)" fontSize="7">50</text>
        <text x="106" y="72" fill="var(--txt3)" fontSize="7" textAnchor="end">100</text>
      </svg>
      <div className="gauge-score" style={{ color }}>{score}<span>/100</span></div>
    </div>
  )
}

function FactorBar({ label, value, color }) {
  return (
    <div className="factor">
      <div className="factor-head">
        <span className="factor-label">{label}</span>
        <span className="factor-val" style={{ color }}>{Math.round(value)}%</span>
      </div>
      <div className="factor-track">
        <div className="factor-fill" style={{ width: `${value}%`, background: color,
          transition: 'width 1s cubic-bezier(0.34,1.56,0.64,1)' }}/>
      </div>
    </div>
  )
}

export default function CheckerPage() {
  const [inputType, setInputType] = useState('text')
  const [textVal, setTextVal] = useState('')
  const [urlVal, setUrlVal] = useState('')
  const [imageFile, setImageFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [result, setResult] = useState(null)
  const [charCount, setCharCount] = useState(0)

  // Pre-fill from Dashboard "Click to check"
  useEffect(() => {
    const pre = sessionStorage.getItem('prefill')
    if (pre) { setTextVal(pre); setCharCount(pre.length); sessionStorage.removeItem('prefill') }
  }, [])

  const onDrop = useCallback((files) => {
    if (files[0]) setImageFile(files[0])
  }, [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'image/*': [] }, maxFiles: 1
  })

  const runAnalysis = async () => {
    if (inputType === 'text'  && !textVal.trim()) return toast.error('Enter some text first')
    if (inputType === 'url'   && !urlVal.trim())  return toast.error('Enter a URL first')
    if (inputType === 'image' && !imageFile)       return toast.error('Upload an image first')

    setLoading(true)
    setResult(null)
    setStepIdx(0)

    // Animate loading steps
    const iv = setInterval(() => setStepIdx(i => Math.min(i + 1, STEPS.length - 1)), 800)

    try {
      let res
      if (inputType === 'text')  res = await analyzeAPI.text(textVal)
      if (inputType === 'url')   res = await analyzeAPI.url(urlVal)
      if (inputType === 'image') res = await analyzeAPI.image(imageFile)
      clearInterval(iv)
      setResult(res.data)
    } catch (err) {
      clearInterval(iv)
      toast.error(err.response?.data?.detail || 'Analysis failed. Check backend connection.')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setResult(null)
    setTextVal('')
    setUrlVal('')
    setImageFile(null)
    setCharCount(0)
  }

  const verdictMeta = result ? {
    real:      { label: 'Likely Real',  emoji: '✅', cls: 'real',      color: 'var(--green)' },
    fake:      { label: 'FAKE NEWS',    emoji: '🚨', cls: 'fake',      color: 'var(--red)'   },
    uncertain: { label: 'Uncertain',    emoji: '⚠️', cls: 'uncertain', color: 'var(--amber)' },
  }[result.verdict] : null

  const factorColor = (v, invert = false) => {
    const n = invert ? 100 - v : v
    return n >= 65 ? 'var(--green)' : n >= 35 ? 'var(--amber)' : 'var(--red)'
  }

  return (
    <div className="checker-root">
      <Navbar />
      <div className="checker-wrap">

        {/* Page header */}
        <div className="checker-hero">
          <div className="checker-hero-badge">AI Analysis</div>
          <h1 className="checker-title">Is this news <span>real?</span></h1>
          <p className="checker-sub">Paste text, enter a URL, or upload a screenshot — our BERT model will analyze it in seconds.</p>
        </div>

        <div className="checker-body">
          {/* Input Panel */}
          <div className="input-panel">

            {/* Input type tabs */}
            <div className="input-tabs">
              {[
                { id: 'text',  icon: '✏️', label: 'Text'  },
                { id: 'url',   icon: '🔗', label: 'URL'   },
                { id: 'image', icon: '🖼️', label: 'Image' },
              ].map(t => (
                <button
                  key={t.id}
                  className={`input-tab ${inputType === t.id ? 'active' : ''}`}
                  onClick={() => { setInputType(t.id); setResult(null) }}
                >
                  <span>{t.icon}</span>{t.label}
                </button>
              ))}
            </div>

            {/* Text Input */}
            {inputType === 'text' && (
              <div className="input-area">
                <textarea
                  className="text-area"
                  placeholder="Paste a news headline, article, or any text you want to verify..."
                  value={textVal}
                  onChange={e => { setTextVal(e.target.value); setCharCount(e.target.value.length) }}
                  rows={7}
                />
                <div className="char-count">{charCount} characters</div>
              </div>
            )}

            {/* URL Input */}
            {inputType === 'url' && (
              <div className="input-area url-area">
                <div className="url-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                  </svg>
                </div>
                <input
                  className="url-input"
                  type="url"
                  placeholder="https://example.com/news-article"
                  value={urlVal}
                  onChange={e => setUrlVal(e.target.value)}
                />
                <div className="url-hint">We'll scrape the article text automatically</div>
              </div>
            )}

            {/* Image Input */}
            {inputType === 'image' && (
              <div className="input-area" style={{ padding: 0 }}>
                <div {...getRootProps()} className={`dropzone ${isDragActive ? 'drag-active' : ''} ${imageFile ? 'has-file' : ''}`}>
                  <input {...getInputProps()} />
                  {imageFile ? (
                    <div className="file-preview">
                      <div className="file-icon">🖼️</div>
                      <div className="file-name">{imageFile.name}</div>
                      <div className="file-size">{(imageFile.size/1024).toFixed(0)} KB — OCR will extract text</div>
                      <button className="file-remove" onClick={e => { e.stopPropagation(); setImageFile(null) }}>Remove</button>
                    </div>
                  ) : (
                    <div className="drop-prompt">
                      <div className="drop-icon">📁</div>
                      <div className="drop-title">{isDragActive ? 'Drop it here!' : 'Drop screenshot here'}</div>
                      <div className="drop-sub">or click to browse — PNG, JPG up to 10MB<br/>OCR will extract text automatically</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            <button className="analyze-btn" onClick={runAnalysis} disabled={loading}>
              {loading ? (
                <><span className="btn-spinner"/>&nbsp;Analyzing...</>
              ) : (
                <><span className="analyze-icon">⚡</span> Analyze with AI</>
              )}
            </button>

            {/* Loading steps */}
            {loading && (
              <div className="loading-steps">
                {STEPS.map((s, i) => (
                  <div key={i} className={`lstep ${i < stepIdx ? 'done' : i === stepIdx ? 'active' : 'pending'}`}>
                    <span className="lstep-icon">{i < stepIdx ? '✓' : i === stepIdx ? '⋯' : '○'}</span>
                    {s}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Result Panel */}
          <div className="result-panel">
            {!result && !loading && (
              <div className="result-empty">
                <div className="empty-icon">🔍</div>
                <div className="empty-title">Awaiting analysis</div>
                <div className="empty-sub">Enter content on the left and click Analyze</div>
              </div>
            )}

            {result && verdictMeta && (
              <div className={`result-card ${verdictMeta.cls}`}>
                <div className="result-top">
                  <div className="result-emoji">{verdictMeta.emoji}</div>
                  <div>
                    <div className="result-verdict" style={{ color: verdictMeta.color }}>
                      {result.label}
                    </div>
                    <div className="result-confidence">
                      Confidence: {(result.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                <TrustGauge score={Math.round(result.trust_score)} />

                <div className="result-summary">{result.summary}</div>

                {/* Factor bars */}
                <div className="factors-grid">
                  <FactorBar label="Source Credibility"   value={result.factors.source_credibility}   color={factorColor(result.factors.source_credibility)} />
                  <FactorBar label="Claim Verifiability"  value={result.factors.claim_verifiability}  color={factorColor(result.factors.claim_verifiability)} />
                  <FactorBar label="Sentiment Bias"       value={result.factors.sentiment_bias}       color={factorColor(result.factors.sentiment_bias, true)} />
                  <FactorBar label="Language Patterns"    value={result.factors.language_patterns}    color={factorColor(result.factors.language_patterns)} />
                </div>

                <div className="result-meta">
                  <div className="meta-chip">
                    <span>Input:</span> {result.input_type}
                  </div>
                  <div className="meta-chip">
                    <span>Speed:</span> {result.processing_ms}ms
                  </div>
                  <div className="meta-chip">
                    <span>Check ID:</span> #{result.check_id}
                  </div>
                </div>

                {result.extracted_text_preview && (
                  <div className="extracted-preview">
                    <div className="preview-label">Text analyzed:</div>
                    <div className="preview-text">"{result.extracted_text_preview}..."</div>
                  </div>
                )}

                <button className="check-again-btn" onClick={reset}>Check Another →</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
