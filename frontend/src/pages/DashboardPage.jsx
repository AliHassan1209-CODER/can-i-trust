import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { newsAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import { useNewsStore } from '../store/newsStore'
import Navbar from '../components/Navbar'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'
import './DashboardPage.css'

const CATEGORIES = [
  { id: 'general',       label: 'All' },
  { id: 'technology',    label: 'Tech' },
  { id: 'science',       label: 'Science' },
  { id: 'business',      label: 'Business' },
  { id: 'health',        label: 'Health' },
  { id: 'sports',        label: 'Sports' },
]

const TRENDING_TOPICS = [
  { rank: 1, topic: 'Pakistan elections 2025',         heat: '148k mentions', tag: 'Politics' },
  { rank: 2, topic: 'AI regulation global summit',     heat: '92k mentions',  tag: 'Tech' },
  { rank: 3, topic: 'Climate emergency declaration',   heat: '67k mentions',  tag: 'Science' },
  { rank: 4, topic: 'Cryptocurrency market crash',     heat: '54k mentions',  tag: 'Business' },
  { rank: 5, topic: 'COVID-19 new variant alert',      heat: '41k mentions',  tag: 'Health' },
]

export default function DashboardPage() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const { articles, category, loading, searchQuery, setArticles, setCategory, setLoading, setSearchQuery } = useNewsStore()
  const [searchInput, setSearchInput] = useState(searchQuery)
  const [searching, setSearching] = useState(false)
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  const fetchNews = useCallback(async (cat) => {
    setLoading(true)
    try {
      const res = await newsAPI.trending(cat)
      setArticles(res.data.articles || [])
    } catch {
      // fallback to mock if API key not set
      setArticles(MOCK_ARTICLES)
    } finally {
      setLoading(false)
    }
  }, [setArticles, setLoading])

  useEffect(() => {
    fetchNews(category)
  }, [category, fetchNews])

  const handleCategoryChange = (cat) => {
    setCategory(cat)
    setSearchInput('')
    setSearchQuery('')
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchInput.trim()) return
    setSearching(true)
    setSearchQuery(searchInput)
    try {
      const res = await newsAPI.search(searchInput)
      setArticles(res.data.articles || [])
    } catch {
      toast.error('Search failed')
    } finally {
      setSearching(false)
    }
  }

  const checkArticle = (article) => {
    const text = `${article.title}. ${article.description || ''}`
    sessionStorage.setItem('prefill', text)
    navigate('/checker')
  }

  const timeAgo = (str) => {
    try { return formatDistanceToNow(new Date(str), { addSuffix: true }) }
    catch { return '' }
  }

  return (
    <div className="dash-root">
      <Navbar />
      <div className="dash-wrap">

        {/* Hero Header */}
        <div className="dash-hero">
          <div className="dash-hero-text">
            <div className="dash-greeting">{greeting}, {user?.full_name?.split(' ')[0] || 'there'}</div>
            <h1 className="dash-headline">What's in the <span>news</span> today?</h1>
            <p className="dash-sub">Browse top stories. Click any card to run a fake news check instantly.</p>
          </div>
          <div className="dash-hero-stat">
            <div className="stat-num">44K+</div>
            <div className="stat-label">Articles trained on</div>
          </div>
        </div>

        {/* Search Bar */}
        <form className="dash-search" onSubmit={handleSearch}>
          <div className="search-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </div>
          <input
            className="search-input"
            placeholder="Search news topics..."
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
          />
          <button className="search-btn" type="submit" disabled={searching}>
            {searching ? '...' : 'Search'}
          </button>
        </form>

        {/* Category Pills */}
        <div className="cat-row">
          {CATEGORIES.map(c => (
            <button
              key={c.id}
              className={`cat-pill ${category === c.id && !searchQuery ? 'active' : ''}`}
              onClick={() => handleCategoryChange(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="dash-grid">
          {/* Articles */}
          <div className="articles-col">
            <div className="section-hd">
              <div className="live-indicator"><span className="live-dot" /> Live</div>
              <span>{searchQuery ? `Results for "${searchQuery}"` : `${category.charAt(0).toUpperCase()+category.slice(1)} News`}</span>
            </div>

            {loading ? (
              <div className="articles-loading">
                {[...Array(6)].map((_, i) => <div key={i} className="skeleton-card" style={{ animationDelay: `${i*0.08}s` }} />)}
              </div>
            ) : articles.length === 0 ? (
              <div className="empty-state">No articles found</div>
            ) : (
              <div className="articles-grid">
                {articles.map((a, i) => (
                  <div key={i} className="article-card" onClick={() => checkArticle(a)}>
                    {a.url_to_image && (
                      <div className="article-img-wrap">
                        <img src={a.url_to_image} alt="" className="article-img" loading="lazy"
                          onError={e => { e.target.style.display='none' }} />
                      </div>
                    )}
                    <div className="article-body">
                      <div className="article-source">{a.source}</div>
                      <div className="article-title">{a.title}</div>
                      {a.description && <div className="article-desc">{a.description?.slice(0,100)}...</div>}
                      <div className="article-meta">
                        <span>{timeAgo(a.published_at)}</span>
                        <span className="check-hint">Click to check →</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar: Trending Topics */}
          <div className="sidebar-col">
            <div className="section-hd">Trending Topics</div>
            <div className="trending-list">
              {TRENDING_TOPICS.map(t => (
                <div key={t.rank} className="trend-item"
                  onClick={() => { setSearchInput(t.topic); setSearchQuery(t.topic); newsAPI.search(t.topic).then(r => setArticles(r.data.articles || [])).catch(()=>{}) }}>
                  <div className="trend-rank">#{t.rank}</div>
                  <div className="trend-body">
                    <div className="trend-topic">{t.topic}</div>
                    <div className="trend-heat">{t.heat} · {t.tag}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="sidebar-cta" onClick={() => navigate('/checker')}>
              <div className="cta-icon">🔍</div>
              <div>
                <div className="cta-title">Check Any News</div>
                <div className="cta-sub">Text, URL or Screenshot</div>
              </div>
              <div className="cta-arrow">→</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Mock fallback when API key not configured
const MOCK_ARTICLES = [
  { title: 'Pakistan economy shows signs of recovery amid IMF talks', description: 'Finance ministry officials met with IMF delegation to discuss latest economic indicators.', source: 'Dawn', published_at: new Date().toISOString(), url_to_image: null },
  { title: 'AI regulation summit concludes with landmark global agreement', description: 'Representatives from 40 countries signed an accord on responsible AI development.', source: 'Reuters', published_at: new Date(Date.now()-3600000).toISOString(), url_to_image: null },
  { title: 'Scientists discover new approach to treating antibiotic resistance', description: 'A team of researchers has found a novel mechanism to combat drug-resistant bacteria.', source: 'Nature', published_at: new Date(Date.now()-7200000).toISOString(), url_to_image: null },
  { title: 'Global markets react to central bank rate decisions', description: 'Major indices moved sharply as investors digested policy announcements from several central banks.', source: 'Bloomberg', published_at: new Date(Date.now()-10800000).toISOString(), url_to_image: null },
  { title: 'Tech giants face new antitrust investigations in EU', description: 'European regulators launched fresh probes into market dominance across digital platforms.', source: 'FT', published_at: new Date(Date.now()-14400000).toISOString(), url_to_image: null },
  { title: 'Climate summit sets new emissions reduction targets', description: 'World leaders agreed to accelerate carbon reduction timelines at this week\'s emergency summit.', source: 'Guardian', published_at: new Date(Date.now()-18000000).toISOString(), url_to_image: null },
]
