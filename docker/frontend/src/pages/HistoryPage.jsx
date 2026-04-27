import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeAPI } from '../services/api'
import Navbar from '../components/Navbar'
import { formatDistanceToNow } from 'date-fns'
import './HistoryPage.css'

const VERDICT_META = {
  real:      { label: 'Real',      color: 'var(--green)', bg: 'rgba(29,233,165,0.1)', icon: '✅' },
  fake:      { label: 'Fake',      color: 'var(--red)',   bg: 'rgba(240,79,79,0.1)',  icon: '🚨' },
  uncertain: { label: 'Uncertain', color: 'var(--amber)', bg: 'rgba(245,166,35,0.1)', icon: '⚠️' },
}

export default function HistoryPage() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter]   = useState('all')
  const navigate = useNavigate()

  useEffect(() => {
    analyzeAPI.history(50, 0)
      .then(r => setItems(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? items : items.filter(i => i.verdict === filter)

  const stats = {
    total:    items.length,
    real:     items.filter(i => i.verdict === 'real').length,
    fake:     items.filter(i => i.verdict === 'fake').length,
    uncertain: items.filter(i => i.verdict === 'uncertain').length,
  }

  const timeAgo = (str) => {
    try { return formatDistanceToNow(new Date(str), { addSuffix: true }) } catch { return '' }
  }

  return (
    <div className="hist-root">
      <Navbar />
      <div className="hist-wrap">
        <div className="hist-header">
          <div>
            <h1 className="hist-title">Check <span>History</span></h1>
            <p className="hist-sub">All your past fake news analyses</p>
          </div>
          <button className="new-check-btn" onClick={() => navigate('/checker')}>+ New Check</button>
        </div>

        {/* Stats Row */}
        <div className="stats-row">
          {[
            { label: 'Total Checks', val: stats.total, color: 'var(--accent)' },
            { label: 'Real',     val: stats.real,     color: 'var(--green)' },
            { label: 'Fake',     val: stats.fake,     color: 'var(--red)' },
            { label: 'Uncertain', val: stats.uncertain, color: 'var(--amber)' },
          ].map(s => (
            <div key={s.label} className="stat-card">
              <div className="stat-card-val" style={{ color: s.color }}>{s.val}</div>
              <div className="stat-card-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Filter Tabs */}
        <div className="filter-tabs">
          {['all', 'real', 'fake', 'uncertain'].map(f => (
            <button
              key={f}
              className={`filter-tab ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All' : VERDICT_META[f].icon + ' ' + VERDICT_META[f].label}
            </button>
          ))}
        </div>

        {/* List */}
        {loading ? (
          <div className="hist-loading">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="hist-skeleton" style={{ animationDelay: `${i*0.07}s` }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="hist-empty">
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem', opacity: 0.3 }}>📋</div>
            <div style={{ fontWeight: 500, marginBottom: '0.35rem' }}>No checks yet</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--txt2)' }}>
              Go to Checker and analyze your first news article
            </div>
            <button className="new-check-btn" style={{ marginTop: '1rem' }} onClick={() => navigate('/checker')}>
              Start Checking →
            </button>
          </div>
        ) : (
          <div className="hist-list">
            {filtered.map((item, i) => {
              const meta = VERDICT_META[item.verdict] || VERDICT_META.uncertain
              return (
                <div key={item.id} className="hist-item" style={{ animationDelay: `${i*0.04}s` }}>
                  <div className="hist-icon" style={{ background: meta.bg, color: meta.color }}>
                    {meta.icon}
                  </div>
                  <div className="hist-content">
                    <div className="hist-input">{item.original_input?.slice(0,120)}{item.original_input?.length > 120 ? '...' : ''}</div>
                    <div className="hist-chips">
                      <span className="hist-chip" style={{ color: meta.color }}>{meta.label}</span>
                      <span className="hist-chip">Trust: {Math.round(item.trust_score)}/100</span>
                      <span className="hist-chip type-chip">{item.input_type}</span>
                      <span className="hist-chip time-chip">{timeAgo(item.created_at)}</span>
                    </div>
                  </div>
                  <div className="hist-score-bar">
                    <div className="hist-score-fill" style={{
                      height: `${item.trust_score}%`,
                      background: meta.color,
                    }}/>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
