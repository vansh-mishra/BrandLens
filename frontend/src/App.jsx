import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight,
  BookOpen, Check, CheckCircle2, ChevronDown, ChevronRight, CircleHelp,
  Clock3, CloudUpload, FileCheck2, FileText, Filter, Gauge, History,
  LayoutDashboard, Leaf, LoaderCircle, MessageSquareText, MoreHorizontal,
  Plus, Search, ShieldCheck, Sparkles, Upload, X, XCircle, Users, LogOut, Copy, RefreshCw,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : window.location.origin)
const SAMPLE_BAD = "LUMALEAF'S MIRACLE SERUM IS 100% SUSTAINABLE!!! It is clinically proven to cure acne fast. Our chemical-free formula delivers guaranteed results."
const SAMPLE_GOOD = "Build a straightforward skincare routine with LumaLeaf. Calm Cleanser contains 2% niacinamide. Our refill pouch uses 70% less packaging plastic by weight than the standard 250 ml bottle."

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = sessionStorage.getItem('brandlens_token')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API}${path}`, { ...options, headers })
  const type = response.headers.get('content-type') || ''
  const data = type.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) throw new Error(data?.detail || data?.message || 'Request failed')
  return data
}

function cx(...classes) { return classes.filter(Boolean).join(' ') }
function roleLabel(role) { return ({ content_creator: 'Content creator', brand_reviewer: 'Brand reviewer', brand_admin: 'Workspace admin' })[role] || 'Workspace member' }
function dateLabel(value) {
  if (!value) return 'Just now'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' · ' + date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}
function shortText(value, length = 76) { return value?.length > length ? `${value.slice(0, length).trim()}…` : value }

function BrandMark({ small = false }) {
  return <div className={cx('brand-mark', small && 'brand-mark-small')}><ShieldCheck size={small ? 17 : 20} strokeWidth={2.1} /></div>
}

function NavButton({ active, icon: Icon, label, hint, onClick }) {
  return <button className={cx('nav-button', active && 'active')} onClick={onClick}>
    <Icon size={18} strokeWidth={1.9} /><span>{label}</span>{hint && <span className="nav-hint">{hint}</span>}
  </button>
}

function SectionTitle({ eyebrow, title, description, action }) {
  return <div className="section-title-row">
    <div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>
    {action}
  </div>
}

function StatCard({ label, value, change, icon: Icon, tone = 'blue' }) {
  return <div className="stat-card">
    <div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone}`}><Icon size={17} /></span></div>
    <div className="stat-value">{value}</div>
    {change && <div className="stat-foot"><span className="tiny-dot" />{change}</div>}
  </div>
}

function Severity({ value }) {
  const severity = (value || 'medium').toLowerCase()
  return <span className={`severity severity-${severity}`}>{severity}</span>
}

function ScoreRing({ score = 0 }) {
  const color = score >= 85 ? '#18836b' : score >= 60 ? '#bd7a20' : '#c34b4b'
  return <div className="score-ring" style={{ '--score': `${score * 3.6}deg`, '--ring-color': color }}>
    <div className="score-ring-inner"><strong>{score}</strong><span>of 100</span></div>
  </div>
}

function EmptyState({ icon: Icon = FileCheck2, title, text, action }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={24} /></div><h3>{title}</h3><p>{text}</p>{action}</div>
}

function FindingCard({ finding, onApply, disabled }) {
  return <article className="finding-card">
    <div className="finding-top"><div className="finding-icon"><AlertCircle size={16} /></div><div className="finding-heading"><div className="finding-title-row"><h3>{finding.title}</h3><Severity value={finding.severity} /></div><div className="finding-meta">{finding.category} <span>·</span> {Math.round((finding.confidence || 0) * 100)}% confidence</div></div></div>
    <div className="quoted-text">“{finding.quote}”</div>
    <p className="finding-explanation">{finding.explanation}</p>
    <div className="source-block"><div className="source-heading"><BookOpen size={14} /><span>Evidence</span><span className="source-verified"><CheckCircle2 size={12} /> Approved source</span></div><strong>{finding.source_title} <span>· {finding.source_section}</span></strong><p>{finding.source_excerpt}</p></div>
    <div className="suggestion-block"><div className="suggestion-head"><Sparkles size={14} /><span>Suggested correction</span></div><p>{finding.suggestion}</p><div className="suggestion-actions"><button className="button button-secondary button-sm" onClick={() => onApply(finding)} disabled={disabled}><Check size={14} /> Apply and recheck</button><span className="not-auto">Never applied automatically</span></div></div>
  </article>
}

function App() {
  const [page, setPage] = useState('studio')
  const [brand, setBrand] = useState(null)
  const [rules, setRules] = useState([])
  const [facts, setFacts] = useState([])
  const [guidelines, setGuidelines] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [reviews, setReviews] = useState([])
  const [content, setContent] = useState(SAMPLE_BAD)
  const [channel, setChannel] = useState('Instagram')
  const [review, setReview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [booting, setBooting] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [uploading, setUploading] = useState(false)
  const [authUser, setAuthUser] = useState(null)
  const [authChecking, setAuthChecking] = useState(true)
  const [authMode, setAuthMode] = useState('login')
  const [authBusy, setAuthBusy] = useState(false)
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '', invite_code: '' })
  const [teamMembers, setTeamMembers] = useState([])
  const [inviteCode, setInviteCode] = useState('')
  const [teamLoading, setTeamLoading] = useState(false)
  const role = roleLabel(authUser?.role)
  const [showNewRule, setShowNewRule] = useState(false)
  const [ruleDraft, setRuleDraft] = useState({ title: '', category: 'Brand guidelines', severity: 'medium', pattern: '', guidance: '', replacement: '', source_title: 'Uploaded brand guideline', source_section: 'Custom rule', source_excerpt: '' })


  useEffect(() => {
    let cancelled = false
    const token = sessionStorage.getItem('brandlens_token')
    if (!token) {
      setAuthChecking(false)
      setBooting(false)
      return () => { cancelled = true }
    }
    request('/api/auth/me')
      .then(data => { if (!cancelled) setAuthUser(data.user) })
      .catch(() => { sessionStorage.removeItem('brandlens_token'); if (!cancelled) setBooting(false) })
      .finally(() => { if (!cancelled) setAuthChecking(false) })
    return () => { cancelled = true }
  }, [])

  const authenticate = async (event) => {
    event.preventDefault()
    setAuthBusy(true); setError(''); setNotice('')
    try {
      const route = authMode === 'register' ? '/api/auth/register' : '/api/auth/login'
      const payload = authMode === 'register' ? authForm : { email: authForm.email, password: authForm.password }
      const data = await request(route, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      sessionStorage.setItem('brandlens_token', data.token)
      setAuthUser(data.user); setBooting(true)
      setAuthForm({ name: '', email: authForm.email, password: '', invite_code: '' })
      setPage('studio')
    } catch (e) { setError(e.message) } finally { setAuthBusy(false) }
  }

  const enterDemo = async () => {
    setAuthBusy(true); setError(''); setNotice('')
    try {
      const data = await request('/api/auth/demo', { method: 'POST' })
      sessionStorage.setItem('brandlens_token', data.token)
      setAuthUser(data.user); setBooting(true)
      setPage('studio')
    } catch (e) {
      setError(`Could not open the demo. Check that the BrandLens API is running. ${e.message}`)
    } finally { setAuthBusy(false) }
  }

  const signOut = () => {
    sessionStorage.removeItem('brandlens_token')
    setAuthUser(null); setReview(null); setReviews([]); setRules([]); setFacts([]); setGuidelines([]); setMetrics(null)
    setPage('studio'); setError(''); setNotice(''); setBooting(false)
  }

  const loadTeam = useCallback(async () => {
    setTeamLoading(true)
    try {
      const data = await request('/api/team')
      setTeamMembers(data.items || []); setInviteCode(data.invite_code || '')
    } catch (e) { setError(e.message) } finally { setTeamLoading(false) }
  }, [])

  const updateTeamRole = async (userId, nextRole) => {
    try {
      const data = await request(`/api/team/users/${userId}/role`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: nextRole }) })
      setTeamMembers(members => members.map(member => member.id === userId ? data.item : member))
      setNotice('Workspace role updated. The member must sign in again for the interface to refresh.')
    } catch (e) { setError(e.message) }
  }

  const refresh = useCallback(async () => {
    try {
      const [brandData, rulesData, factsData, guidelinesData, metricsData, reviewsData] = await Promise.all([
        request('/api/brand'), request('/api/rules'), request('/api/facts'), request('/api/guidelines'), request('/api/metrics'), request('/api/reviews?limit=50'),
      ])
      setBrand(brandData); setRules(rulesData.items || []); setFacts(factsData.items || [])
      setGuidelines(guidelinesData.items || []); setMetrics(metricsData); setReviews(reviewsData.items || [])
    } catch (e) {
      setError(`Cannot connect to the BrandLens API. Start the backend on port 8000. ${e.message}`)
    } finally { setBooting(false) }
  }, [])

  useEffect(() => { if (authUser) refresh() }, [authUser, refresh])
  useEffect(() => { if (page === 'team' && authUser?.role === 'brand_admin') loadTeam() }, [page, authUser, loadTeam])

  const startReview = async () => {
    if (content.trim().length < 5) { setError('Add at least a sentence to review.'); return }
    setBusy(true); setError(''); setNotice('')
    try {
      const data = await request('/api/reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content, channel }) })
      setReview(data); setContent(data.content); await refresh()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const loadReview = async (id) => {
    setBusy(true); setError('')
    try { const data = await request(`/api/reviews/${id}`); setReview(data); setContent(data.content); setChannel(data.channel); setPage('studio') }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const applyFix = async (finding) => {
    if (!review) return
    setBusy(true); setError(''); setNotice('')
    try {
      let revised = content
      if (finding.quote && revised.includes(finding.quote)) revised = revised.replace(finding.quote, finding.suggestion)
      else if (finding.quote && finding.quote.length > 12) revised = revised.replace(finding.quote.replace(/^…|…$/g, ''), finding.suggestion)
      else { setError('This finding needs a manual edit. Copy the suggested correction into the editor, then run the check again.'); setBusy(false); return }
      const data = await request(`/api/reviews/${review.id}/revise`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: revised }) })
      setReview(data); setContent(data.content); setNotice('Correction applied and the revised copy has been checked again. It still needs human approval.'); await refresh()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const makeDecision = async (decision) => {
    if (!review) return
    setBusy(true); setError(''); setNotice('')
    try {
      const data = await request(`/api/reviews/${review.id}/decision`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, reviewer: role === 'Content creator' ? 'Demo reviewer' : role, comment: decision === 'approved' ? 'Approved in the demonstration workspace.' : decision === 'rejected' ? 'Rejected in the demonstration workspace.' : 'Returned to creator for revision.' }) })
      setReview(data); setNotice(`Review marked “${decision.replace('_', ' ')}”. The decision has been added to the audit history.`); await refresh()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const uploadGuideline = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploading(true); setError(''); setNotice('')
    try {
      const form = new FormData(); form.append('file', file)
      const data = await request('/api/guidelines/upload', { method: 'POST', body: form })
      setNotice(`${data.item.filename} uploaded. Review the extracted text before adding any new live rule.`)
      await refresh()
    } catch (e) { setError(e.message) } finally { setUploading(false) }
  }

  const addRule = async (event) => {
    event.preventDefault(); setError(''); setNotice('')
    try {
      const data = await request('/api/rules', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(ruleDraft) })
      setRules(current => [...current, data.item]); setShowNewRule(false)
      setRuleDraft({ title: '', category: 'Brand guidelines', severity: 'medium', pattern: '', guidance: '', replacement: '', source_title: 'Uploaded brand guideline', source_section: 'Custom rule', source_excerpt: '' })
      setNotice('Brand rule added. New reviews will use this rule.')
    } catch (e) { setError(e.message) }
  }

  const filteredReviews = useMemo(() => reviews.filter(item => `${item.content} ${item.channel} ${item.status}`.toLowerCase().includes(search.toLowerCase())), [reviews, search])
  const issueCounts = review?.findings?.reduce((acc, f) => { acc[f.severity] = (acc[f.severity] || 0) + (f.status === 'open' ? 1 : 0); return acc }, {}) || {}

  if (authChecking || (authUser && booting)) return <div className="boot-screen"><BrandMark /><div><strong>Loading BrandLens</strong><span>Connecting to your review workspace…</span></div><LoaderCircle className="spin" size={20} /></div>

  if (!authUser) return <div className="auth-shell"><div className="auth-card"><div className="auth-brand"><BrandMark /><div><strong>BrandLens</strong><span>Brand governance workspace</span></div></div><div className="auth-eyebrow">PRE-PUBLICATION CONTENT REVIEW</div><h1>{authMode === 'register' ? 'Create your workspace' : 'Welcome to BrandLens'}</h1><p className="auth-intro">Explore the brand-review workflow without an account, or sign in to keep your team's workspace and review history.</p>{error && <div className="auth-error"><AlertCircle size={16}/><span>{error}</span></div>}<button className="button button-primary auth-demo-button" type="button" onClick={enterDemo} disabled={authBusy}>{authBusy ? <LoaderCircle className="spin" size={16}/> : <Sparkles size={16}/>} {authBusy ? 'Opening demo…' : 'Explore demo without signing up'} <ArrowRight size={15}/></button><p className="auth-demo-caption">Instant access to the sample brand, rules, review studio, library, history, and insights.</p><div className="auth-divider"><span>OR {authMode === 'register' ? 'CREATE AN ACCOUNT' : 'SIGN IN TO YOUR WORKSPACE'}</span></div><h2 className="auth-secondary-heading">{authMode === 'register' ? 'Create your workspace' : 'Sign in'}</h2><form className="auth-form" onSubmit={authenticate}>{authMode === 'register' && <label>Your name<input required minLength={2} maxLength={100} autoComplete="name" value={authForm.name} onChange={e => setAuthForm({ ...authForm, name: e.target.value })} placeholder="Full name" /></label>}<label>Work email<input type="email" required autoComplete="email" value={authForm.email} onChange={e => setAuthForm({ ...authForm, email: e.target.value })} placeholder="you@company.com" /></label><label>Password<input type="password" required minLength={authMode === 'register' ? 10 : 1} autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} value={authForm.password} onChange={e => setAuthForm({ ...authForm, password: e.target.value })} placeholder={authMode === 'register' ? 'At least 10 characters, letters and numbers' : 'Your password'} /></label>{authMode === 'register' && <label>Workspace invite code <span className="optional-label">Optional</span><input autoComplete="off" value={authForm.invite_code} onChange={e => setAuthForm({ ...authForm, invite_code: e.target.value })} placeholder="Enter code to join a teammate" /><small>Leave blank to create a new workspace as its administrator.</small></label>}<button className="button button-secondary auth-submit" type="submit" disabled={authBusy}>{authBusy ? <LoaderCircle className="spin" size={16}/> : <ShieldCheck size={16}/>} {authBusy ? 'Please wait…' : authMode === 'register' ? 'Create account' : 'Sign in'} <ArrowRight size={15}/></button></form><div className="auth-switch">{authMode === 'register' ? 'Already have an account?' : 'Want a saved workspace?'} <button onClick={() => { setAuthMode(authMode === 'register' ? 'login' : 'register'); setError('') }}>{authMode === 'register' ? 'Sign in' : 'Create account'}</button></div><div className="auth-footnote"><ShieldCheck size={14}/> Demo mode uses sample data. Sign in for a persistent team workspace.</div></div></div>

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand-lockup"><BrandMark /><div><strong>BrandLens</strong><span>Brand governance</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <button className="workspace-switch"><span className="workspace-avatar"><Leaf size={16} /></span><span className="workspace-copy"><strong>{brand?.name || 'LumaLeaf'}</strong><small>Team workspace</small></span><ChevronDown size={15} /></button>
      <div className="nav-group"><div className="nav-caption">WORKSPACE</div>
        <NavButton active={page === 'overview'} icon={LayoutDashboard} label="Overview" onClick={() => setPage('overview')} />
        <NavButton active={page === 'studio'} icon={FileCheck2} label="Review studio" hint="" onClick={() => setPage('studio')} />
        <NavButton active={page === 'library'} icon={BookOpen} label="Brand library" onClick={() => setPage('library')} />
        <NavButton active={page === 'history'} icon={History} label="Review history" onClick={() => setPage('history')} />
        <NavButton active={page === 'analytics'} icon={Activity} label="Insights" onClick={() => setPage('analytics')} />
        {authUser.role === 'brand_admin' && !authUser.is_demo && <NavButton active={page === 'team'} icon={Users} label="Team access" onClick={() => setPage('team')} />}
      </div>
      <div className="sidebar-bottom">
        <div className="compliance-card"><div className="compliance-icon"><ShieldCheck size={18} /></div><strong>Human-led by design</strong><p>AI flags potential issues. Your team owns the final decision.</p><button onClick={() => setPage('library')}>View brand rules <ArrowRight size={13} /></button></div>
        <div className="user-profile"><div className="avatar">{(authUser.name || 'BL').split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase()}</div><div className="user-details"><strong>{authUser.name}</strong><span>{role}</span></div><button className="logout-button" title={authUser.is_demo ? "Exit demo" : "Sign out"} onClick={signOut}><LogOut size={15}/></button></div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumb"><span>{authUser.workspace_name || 'Workspace'}</span><ChevronRight size={14} /><strong>{({ overview: 'Overview', studio: 'Review studio', library: 'Brand library', history: 'Review history', analytics: 'Insights', team: 'Team access' })[page]}</strong></div><div className="topbar-right"><div className="secure-status"><span className="status-dot" /> {authUser.is_demo ? 'Demo session · sample data' : 'Authenticated workspace'}</div><div className="signed-in-user"><strong>{authUser.is_demo ? 'Demo visitor' : authUser.name}</strong><span>{authUser.is_demo ? 'No account required' : role}</span></div><button className="icon-only help-button" title="About BrandLens" onClick={() => setNotice('BrandLens findings are advisory. A workspace reviewer makes the final publication decision.')}><CircleHelp size={18} /></button><button className="icon-only help-button top-signout" title={authUser.is_demo ? "Exit demo" : "Sign out"} onClick={signOut}><LogOut size={17}/></button></div></header>
      <div className="content-area">
        {error && <div className="alert alert-error"><AlertCircle size={17} /><span>{error}</span><button onClick={() => setError('')}><X size={15} /></button></div>}
        {notice && <div className="alert alert-success"><CheckCircle2 size={17} /><span>{notice}</span><button onClick={() => setNotice('')}><X size={15} /></button></div>}

        {page === 'studio' && <>
          <SectionTitle eyebrow="CONTENT QUALITY CONTROL" title="Review before you publish" description="Check every claim against approved brand rules and facts." action={<div className="review-id-pill"><span className="status-dot" />{review ? `Review ${review.id.slice(0, 8)}` : 'New review'}</div>} />
          <div className="studio-toolbar"><div className="example-label"><Sparkles size={14} /> Try a sample</div><button className="sample-chip" onClick={() => { setContent(SAMPLE_BAD); setReview(null); setNotice('Loaded the sample containing seeded brand issues. Run the check to see source-linked findings.'); }}>Problematic copy <span className="sample-dot red" /></button><button className="sample-chip" onClick={() => { setContent(SAMPLE_GOOD); setReview(null); setNotice('Loaded the compliant example with approved facts. Run the check to validate it.'); }}>Compliant copy <span className="sample-dot green" /></button><span className="toolbar-spacer" /><span className="rules-count"><ShieldCheck size={14} /> {rules.length} active rules</span></div>
          <div className="studio-grid">
            <section className="panel editor-panel">
              <div className="panel-header"><div><div className="panel-kicker">STEP 01</div><h2>Content to review</h2><p>Paste the exact copy you plan to publish.</p></div><span className="file-label"><FileText size={14} /> Text review</span></div>
              <div className="field-row"><label htmlFor="channel">Publishing channel</label><div className="select-wrap"><select id="channel" value={channel} onChange={e => setChannel(e.target.value)}><option>Instagram</option><option>Website</option><option>Email campaign</option><option>Paid advertisement</option><option>Product page</option><option>Press release</option></select><ChevronDown size={14} /></div></div>
              <textarea className="content-editor" value={content} onChange={e => { setContent(e.target.value); if (review) setReview(null) }} maxLength={12000} placeholder="Paste campaign copy, a product description, or a social post…" aria-label="Content to review" />
              <div className="editor-footer"><span>{content.length} characters <span className="muted-divider">·</span> {content.trim() ? content.trim().split(/\s+/).length : 0} words</span><span className="privacy-note"><ShieldCheck size={13} /> Demo content only</span></div>
              <div className="editor-controls"><button className="button button-primary" onClick={startReview} disabled={busy || content.trim().length < 5}>{busy ? <LoaderCircle size={16} className="spin" /> : <Sparkles size={16} />}{busy ? 'Checking content…' : review ? 'Run review again' : 'Run brand check'}<ArrowRight size={15} /></button><button className="button button-ghost" onClick={() => { setContent(''); setReview(null); setNotice('Editor cleared.'); }}>Clear</button></div>
              <div className="workflow-note"><div className="workflow-note-icon"><ShieldCheck size={16} /></div><p><strong>Evidence over guesswork.</strong> Findings cite the configured brand rules. A missing source is labelled unverified, not automatically false.</p></div>
            </section>

            <section className="panel results-panel">
              {!review ? <>
                <div className="panel-header results-header"><div><div className="panel-kicker">STEP 02</div><h2>Review results</h2><p>Your findings will appear here.</p></div><span className="waiting-pill"><Clock3 size={13} /> Awaiting check</span></div>
                <div className="results-empty"><div className="empty-orbit"><div className="orbit-dot orbit-dot-one" /><div className="orbit-dot orbit-dot-two" /><ShieldCheck size={34} /></div><h3>Ready for a brand check</h3><p>Run the review to surface terminology violations, unsupported claims, and tone-of-voice issues with their sources.</p><div className="checks-preview"><div><CheckCircle2 size={15} /><span>Approved terminology</span></div><div><CheckCircle2 size={15} /><span>Claim evidence</span></div><div><CheckCircle2 size={15} /><span>Voice and tone</span></div></div></div>
                <div className="result-legend"><span><i className="legend-dot critical" />Critical</span><span><i className="legend-dot high" />High</span><span><i className="legend-dot medium" />Medium</span><span><i className="legend-dot low" />Low</span></div>
              </> : <>
                <div className="panel-header results-header"><div><div className="panel-kicker">REVIEW COMPLETE</div><h2>Brand alignment</h2><p>{review.summary}</p></div><span className={`status-pill status-${review.status}`}>{review.status.replace('_', ' ')}</span></div>
                <div className="score-summary"><ScoreRing score={review.score} /><div className="score-details"><strong>{review.score >= 85 ? 'Looks on-brand' : review.score >= 60 ? 'Needs a closer look' : 'Action required'}</strong><p>Alignment score is a heuristic based on configured findings, not a legal or factual certification.</p><div className="mini-severity-list">{['critical', 'high', 'medium', 'low'].map(level => <span key={level}><i className={`legend-dot ${level}`} />{issueCounts[level] || 0} {level}</span>)}</div></div></div>
                <div className="result-details"><div className="result-detail-row"><span>Publishing channel</span><strong>{review.channel}</strong></div><div className="result-detail-row"><span>Last checked</span><strong>{dateLabel(review.updated_at || review.created_at)}</strong></div><div className="result-detail-row"><span>Findings</span><strong>{review.findings?.filter(f => f.status === 'open').length || 0} open</strong></div></div>
                <div className="result-actions"><button className="button button-primary" disabled={busy || role === 'Content creator'} onClick={() => makeDecision('approved')}><Check size={15} /> Approve content</button><button className="button button-secondary" disabled={busy || role === 'Content creator'} onClick={() => makeDecision('needs_revision')}><MessageSquareText size={15} /> Request revision</button><button className="button button-ghost button-icon-only" title="Reject content" disabled={busy || role === 'Content creator'} onClick={() => makeDecision('rejected')}><XCircle size={16} /></button></div>
                {role === 'Content creator' && <div className="role-note"><ShieldCheck size={14} /> Switch to “Brand reviewer” in the sidebar to test the approval controls.</div>}
              </>}
            </section>
          </div>
          {review && <section className="findings-section"><div className="findings-heading"><div><div className="panel-kicker">STEP 03</div><h2>Findings and evidence <span className="count-bubble">{review.findings?.length || 0}</span></h2><p>Each flag links to a configured rule or claims policy. Review suggestions before applying them.</p></div><button className="button button-secondary button-sm" onClick={() => { const blob = new Blob([JSON.stringify({ brand: brand?.name, review }, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `brandlens-review-${review.id.slice(0, 8)}.json`; link.click(); URL.revokeObjectURL(url); }}><ArrowDownRight size={14} /> Export report</button></div>
            {review.findings?.length ? <div className="findings-grid">{review.findings.map(f => <FindingCard key={f.id} finding={f} onApply={applyFix} disabled={busy || role !== 'Content creator'} />)}</div> : <div className="clean-result"><CheckCircle2 size={21} /><div><strong>No configured issues detected</strong><p>That is not a guarantee that every statement is accurate. Verify source material and have a reviewer approve the copy.</p></div></div>}
            <div className="human-review-banner"><div className="human-review-icon"><ShieldCheck size={18} /></div><div><strong>Human approval remains mandatory</strong><p>BrandLens never publishes or approves content automatically. Review every finding, including false positives and low-confidence flags.</p></div><span className="human-badge">HUMAN-IN-THE-LOOP</span></div>
          </section>}
        </>}

        {page === 'overview' && <>
          <SectionTitle eyebrow="WORKSPACE OVERVIEW" title="Brand health at a glance" description="A lightweight view of your review activity and unresolved issues." action={<button className="button button-primary" onClick={() => setPage('studio')}><Plus size={16} /> New review</button>} />
          <div className="stats-grid"><StatCard label="Total reviews" value={metrics?.total_reviews ?? 0} change="Across this demo workspace" icon={FileCheck2} tone="blue" /><StatCard label="Awaiting decision" value={metrics?.pending_reviews ?? 0} change="Pending or returned for revision" icon={Clock3} tone="amber" /><StatCard label="Average alignment" value={`${metrics?.average_score ?? 0}/100`} change="Heuristic score, not certification" icon={Gauge} tone="green" /><StatCard label="Open findings" value={metrics?.open_findings ?? 0} change="Still marked for review" icon={AlertCircle} tone="rose" /></div>
          <div className="overview-grid"><section className="panel"><div className="panel-header"><div><h2>Recent reviews</h2><p>Latest content checked in BrandLens.</p></div><button className="text-button" onClick={() => setPage('history')}>View all <ArrowRight size={14} /></button></div><ReviewTable reviews={metrics?.recent_reviews || []} onOpen={loadReview} /></section><section className="panel health-panel"><div className="panel-header"><div><h2>Brand guardrails</h2><p>Current policy coverage.</p></div><ShieldCheck className="panel-head-icon" size={19} /></div><div className="guardrail-summary"><div className="guardrail-number">{rules.length}<span> active rules</span></div><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.min(100, rules.length * 10)}%` }} /></div></div><div className="guardrail-list">{[{ label: 'Claims & evidence', sub: 'Unsupported or absolute claims', icon: AlertCircle }, { label: 'Terminology', sub: 'Approved words and phrases', icon: BookOpen }, { label: 'Tone of voice', sub: 'Brand personality and style', icon: MessageSquareText }].map(item => <div className="guardrail-item" key={item.label}><span className="guardrail-item-icon"><item.icon size={16} /></span><div><strong>{item.label}</strong><small>{item.sub}</small></div><ChevronRight size={15} /></div>)}</div><button className="button button-secondary full-width" onClick={() => setPage('library')}>Manage brand library</button></section></div>
        </>}

        {page === 'library' && <>
          <SectionTitle eyebrow="SOURCE OF TRUTH" title="Brand library" description="The approved rules and facts used to ground every review. This workspace uses a fictional demo brand." action={<label className="button button-secondary upload-button"><Upload size={15} />{uploading ? 'Uploading…' : 'Upload guideline'}<input type="file" accept=".txt,.md,.csv,.pdf" onChange={uploadGuideline} disabled={uploading} hidden /></label>} />
          <div className="library-banner"><div className="library-banner-icon"><Leaf size={21} /></div><div><strong>{brand?.name || 'LumaLeaf'} · Demo brand</strong><p>{brand?.description} These example rules and facts are fictional and should be replaced with your organisation's approved materials for real use.</p></div><span className="demo-chip">SAMPLE DATA</span></div>
          <div className="library-stats"><div><span>Active rules</span><strong>{rules.length}</strong></div><div><span>Approved facts</span><strong>{facts.length}</strong></div><div><span>Uploaded documents</span><strong>{guidelines.length}</strong></div></div>
          <section className="panel library-panel"><div className="panel-header"><div><h2>Active brand rules</h2><p>Every rule includes a source passage and guidance.</p></div>{role !== 'Content creator' && <button className="button button-secondary button-sm" onClick={() => setShowNewRule(!showNewRule)}>{showNewRule ? <X size={14} /> : <Plus size={14} />}{showNewRule ? 'Cancel' : 'Add rule'}</button>}</div>
            {showNewRule && <form className="rule-form" onSubmit={addRule}><div className="form-grid"><label>Rule title<input required minLength="3" value={ruleDraft.title} onChange={e => setRuleDraft({ ...ruleDraft, title: e.target.value })} placeholder="e.g. Avoid unverified superlatives" /></label><label>Category<select value={ruleDraft.category} onChange={e => setRuleDraft({ ...ruleDraft, category: e.target.value })}><option>Brand guidelines</option><option>Terminology</option><option>Claims & evidence</option><option>Tone of voice</option><option>Accessibility</option></select></label><label>Severity<select value={ruleDraft.severity} onChange={e => setRuleDraft({ ...ruleDraft, severity: e.target.value })}><option>low</option><option>medium</option><option>high</option><option>critical</option></select></label><label>Match pattern (regex)<input required value={ruleDraft.pattern} onChange={e => setRuleDraft({ ...ruleDraft, pattern: e.target.value })} placeholder="e.g. \\b(?:guaranteed|miracle)\\b" /></label><label className="wide-field">Why it is a problem<textarea required value={ruleDraft.guidance} onChange={e => setRuleDraft({ ...ruleDraft, guidance: e.target.value })} /></label><label className="wide-field">Approved source excerpt<textarea required value={ruleDraft.source_excerpt} onChange={e => setRuleDraft({ ...ruleDraft, source_excerpt: e.target.value })} /></label><label className="wide-field">Suggested correction<input value={ruleDraft.replacement} onChange={e => setRuleDraft({ ...ruleDraft, replacement: e.target.value })} /></label></div><button className="button button-primary" type="submit"><Plus size={15} /> Save active rule</button><p className="form-footnote">The match pattern is a regular expression. Use an exact and testable pattern to avoid unnecessary false positives.</p></form>}
            <div className="rules-list">{rules.map(rule => <article className="rule-row" key={rule.id}><div className="rule-type-icon"><BookOpen size={17} /></div><div className="rule-body"><div className="rule-row-title"><h3>{rule.title}</h3><Severity value={rule.severity} /></div><p>{rule.guidance}</p><div className="rule-source"><BookOpen size={12} /> {rule.source_title} · {rule.source_section}</div><div className="rule-source-quote">“{rule.source_excerpt}”</div></div><span className="rule-id">{rule.id}</span></article>)}</div>
          </section>
          <section className="panel facts-panel"><div className="panel-header"><div><h2>Approved facts</h2><p>Use the precise scope of each fact in marketing copy.</p></div><span className="source-verified"><CheckCircle2 size={13} /> Approved for demo</span></div><div className="facts-grid">{facts.map(fact => <div className="fact-card" key={fact.id}><div className="fact-id">{fact.id}</div><strong>{fact.title}</strong><p>{fact.content}</p><span>{fact.source_title} · {fact.source_section}</span></div>)}</div></section>
          <section className="panel facts-panel"><div className="panel-header"><div><h2>Uploaded guidelines</h2><p>Files are stored for inspection. New rules are not activated automatically.</p></div></div>{guidelines.length ? <div className="uploaded-list">{guidelines.map(file => <div className="uploaded-row" key={file.id}><span className="uploaded-file-icon"><FileText size={17} /></span><div><strong>{file.filename}</strong><small>{file.characters.toLocaleString()} characters · uploaded {dateLabel(file.created_at)}</small></div><span className="review-manually">Review manually</span></div>)}</div> : <div className="upload-empty"><CloudUpload size={22} /><div><strong>No custom guidelines uploaded</strong><p>Upload a .txt, .md, .csv, or text-based PDF to save the document for review.</p></div></div>}</section>
        </>}

        {page === 'history' && <>
          <SectionTitle eyebrow="AUDIT TRAIL" title="Review history" description="Find the version that was checked and inspect its findings and decisions." action={<button className="button button-primary" onClick={() => setPage('studio')}><Plus size={16} /> New review</button>} />
          <div className="history-toolbar"><div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search content, channel or status" /></div><span className="table-count">{filteredReviews.length} review{filteredReviews.length === 1 ? '' : 's'}</span></div>
          <section className="panel history-panel">{filteredReviews.length ? <ReviewTable reviews={filteredReviews} onOpen={loadReview} showFindings /> : <EmptyState icon={History} title="No matching reviews" text="Run a content check or change your search to see the audit trail." action={<button className="button button-primary" onClick={() => { setSearch(''); setPage('studio') }}>Open review studio</button>} />}</section>
        </>}

        {page === 'analytics' && <>
          <SectionTitle eyebrow="QUALITY INSIGHTS" title="Insights" description="Understand recurring issues in the current demo workspace. More advanced trend analysis is planned for Round 3." action={<button className="button button-secondary" onClick={refresh}><Activity size={15} /> Refresh data</button>} />
          <div className="stats-grid"><StatCard label="Content reviewed" value={metrics?.total_reviews ?? 0} icon={FileCheck2} tone="blue" /><StatCard label="Approved reviews" value={metrics?.approved_reviews ?? 0} icon={CheckCircle2} tone="green" /><StatCard label="Pending decisions" value={metrics?.pending_reviews ?? 0} icon={Clock3} tone="amber" /><StatCard label="Open findings" value={metrics?.open_findings ?? 0} icon={AlertCircle} tone="rose" /></div>
          <div className="overview-grid"><section className="panel"><div className="panel-header"><div><h2>Open findings by severity</h2><p>Counts from reviewed content.</p></div></div><div className="severity-chart">{['critical', 'high', 'medium', 'low'].map(level => { const count = metrics?.by_severity?.[level] || 0; const max = Math.max(1, ...Object.values(metrics?.by_severity || {})); return <div className="chart-row" key={level}><div className="chart-label"><Severity value={level} /></div><div className="chart-track"><div className={`chart-bar ${level}`} style={{ width: `${count ? Math.max(5, (count / max) * 100) : 0}%` }} /></div><strong>{count}</strong></div> })}</div><p className="chart-caption">This chart reflects the demo database only. It is not a benchmark of real-world accuracy.</p></section><section className="panel"><div className="panel-header"><div><h2>Review principles</h2><p>How BrandLens should be evaluated.</p></div><ShieldCheck className="panel-head-icon" size={19} /></div><div className="principle-list">{[{ n: '01', title: 'Ground every finding', text: 'The reviewer can inspect the exact approved rule passage.' }, { n: '02', title: 'Separate facts from suspicion', text: 'A missing source is labelled unverified, not false.' }, { n: '03', title: 'Keep a human in control', text: 'Suggestions never publish or approve content by themselves.' }, { n: '04', title: 'Measure before claiming', text: 'Accuracy and time saved need a labelled test set and baseline.' }].map(p => <div className="principle-item" key={p.n}><span>{p.n}</span><div><strong>{p.title}</strong><p>{p.text}</p></div></div>)}</div></section></div>
          <section className="panel"><div className="panel-header"><div><h2>Recent review activity</h2><p>Review status and alignment score.</p></div><button className="text-button" onClick={() => setPage('history')}>Open history <ArrowRight size={14} /></button></div><ReviewTable reviews={metrics?.recent_reviews || []} onOpen={loadReview} /></section>
        </>}

        {page === 'team' && authUser.role === 'brand_admin' && <>
          <SectionTitle eyebrow="WORKSPACE ADMINISTRATION" title="Team access" description="Invite teammates and assign the permissions required for their role." action={<button className="button button-secondary" onClick={loadTeam} disabled={teamLoading}><RefreshCw size={15}/> Refresh team</button>} />
          <section className="panel team-panel"><div className="panel-header"><div><div className="panel-kicker">INVITATION</div><h2>Invite a teammate</h2><p>Share this code only with people who should access this workspace.</p></div><span className="waiting-pill"><ShieldCheck size={13}/> Workspace private</span></div><div className="invite-code-row"><code>{inviteCode || 'Loading invite code…'}</code><button className="button button-secondary button-sm" onClick={() => { navigator.clipboard?.writeText(inviteCode); setNotice('Workspace invite code copied.'); }} disabled={!inviteCode}><Copy size={14}/> Copy code</button></div><p className="team-hint">New teammates should select Create account and enter this code. Their default role is Content creator.</p></section>
          <section className="panel team-panel"><div className="panel-header"><div><div className="panel-kicker">MEMBERS</div><h2>Workspace members</h2><p>Only workspace administrators can change member permissions.</p></div><span className="count-bubble">{teamMembers.length}</span></div>{teamLoading ? <div className="team-loading"><LoaderCircle className="spin" size={18}/> Loading team members…</div> : <div className="team-list">{teamMembers.map(member => <div className="team-member" key={member.id}><div className="avatar">{member.name.split(/\s+/).map(part => part[0]).join('').slice(0,2).toUpperCase()}</div><div className="team-member-main"><strong>{member.name}</strong><span>{member.email}</span></div><span className="member-date">Joined {dateLabel(member.created_at)}</span><select aria-label={`Role for ${member.name}`} value={member.role} onChange={e => updateTeamRole(member.id, e.target.value)} disabled={member.id === authUser.id}><option value="content_creator">Content creator</option><option value="brand_reviewer">Brand reviewer</option><option value="brand_admin">Workspace admin</option></select></div>)}</div>}</section>
        </>}

        <footer className="footer"><span>BrandLens <span className="footer-dot">·</span> Evidence-backed brand governance</span><span><ShieldCheck size={13} /> Prototype · {rules.length} active rules</span></footer>
      </div>
    </main>
  </div>
}

function ReviewTable({ reviews, onOpen, showFindings = false }) {
  if (!reviews?.length) return <EmptyState icon={FileText} title="No reviews yet" text="Run your first brand check to create a review record and populate this workspace." />
  return <div className="table-wrap"><table className="review-table"><thead><tr><th>Content</th><th>Channel</th>{showFindings && <th>Findings</th>}<th>Score</th><th>Status</th><th>Last updated</th><th /></tr></thead><tbody>{reviews.map(item => <tr key={item.id}><td><div className="content-cell"><strong>{shortText(item.content || item.preview || 'Untitled review', 58)}</strong><small>BL-{item.id.slice(0, 8).toUpperCase()}</small></div></td><td>{item.channel}</td>{showFindings && <td>{item.finding_count ?? '—'}</td>}<td><span className={`score-text ${item.score >= 85 ? 'good' : item.score >= 60 ? 'warn' : 'bad'}`}>{item.score}/100</span></td><td><span className={`status-pill status-${item.status}`}>{(item.status || 'pending').replace('_', ' ')}</span></td><td className="date-cell">{dateLabel(item.updated_at || item.created_at)}</td><td><button className="row-open" title="Open review" onClick={() => onOpen(item.id)}><ArrowRight size={15} /></button></td></tr>)}</tbody></table></div>
}

export default App
