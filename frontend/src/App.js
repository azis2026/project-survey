import { useCallback, useEffect, useMemo, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate, useLocation, useParams } from "react-router-dom";
import axios from "axios";
import { BarChart3, Check, ChevronLeft, Download, FileSpreadsheet, FileText, Image as ImageIcon, Layers, LogOut, Mail, Menu, MessageSquare, Palette, Pencil, Plus, QrCode, Send, Settings, ShieldCheck, Star, Trash2, TrendingUp, Users as UsersIcon, UserPlus, X } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "@/App.css";

const API = `${process.env.REACT_APP_BACKEND_URL || ""}/api`;
const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("survey_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
const labels = ["Sangat Tidak Puas", "Tidak Puas", "Cukup Puas", "Puas", "Sangat Puas"];
const fmt = (date) => new Date(date).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
const today = () => new Date().toISOString().slice(0, 10);
const daysAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); };

function BrandMark({ branding, dark = false }) {
  const name = branding?.institution_name || "Survey Kepuasan Layanan";
  const accent = branding?.accent_color || "#2563eb";
  return <div className={`brand ${dark ? "brand-dark" : ""}`}>
    {branding?.logo_data_url ? <img src={branding.logo_data_url} alt={name} className="brand-logo"/> : <span className="brand-mark" style={{background: accent}}><ShieldCheck size={20}/></span>}
    <span>{name}</span>
  </div>;
}

function PublicSurvey() {
  const { slug: slugParam } = useParams();
  const slug = slugParam || "pelayanan-umum";
  const [survey, setSurvey] = useState(null);
  const [branding, setBranding] = useState(null);
  const [started, setStarted] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [missing, setMissing] = useState(false);
  useEffect(() => {
    api.get(`/survey/${slug}`).then(r => setSurvey(r.data)).catch(() => setMissing(true));
    api.get("/branding").then(r => setBranding(r.data)).catch(() => {});
  }, [slug]);
  useEffect(() => {
    if (branding?.accent_color) document.documentElement.style.setProperty("--brand", branding.accent_color);
  }, [branding]);
  const submit = async () => {
    if (!rating) { setError("Silakan pilih tingkat kepuasan terlebih dahulu."); return; }
    setLoading(true); setError("");
    try { await api.post("/responses", { survey_id: survey.id, rating, comment }); setSubmitted(true); }
    catch (e) { setError(e.response?.data?.detail || "Maaf, terjadi kendala saat mengirim survey. Silakan coba lagi."); }
    finally { setLoading(false); }
  };
  if (submitted) return <main className="public-shell"><div className="success-screen" data-testid="thank-you-screen"><div className="success-icon"><Check size={40} /></div><p className="eyebrow">Tanggapan tersimpan</p><h1 data-testid="thank-you-title">Terima Kasih!</h1><p>Terima kasih telah meluangkan waktu untuk memberikan penilaian dan saran kepada kami.</p><p>Masukan Anda sangat membantu kami dalam meningkatkan kualitas pelayanan.</p><button className="button primary" data-testid="survey-done-button" onClick={() => window.location.reload()}>Selesai</button></div></main>;
  if (missing) return <main className="public-shell"><div className="empty-panel"><ShieldCheck size={34}/><h1>Survey sedang tidak tersedia.</h1><p>Silakan kembali lagi nanti.</p></div></main>;
  if (!survey) return <main className="public-shell"><div className="loading-state" data-testid="survey-loading">Memuat survey...</div></main>;
  if (survey.status !== "active") return <main className="public-shell"><div className="empty-panel"><ShieldCheck size={34}/><h1>Survey sedang tidak tersedia.</h1><p>Silakan kembali lagi nanti.</p></div></main>;
  const brandName = branding?.institution_name || "Survey Kepuasan Layanan";
  return <main className="public-shell"><div className="public-top"><BrandMark branding={branding}/><span className="privacy-note"><ShieldCheck size={14}/> Anonymous survey</span></div><section className={`survey-stage ${started ? "is-started" : ""}`}><div className="survey-copy"><p className="eyebrow">PENGALAMAN ANDA BERARTI</p><h1 data-testid="survey-title">{survey.title}</h1><p data-testid="survey-description">{survey.description}</p>{!started && <button className="button primary large" data-testid="start-survey-button" onClick={() => setStarted(true)}>Mulai Survey <ChevronLeft className="rotate-180" size={18}/></button>}</div><div className="survey-card" data-testid="survey-form"><div className="card-top"><span className="mini-brand">{brandName.slice(0,3).toUpperCase()}</span><span>{survey.title.slice(0, 32)}</span></div>{!started ? <div className="preview-state"><div className="preview-stars"><Star fill="currentColor"/><Star fill="currentColor"/><Star fill="currentColor"/><Star fill="currentColor"/><Star fill="currentColor"/></div><h2>Penilaian singkat,<br/>perubahan berarti.</h2><p>Hanya perlu beberapa detik untuk membantu kami melayani lebih baik.</p></div> : <div className="rating-flow"><p className="eyebrow">PENILAIAN KEPUASAN</p><h2 data-testid="survey-question">{survey.question}</h2><div className="star-picker" role="radiogroup" aria-label="Pilih rating kepuasan">{[1,2,3,4,5].map(n => <button key={n} className={`star-button ${rating >= n ? "active" : ""}`} data-testid={`rating-${n}-button`} aria-label={`${n} bintang, ${labels[n-1]}`} onClick={() => setRating(n)}><Star fill={rating >= n ? "currentColor" : "none"}/></button>)}</div><div className={`rating-label ${rating ? "visible" : ""}`} data-testid="rating-label">{rating ? labels[rating-1] : "Pilih rating Anda"}</div><label className="field-label" htmlFor="comment">Ada saran atau komentar? <span>(opsional)</span></label><textarea id="comment" data-testid="survey-comment-input" value={comment} maxLength={survey.max_comment_length} onChange={e => setComment(e.target.value)} placeholder={survey.comment_placeholder}/><div className="char-count" data-testid="comment-character-count">{comment.length} / {survey.max_comment_length}</div>{error && <div className="error-message" data-testid="survey-error">{error}</div>}<button className="button primary submit-button" data-testid="submit-survey-button" disabled={loading} onClick={submit}>{loading ? "Mengirim..." : "Kirim Survey"}<ChevronLeft className="rotate-180" size={18}/></button><p className="privacy-foot"><ShieldCheck size={14}/> Tidak meminta data pribadi</p></div>}</div></section><footer className="public-footer">{brandName} <span>•</span> Masukan Anda membantu kami bertumbuh</footer></main>;
}

function AdminLogin({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const go = useNavigate();
  const submit = async e => {
    e.preventDefault(); setLoading(true); setError("");
    try {
      const r = await api.post("/auth/login", { email, password });
      if (r.data?.token) {
        localStorage.setItem("survey_access_token", r.data.token);
      }
      onLogin(r.data);
      go("/admin");
    }
    catch (err) { setError(err.response?.data?.detail || "Username atau password salah."); }
    finally { setLoading(false); }
  };
  return <main className="auth-shell"><div className="auth-panel"><BrandMark/><div className="auth-heading"><span className="icon-box"><ShieldCheck size={22}/></span><p className="eyebrow">AREA TERBATAS</p><h1>Admin Survey</h1><p>Kelola tanggapan dan lihat perkembangan kualitas pelayanan.</p></div><form onSubmit={submit} data-testid="admin-login-form" autoComplete="on"><label className="field-label" htmlFor="email">Username / Email</label><input id="email" data-testid="admin-email-input" value={email} onChange={e => setEmail(e.target.value)} type="email" autoComplete="username" required/><label className="field-label" htmlFor="password">Password</label><div className="password-wrap"><input id="password" data-testid="admin-password-input" value={password} onChange={e => setPassword(e.target.value)} type={show ? "text" : "password"} autoComplete="current-password" required/><button type="button" className="icon-button password-toggle" data-testid="toggle-password-button" onClick={() => setShow(!show)} aria-label="Tampilkan password">{show ? <X size={18}/> : <ShieldCheck size={18}/>}</button></div>{error && <div className="error-message" data-testid="login-error">{error}</div>}<button className="button primary full" data-testid="admin-login-submit" disabled={loading}>{loading ? "Memeriksa..." : "Masuk"}</button></form><Link className="back-link" to="/">Kembali ke survey publik</Link></div></main>;
}

function ChangePasswordModal({ open, onClose }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (!open) { setCurrent(""); setNext(""); setConfirm(""); setError(""); setOk(false); } }, [open]);
  if (!open) return null;
  const submit = async e => {
    e.preventDefault(); setError("");
    if (next.length < 8) { setError("Password baru minimal 8 karakter."); return; }
    if (next !== confirm) { setError("Konfirmasi password tidak cocok."); return; }
    setSaving(true);
    try { await api.post("/auth/change-password", { current_password: current, new_password: next }); setOk(true); setTimeout(onClose, 1500); }
    catch (err) { setError(err.response?.data?.detail || "Tidak dapat mengubah password."); }
    finally { setSaving(false); }
  };
  return <div className="modal-backdrop" onClick={onClose}><div className="editor-modal" onClick={e => e.stopPropagation()} data-testid="change-password-modal" style={{maxWidth:460}}><button type="button" className="icon-button close-modal" onClick={onClose}><X size={18}/></button><p className="eyebrow">KEAMANAN AKUN</p><h2>Ubah password</h2><form onSubmit={submit} className="editor-form"><label className="field-label full-field">Password saat ini<input type="password" autoComplete="current-password" value={current} onChange={e => setCurrent(e.target.value)} data-testid="current-password-input" required/></label><label className="field-label full-field">Password baru<input type="password" autoComplete="new-password" minLength={8} value={next} onChange={e => setNext(e.target.value)} data-testid="new-password-input" required/></label><label className="field-label full-field">Konfirmasi password baru<input type="password" autoComplete="new-password" minLength={8} value={confirm} onChange={e => setConfirm(e.target.value)} data-testid="confirm-password-input" required/></label>{error && <div className="error-message full-field">{error}</div>}{ok && <div className="toast-banner inline full-field" style={{gridColumn:"1/-1"}}><Check size={16}/> Password berhasil diubah.</div>}<div className="settings-actions"><button type="button" className="button secondary" onClick={onClose}>Batal</button><button className="button primary" data-testid="save-password-button" disabled={saving || ok}>{saving ? "Menyimpan..." : "Simpan Password"}</button></div></form></div></div>;
}

function Sidebar({ user, branding, onLogout }) {
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const base = [["/admin", "Dashboard", BarChart3], ["/admin/surveys", "Kelola Survey", Layers], ["/admin/responses", "Data Survey", FileText], ["/admin/qr", "QR Code Survey", QrCode], ["/admin/settings", "Pengaturan Survey", Settings]];
  const superItems = [["/admin/users", "Pengguna Admin", UsersIcon], ["/admin/branding", "Branding", Palette]];
  const items = user?.role === "super_admin" ? [...base, ...superItems] : base;
  return <><button className="mobile-menu icon-button" data-testid="mobile-menu-button" onClick={() => setOpen(!open)}><Menu/></button><aside className={`sidebar ${open ? "open" : ""}`}><BrandMark branding={branding} dark/><div className="side-label">RUANG KERJA ADMIN</div><nav>{items.map(([path, text, Icon]) => <Link key={path} data-testid={`nav-${text.toLowerCase().replaceAll(" ", "-")}`} className={loc.pathname === path ? "active" : ""} to={path} onClick={() => setOpen(false)}><Icon size={18}/>{text}</Link>)}</nav><div className="sidebar-bottom"><button type="button" className="user-chip" data-testid="open-change-password" onClick={() => setPwOpen(true)}><span className="status-dot"/><div><strong>{user?.name}</strong><em>{user?.role === "super_admin" ? "Super Admin" : "Admin"} · Ubah password</em></div></button><button className="logout-button" data-testid="logout-button" onClick={onLogout}><LogOut size={17}/> Keluar</button></div></aside><ChangePasswordModal open={pwOpen} onClose={() => setPwOpen(false)}/></>;
}

function AdminLayout({ children, user, branding, onLogout }) { return <div className="admin-app"><Sidebar user={user} branding={branding} onLogout={onLogout}/><main className="admin-main">{children}</main></div>; }
function AdminHeader({ title, subtitle, children }) { return <header className="admin-header"><div><p className="eyebrow">SURVEY KEPUASAN LAYANAN</p><h1 data-testid="admin-page-title">{title}</h1><p>{subtitle}</p></div><div className="header-actions">{children}</div></header>; }
function Kpi({ icon: Icon, label, value, suffix, tone }) { return <div className="kpi-card" data-testid={`kpi-${label.toLowerCase().replaceAll(" ", "-")}`}><div className={`kpi-icon ${tone}`}><Icon size={19}/></div><span>{label}</span><strong>{value}{suffix && <small>{suffix}</small>}</strong></div>; }

function useSurveyList() {
  const [surveys, setSurveys] = useState([]);
  const reload = useCallback(() => api.get("/admin/surveys").then(r => setSurveys(r.data)), []);
  useEffect(() => { reload(); }, [reload]);
  return { surveys, reload };
}

function Dashboard() {
  const [data, setData] = useState(null);
  const [period, setPeriod] = useState("all");
  const [surveyId, setSurveyId] = useState("");
  const [startDate, setStartDate] = useState(daysAgo(7));
  const [endDate, setEndDate] = useState(today());
  const [clearing, setClearing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [message, setMessage] = useState("");
  const { surveys } = useSurveyList();
  const load = useCallback(() => {
    let qs = `period=${period}`;
    if (surveyId) qs += `&survey_id=${surveyId}`;
    if (period === "custom") qs += `&start_date=${startDate}&end_date=${endDate}`;
    return api.get(`/admin/analytics?${qs}`).then(r => setData(r.data));
  }, [period, surveyId, startDate, endDate]);
  useEffect(() => { load(); }, [load]);
  const clearDemo = async () => {
    setClearing(true);
    try { const r = await api.delete("/admin/demo-data"); setMessage(`${r.data.deleted} data demo berhasil dihapus.`); setConfirm(false); load(); setTimeout(() => setMessage(""), 4000); }
    finally { setClearing(false); }
  };
  if (!data) return <div className="loading-state">Memuat dashboard...</div>;
  const ratingRows = [5,4,3,2,1];
  return <><AdminHeader title="Dashboard Survey" subtitle="Pantau suara pengguna dan kualitas pelayanan secara berkala.">
    {surveys.length > 1 && <select className="select-control" data-testid="dashboard-survey-filter" value={surveyId} onChange={e => setSurveyId(e.target.value)}><option value="">Semua Survey</option>{surveys.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</select>}
    <select className="select-control" data-testid="dashboard-period-filter" value={period} onChange={e => setPeriod(e.target.value)}><option value="all">Semua Data</option><option value="today">Hari Ini</option><option value="7d">7 Hari Terakhir</option><option value="30d">30 Hari Terakhir</option><option value="month">Bulan Ini</option><option value="custom">Rentang Tanggal</option></select>
    <button className="button secondary compact" data-testid="clear-demo-button" onClick={() => setConfirm(true)}><Trash2 size={15}/> Hapus Data Demo</button>
  </AdminHeader>
  {period === "custom" && <div className="date-range-row" data-testid="date-range-row"><label>Dari<input type="date" data-testid="start-date-input" value={startDate} max={endDate} onChange={e => setStartDate(e.target.value)}/></label><label>Sampai<input type="date" data-testid="end-date-input" value={endDate} min={startDate} max={today()} onChange={e => setEndDate(e.target.value)}/></label><span className="range-hint">{startDate} s/d {endDate}</span></div>}
  {message && <div className="toast-banner" data-testid="demo-cleared-message"><Check size={16}/> {message}</div>}
  <div className="kpi-grid"><Kpi icon={UsersIcon} label="Total Responden" value={data.total.toLocaleString("id-ID")} tone="blue"/><Kpi icon={Star} label="Rata-rata Kepuasan" value={data.average.toFixed(2)} suffix=" / 5" tone="yellow"/><Kpi icon={TrendingUp} label="Rating 5" value={data.five_percent} suffix="%" tone="green"/><Kpi icon={MessageSquare} label="Komentar" value={data.comments.toLocaleString("id-ID")} tone="orange"/></div>
  <div className="analytics-grid"><section className="panel chart-panel"><div className="panel-heading"><div><h2>Trend kepuasan</h2><p>Rata-rata rating per hari</p></div><span className="chart-legend"><i/> Rating</span></div><div className="chart-area">{data.trend.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={data.trend}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0"/><XAxis dataKey="date" tickLine={false} axisLine={false} tick={{fontSize: 11, fill: "#64748b"}}/><YAxis domain={[0,5]} ticks={[0,1,2,3,4,5]} tickLine={false} axisLine={false} tick={{fontSize: 11, fill: "#64748b"}}/><Tooltip/><Line type="monotone" dataKey="rating" stroke="#2563eb" strokeWidth={3} dot={{r: 3, fill: "#2563eb"}}/></LineChart></ResponsiveContainer> : <div className="empty-state"><TrendingUp size={28}/><h3>Belum ada data trend.</h3></div>}</div></section><section className="panel distribution-panel"><div className="panel-heading"><div><h2>Distribusi rating</h2><p>Komposisi tanggapan</p></div><Star size={18} fill="#f59e0b" color="#f59e0b"/></div><div className="distribution-list">{ratingRows.map(n => <div className="distribution-row" key={n}><span>{"★".repeat(n)}{"☆".repeat(5-n)}</span><div className="bar-track"><i style={{width: `${data.total ? data.counts[n] / data.total * 100 : 0}%`}}/></div><b>{data.counts[n]}</b></div>)}</div><div className="average-highlight"><span>Rata-rata kepuasan</span><strong>{data.average.toFixed(2)} <small>/ 5.00</small></strong></div></section></div>
  <section className="panel recent-panel"><div className="panel-heading"><div><h2>Response terbaru</h2><p>Tanggapan terakhir yang masuk</p></div><Link className="text-link" to="/admin/responses">Lihat semua <ChevronLeft className="rotate-180" size={15}/></Link></div>{data.recent.length ? <div className="recent-list">{data.recent.map(item => <div className="recent-item" key={item.id} data-testid="recent-response"><span className="small-rating">{"★".repeat(item.rating)}<em>{"★".repeat(5-item.rating)}</em></span><p>{item.comment || "Tidak ada komentar"}</p><time>{fmt(item.created_at)}</time></div>)}</div> : <div className="empty-state"><MessageSquare size={28}/><h3>Belum ada data survey.</h3><p>Data akan muncul setelah pengguna mengirimkan survey.</p></div>}</section>
  {confirm && <div className="modal-backdrop" onClick={() => setConfirm(false)}><div className="detail-modal" onClick={e => e.stopPropagation()} data-testid="confirm-clear-demo"><button type="button" className="icon-button close-modal" onClick={() => setConfirm(false)}><X size={18}/></button><p className="eyebrow">KONFIRMASI</p><h2>Hapus data demo?</h2><p className="detail-date">Tindakan ini menghapus semua tanggapan seed yang dibuat saat pengembangan. Data tanggapan asli tidak akan tersentuh.</p><div className="confirm-actions"><button className="button secondary" onClick={() => setConfirm(false)}>Batal</button><button className="button primary danger" data-testid="confirm-clear-button" disabled={clearing} onClick={clearDemo}>{clearing ? "Menghapus..." : "Ya, hapus"}</button></div></div></div>}
  </>;
}

function Responses() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [rating, setRating] = useState("");
  const [surveyId, setSurveyId] = useState("");
  const [detail, setDetail] = useState(null);
  const [exportOpen, setExportOpen] = useState(false);
  const { surveys } = useSurveyList();
  const load = useCallback(() => api.get(`/admin/responses?page=${page}&search=${encodeURIComponent(search)}${rating ? `&rating=${rating}` : ""}${surveyId ? `&survey_id=${surveyId}` : ""}`).then(r => setData(r.data)), [page, rating, search, surveyId]);
  useEffect(() => { load(); }, [load]);
  const download = async (format) => {
    const url = `/admin/export.${format}${surveyId ? `?survey_id=${surveyId}` : ""}`;
    const r = await api.get(url, { responseType: "blob" });
    const blob = URL.createObjectURL(r.data);
    const a = document.createElement("a"); a.href = blob; a.download = `survey-responses.${format}`; a.click(); URL.revokeObjectURL(blob);
    setExportOpen(false);
  };
  return <><AdminHeader title="Data Survey" subtitle="Baca setiap tanggapan untuk menemukan peluang perbaikan.">
    <div className="export-dropdown"><button className="button secondary" data-testid="export-toggle-button" onClick={() => setExportOpen(!exportOpen)}><Download size={16}/> Export Data</button>{exportOpen && <div className="export-menu" data-testid="export-menu"><button data-testid="export-csv-button" onClick={() => download("csv")}><FileText size={15}/> Export CSV</button><button data-testid="export-xlsx-button" onClick={() => download("xlsx")}><FileSpreadsheet size={15}/> Export Excel (XLSX)</button></div>}</div>
  </AdminHeader><section className="panel table-panel"><div className="table-toolbar"><div className="search-wrap"><span>⌕</span><input data-testid="response-search-input" placeholder="Cari komentar..." value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === "Enter" && (setPage(1), load())}/></div>{surveys.length > 1 && <select className="select-control" data-testid="response-survey-filter" value={surveyId} onChange={e => {setSurveyId(e.target.value);setPage(1)}}><option value="">Semua Survey</option>{surveys.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</select>}<select className="select-control" data-testid="response-rating-filter" value={rating} onChange={e => {setRating(e.target.value);setPage(1)}}><option value="">Semua rating</option>{[5,4,3,2,1].map(n => <option value={n} key={n}>{n} bintang</option>)}</select><button className="button secondary compact" data-testid="response-search-button" onClick={() => {setPage(1);load()}}>Terapkan</button></div><div className="table-scroll"><table><thead><tr><th>TANGGAL</th><th>RATING</th><th>KOMENTAR</th><th></th></tr></thead><tbody>{data?.items.map(item => <tr key={item.id} data-testid="response-row"><td><b>{fmt(item.created_at).split(" ").slice(0,3).join(" ")}</b><small>{fmt(item.created_at).split(" ").slice(3).join(" ")}</small></td><td><span className="table-rating">{item.rating} <Star size={14} fill="currentColor"/></span><small>{item.rating_label}</small></td><td className="comment-cell">{item.comment || <span className="muted">Tidak ada komentar</span>}</td><td><button className="icon-button" data-testid="view-response-button" aria-label="Lihat detail" onClick={() => setDetail(item)}><ChevronLeft className="rotate-180" size={17}/></button></td></tr>)}{data && !data.items.length && <tr><td colSpan="4"><div className="empty-state"><FileText size={28}/><h3>Belum ada tanggapan yang sesuai dengan filter.</h3></div></td></tr>}</tbody></table></div><div className="pagination"><span>{data ? `Menampilkan ${data.items.length} dari ${data.total} tanggapan` : "Memuat..."}</span><div><button className="icon-button" data-testid="previous-page-button" disabled={page <= 1} onClick={() => setPage(page-1)}><ChevronLeft size={17}/></button><b data-testid="current-page">{page}</b><button className="icon-button" data-testid="next-page-button" disabled={!data || page >= data.pages} onClick={() => setPage(page+1)}><ChevronLeft className="rotate-180" size={17}/></button></div></div></section>
  {detail && <div className="modal-backdrop" onClick={() => setDetail(null)}><div className="detail-modal" onClick={e => e.stopPropagation()} data-testid="response-detail-modal"><button type="button" className="icon-button close-modal" data-testid="close-detail-button" onClick={() => setDetail(null)}><X size={18}/></button><p className="eyebrow">DETAIL SURVEY</p><h2>{detail.rating_label}</h2><div className="detail-stars">{"★".repeat(detail.rating)}</div><p className="detail-date">{fmt(detail.created_at)}</p><div className="detail-comment">“{detail.comment || "Tidak ada komentar."}”</div></div></div>}
  </>;
}

const emptySurvey = { title: "", description: "", question: "Seberapa puas Anda dengan pelayanan kami?", comment_placeholder: "Tuliskan saran atau komentar Anda di sini...", max_comment_length: 500, status: "active", slug: "" };

function SurveyEditor({ open, initial, onClose, onSaved }) {
  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { setForm(initial); setError(""); }, [initial]);
  if (!open) return null;
  const update = e => setForm({...form, [e.target.name]: e.target.value});
  const save = async e => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const payload = {...form, max_comment_length: Number(form.max_comment_length)};
      const r = form.id ? await api.put(`/admin/surveys/${form.id}`, payload) : await api.post("/admin/surveys", payload);
      onSaved(r.data);
    } catch (err) { setError(err.response?.data?.detail || "Tidak dapat menyimpan survey."); }
    finally { setSaving(false); }
  };
  return <div className="modal-backdrop" onClick={onClose}><div className="editor-modal" onClick={e => e.stopPropagation()} data-testid="survey-editor"><button type="button" className="icon-button close-modal" onClick={onClose} data-testid="close-editor-button"><X size={18}/></button><p className="eyebrow">{form.id ? "UBAH SURVEY" : "SURVEY BARU"}</p><h2>{form.id ? "Perbarui konten survey" : "Tambahkan survey baru"}</h2><form onSubmit={save} className="editor-form"><label className="field-label">Judul<input name="title" value={form.title} onChange={update} data-testid="survey-title-input" required/></label><label className="field-label">Slug URL<input name="slug" value={form.slug} onChange={update} placeholder="pelayanan-administrasi" data-testid="survey-slug-input"/></label><label className="field-label full-field">Deskripsi<textarea name="description" value={form.description} onChange={update} data-testid="survey-description-input" required/></label><label className="field-label full-field">Pertanyaan utama<input name="question" value={form.question} onChange={update} data-testid="survey-question-input" required/></label><label className="field-label full-field">Placeholder komentar<input name="comment_placeholder" value={form.comment_placeholder} onChange={update} data-testid="survey-placeholder-input" required/></label><label className="field-label">Maksimal karakter<input type="number" name="max_comment_length" value={form.max_comment_length} onChange={update} data-testid="survey-max-length-input"/></label><label className="field-label">Status<select name="status" className="select-control" value={form.status} onChange={update} data-testid="survey-status-select"><option value="active">Aktif</option><option value="inactive">Nonaktif</option></select></label>{error && <div className="error-message">{error}</div>}<div className="settings-actions"><button type="button" className="button secondary" data-testid="cancel-editor-button" onClick={onClose}>Batal</button><button className="button primary" data-testid="save-survey-button" disabled={saving}>{saving ? "Menyimpan..." : "Simpan Survey"}</button></div></form></div></div>;
}

function SurveysPage() {
  const { surveys, reload } = useSurveyList();
  const [editing, setEditing] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [notice, setNotice] = useState("");
  const openCreate = () => setEditing({...emptySurvey});
  const openEdit = (survey) => setEditing({...survey});
  const onSaved = () => { setEditing(null); reload(); setNotice("Survey tersimpan."); setTimeout(() => setNotice(""), 3000); };
  const doDelete = async () => {
    try { await api.delete(`/admin/surveys/${confirmDelete.id}`); setConfirmDelete(null); reload(); setNotice("Survey dihapus."); setTimeout(() => setNotice(""), 3000); }
    catch (err) { alert(err.response?.data?.detail || "Gagal menghapus"); }
  };
  return <><AdminHeader title="Kelola Survey" subtitle="Buat survey terpisah untuk tiap layanan agar hasilnya mudah dibedakan."><button className="button primary" data-testid="create-survey-button" onClick={openCreate}><Plus size={16}/> Survey Baru</button></AdminHeader>
    {notice && <div className="toast-banner" data-testid="survey-notice"><Check size={16}/> {notice}</div>}
    <section className="survey-grid">{surveys.map(s => <article key={s.id} className="survey-card-admin" data-testid={`survey-card-${s.slug}`}><div className="survey-card-top"><span className={`status-pill ${s.status}`}>{s.status === "active" ? "Aktif" : "Nonaktif"}</span><div><button className="icon-button" data-testid={`edit-survey-${s.slug}`} onClick={() => openEdit(s)} aria-label="Ubah"><Pencil size={16}/></button><button className="icon-button" data-testid={`delete-survey-${s.slug}`} onClick={() => setConfirmDelete(s)} aria-label="Hapus"><Trash2 size={16}/></button></div></div><h2>{s.title}</h2><p className="survey-card-desc">{s.description}</p><div className="survey-card-meta"><div><span>Response</span><strong>{s.response_count.toLocaleString("id-ID")}</strong></div><div><span>Rata-rata</span><strong>{s.average_rating ? s.average_rating.toFixed(2) : "–"}</strong></div></div><Link className="text-link" to={`/survey/${s.slug}`} target="_blank">Buka halaman publik <ChevronLeft className="rotate-180" size={14}/></Link></article>)}{!surveys.length && <div className="empty-state"><Layers size={28}/><h3>Belum ada survey.</h3><p>Buat survey pertama untuk mulai mengumpulkan tanggapan.</p></div>}</section>
    <SurveyEditor open={!!editing} initial={editing || emptySurvey} onClose={() => setEditing(null)} onSaved={onSaved}/>
    {confirmDelete && <div className="modal-backdrop" onClick={() => setConfirmDelete(null)}><div className="detail-modal" onClick={e => e.stopPropagation()} data-testid="confirm-delete-survey"><button type="button" className="icon-button close-modal" onClick={() => setConfirmDelete(null)}><X size={18}/></button><p className="eyebrow">KONFIRMASI</p><h2>Hapus survey?</h2><p className="detail-date">Semua tanggapan untuk “{confirmDelete.title}” juga akan dihapus. Tindakan ini tidak bisa dibatalkan.</p><div className="confirm-actions"><button className="button secondary" onClick={() => setConfirmDelete(null)}>Batal</button><button className="button primary danger" data-testid="confirm-delete-button" onClick={doDelete}>Ya, hapus survey</button></div></div></div>}
  </>;
}

function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => { api.get("/admin/settings").then(r => setSettings(r.data)); }, []);
  if (!settings) return <div className="loading-state">Memuat pengaturan...</div>;
  const update = e => setSettings({...settings, [e.target.name]: e.target.value});
  const save = async e => {
    e.preventDefault();
    await api.put("/admin/settings", {...settings, max_comment_length: Number(settings.max_comment_length)});
    setSaved(true); setTimeout(() => setSaved(false), 2500);
  };
  return <><AdminHeader title="Pengaturan Survey Utama" subtitle="Sesuaikan konten survey default. Untuk survey tambahan, buka Kelola Survey."/><form className="settings-form panel" onSubmit={save} data-testid="settings-form"><div className="settings-intro"><div className="icon-box"><Settings size={22}/></div><div><h2>Konten survey</h2><p>Perubahan akan langsung terlihat oleh pengguna.</p></div><label className="switch-label"><input type="checkbox" data-testid="survey-status-toggle" checked={settings.status === "active"} onChange={e => setSettings({...settings, status: e.target.checked ? "active" : "inactive"})}/><span className="switch"/> {settings.status === "active" ? "Survey aktif" : "Survey nonaktif"}</label></div><div className="form-grid"><label className="field-label">Judul survey<input name="title" data-testid="settings-title-input" value={settings.title} onChange={update}/></label><label className="field-label">Pertanyaan utama<input name="question" data-testid="settings-question-input" value={settings.question} onChange={update}/></label><label className="field-label full-field">Deskripsi<textarea name="description" data-testid="settings-description-input" value={settings.description} onChange={update}/></label><label className="field-label full-field">Placeholder komentar<input name="comment_placeholder" data-testid="settings-placeholder-input" value={settings.comment_placeholder} onChange={update}/></label><label className="field-label">Maksimal karakter<input name="max_comment_length" data-testid="settings-max-length-input" type="number" value={settings.max_comment_length} onChange={update}/></label></div><div className="settings-actions"><span className="saved-message">{saved ? "✓ Pengaturan tersimpan" : ""}</span><button className="button primary" data-testid="save-settings-button">Simpan Perubahan</button></div></form></>;
}

function QRPage() {
  const { surveys } = useSurveyList();
  const [selected, setSelected] = useState(null);
  const active = useMemo(() => surveys.find(s => s.id === selected) || surveys[0], [surveys, selected]);
  useEffect(() => { if (surveys.length && !selected) setSelected(surveys[0].id); }, [surveys, selected]);
  if (!surveys.length) return <><AdminHeader title="QR Code Survey" subtitle="Belum ada survey yang aktif."/><div className="empty-state"><QrCode size={28}/><h3>Belum ada survey.</h3></div></>;
  if (!active) return <div className="loading-state">Memuat QR...</div>;
  const url = `${window.location.origin}/survey/${active.slug}`;
  const qrUrl = `${API}/admin/qr/${active.slug}.png`;
  const download = async () => {
    const r = await api.get(`/admin/qr/${active.slug}.png`, { responseType: "blob" });
    const blob = URL.createObjectURL(r.data);
    const a = document.createElement("a"); a.href = blob; a.download = `qr-${active.slug}.png`; a.click(); URL.revokeObjectURL(blob);
  };
  return <><AdminHeader title="QR Code Survey" subtitle="Bagikan akses survey di meja, loket, atau ruang tunggu.">
    {surveys.length > 1 && <select className="select-control" data-testid="qr-survey-selector" value={active.id} onChange={e => setSelected(e.target.value)}>{surveys.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</select>}
  </AdminHeader>
  <div className="qr-layout"><section className="panel qr-card"><div className="qr-frame"><img data-testid="survey-qr-image" src={qrUrl} alt={`QR Code ${active.title}`}/></div><h2>{active.title}</h2><p>Scan untuk membuka survey</p><button className="button primary" data-testid="download-qr-button" onClick={download}><Download size={16}/> Download QR (PNG)</button></section><section className="panel qr-info"><p className="eyebrow">URL SURVEY</p><h2>Siap dibagikan</h2><p>QR Code ini dibuat oleh server dan mengarah ke halaman survey publik. Tempelkan di area pelayanan agar pengguna dapat mengaksesnya dengan cepat.</p><div className="url-box" data-testid="survey-url">{url}<button className="icon-button" data-testid="copy-survey-url" onClick={() => navigator.clipboard?.writeText(url)}><FileText size={17}/></button></div><div className="qr-note"><QrCode size={22}/><span>QR Code dihasilkan lokal — bisa diunduh dan dicetak tanpa koneksi internet pihak ketiga.</span></div></section></div></>;
}

function UsersPage({ me }) {
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", name: "", password: "", role: "admin" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [confirmDel, setConfirmDel] = useState(null);
  const load = () => api.get("/admin/users").then(r => setUsers(r.data));
  useEffect(() => { load(); }, []);
  const submit = async e => {
    e.preventDefault(); setSaving(true); setError("");
    try { await api.post("/admin/users", form); setOpen(false); setForm({ email: "", name: "", password: "", role: "admin" }); load(); setNotice("Pengguna baru berhasil ditambahkan."); setTimeout(() => setNotice(""), 3000); }
    catch (err) { setError(err.response?.data?.detail || "Gagal membuat pengguna."); }
    finally { setSaving(false); }
  };
  const doDelete = async () => {
    try { await api.delete(`/admin/users/${confirmDel.id}`); setConfirmDel(null); load(); setNotice("Pengguna dihapus."); setTimeout(() => setNotice(""), 3000); }
    catch (err) { alert(err.response?.data?.detail || "Gagal menghapus"); setConfirmDel(null); }
  };
  return <><AdminHeader title="Pengguna Admin" subtitle="Tambahkan akun admin untuk tim yang memeriksa survey ini."><button className="button primary" data-testid="create-user-button" onClick={() => setOpen(true)}><UserPlus size={16}/> Tambah Admin</button></AdminHeader>
    {notice && <div className="toast-banner" data-testid="user-notice"><Check size={16}/> {notice}</div>}
    <section className="panel table-panel"><div className="table-scroll"><table><thead><tr><th>NAMA</th><th>EMAIL</th><th>ROLE</th><th>DIBUAT</th><th></th></tr></thead><tbody>{users.map(u => <tr key={u.id} data-testid={`user-row-${u.email}`}><td><b>{u.name}</b></td><td>{u.email}</td><td><span className={`status-pill ${u.role === "super_admin" ? "active" : "inactive"}`}>{u.role === "super_admin" ? "Super Admin" : "Admin"}</span></td><td><small>{fmt(u.created_at)}</small></td><td style={{textAlign:"right"}}>{u.email !== me.email && u.role !== "super_admin" && <button className="icon-button" data-testid={`delete-user-${u.email}`} onClick={() => setConfirmDel(u)} aria-label="Hapus"><Trash2 size={16}/></button>}</td></tr>)}</tbody></table></div></section>
    {open && <div className="modal-backdrop" onClick={() => setOpen(false)}><div className="editor-modal" onClick={e => e.stopPropagation()} data-testid="user-editor"><button type="button" className="icon-button close-modal" onClick={() => setOpen(false)}><X size={18}/></button><p className="eyebrow">PENGGUNA BARU</p><h2>Undang anggota tim</h2><form onSubmit={submit} className="editor-form"><label className="field-label full-field">Nama<input value={form.name} onChange={e => setForm({...form, name: e.target.value})} data-testid="new-user-name" required/></label><label className="field-label full-field">Email<input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} data-testid="new-user-email" required/></label><label className="field-label">Password awal<input type="text" minLength={8} value={form.password} onChange={e => setForm({...form, password: e.target.value})} data-testid="new-user-password" required/></label><label className="field-label">Role<select className="select-control" value={form.role} onChange={e => setForm({...form, role: e.target.value})} data-testid="new-user-role"><option value="admin">Admin (akses biasa)</option><option value="super_admin">Super Admin (akses penuh)</option></select></label>{error && <div className="error-message full-field">{error}</div>}<div className="settings-actions"><button type="button" className="button secondary" onClick={() => setOpen(false)}>Batal</button><button className="button primary" data-testid="save-user-button" disabled={saving}>{saving ? "Menyimpan..." : "Simpan"}</button></div></form></div></div>}
    {confirmDel && <div className="modal-backdrop" onClick={() => setConfirmDel(null)}><div className="detail-modal" onClick={e => e.stopPropagation()} data-testid="confirm-delete-user"><button type="button" className="icon-button close-modal" onClick={() => setConfirmDel(null)}><X size={18}/></button><p className="eyebrow">KONFIRMASI</p><h2>Hapus admin?</h2><p className="detail-date">{confirmDel.email} tidak akan bisa login lagi setelah dihapus.</p><div className="confirm-actions"><button className="button secondary" onClick={() => setConfirmDel(null)}>Batal</button><button className="button primary danger" data-testid="confirm-delete-user-button" onClick={doDelete}>Ya, hapus</button></div></div></div>}
  </>;
}

function BrandingPage({ onBrandingChange }) {
  const [form, setForm] = useState(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [digestMsg, setDigestMsg] = useState("");
  useEffect(() => { api.get("/admin/branding").then(r => setForm(r.data)); }, []);
  if (!form) return <div className="loading-state">Memuat branding...</div>;
  const upload = e => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 300_000) { setError("Ukuran logo maksimal 300KB."); return; }
    const reader = new FileReader();
    reader.onload = () => setForm({...form, logo_data_url: reader.result});
    reader.readAsDataURL(file);
  };
  const save = async e => {
    e.preventDefault(); setError("");
    try {
      const r = await api.put("/admin/branding", { institution_name: form.institution_name, accent_color: form.accent_color, logo_data_url: form.logo_data_url || null, digest_recipient: form.digest_recipient || null });
      setForm(r.data); setSaved(true); onBrandingChange?.(r.data); setTimeout(() => setSaved(false), 2500);
    } catch (err) { setError(err.response?.data?.detail || "Gagal menyimpan branding."); }
  };
  const sendDigestNow = async () => {
    setSending(true); setDigestMsg("");
    try { const r = await api.post("/admin/digest/send-now"); setDigestMsg(`Rekap dikirim ke ${r.data.sent} penerima${r.data.errors?.length ? ` (${r.data.errors.length} gagal)` : ""}.`); }
    catch (err) { setDigestMsg(err.response?.data?.detail || "Gagal mengirim rekap."); }
    finally { setSending(false); setTimeout(() => setDigestMsg(""), 6000); }
  };
  return <><AdminHeader title="Logo & Branding" subtitle="Sesuaikan tampilan survey agar terasa milik institusi Anda."/>
    <form className="settings-form panel" onSubmit={save} data-testid="branding-form">
      <div className="settings-intro"><div className="icon-box" style={{background: `${form.accent_color}22`, color: form.accent_color}}><Palette size={22}/></div><div><h2>Identitas visual</h2><p>Logo, warna aksen, dan email untuk rekap mingguan.</p></div></div>
      <div className="form-grid">
        <label className="field-label full-field">Nama institusi<input data-testid="branding-name-input" value={form.institution_name || ""} onChange={e => setForm({...form, institution_name: e.target.value})} required/></label>
        <label className="field-label">Warna aksen<div className="color-row"><input type="color" data-testid="branding-color-input" value={form.accent_color} onChange={e => setForm({...form, accent_color: e.target.value})}/><input type="text" value={form.accent_color} onChange={e => setForm({...form, accent_color: e.target.value})} maxLength={7}/></div></label>
        <label className="field-label">Logo (maks. 300KB)<input type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp" onChange={upload} data-testid="branding-logo-input"/></label>
        <div className="field-label full-field logo-preview-wrap">Pratinjau logo<div className="logo-preview">{form.logo_data_url ? <><img src={form.logo_data_url} alt="Logo"/><button type="button" className="button secondary compact" data-testid="remove-logo-button" onClick={() => setForm({...form, logo_data_url: null})}><Trash2 size={14}/> Hapus logo</button></> : <span className="muted"><ImageIcon size={18}/> Belum ada logo</span>}</div></div>
        <label className="field-label full-field">Email penerima rekap mingguan (opsional)<input type="email" value={form.digest_recipient || ""} onChange={e => setForm({...form, digest_recipient: e.target.value})} placeholder="laporan@institusi.go.id" data-testid="branding-digest-input"/><small className="muted-note">Jika kosong, rekap tetap dikirim ke semua akun admin yang punya email valid.</small></label>
      </div>
      {error && <div className="error-message">{error}</div>}
      <div className="settings-actions"><span className="saved-message">{saved ? "✓ Branding tersimpan" : ""}</span><button className="button primary" data-testid="save-branding-button">Simpan Branding</button></div>
    </form>
    <section className="panel digest-panel"><div className="settings-intro"><div className="icon-box" style={{background:"#dbeafe",color:"#2563eb"}}><Mail size={22}/></div><div><h2>Rekap mingguan otomatis</h2><p>Email ringkasan rating & komentar 7 hari terakhir dikirim setiap Senin 08:00 WIB.</p></div></div><div className="digest-info"><p>Kirim pratinjau sekarang untuk memastikan email terkirim ke kotak masuk tim.</p>{digestMsg && <div className="toast-banner inline" data-testid="digest-message"><Check size={16}/> {digestMsg}</div>}<button type="button" className="button secondary" data-testid="send-digest-now-button" disabled={sending} onClick={sendDigestNow}><Send size={15}/> {sending ? "Mengirim..." : "Kirim rekap sekarang"}</button></div></section>
  </>;
}

function AdminApp({ user, branding, onBrandingChange, onLogout }) {
  const isSuper = user.role === "super_admin";
  return <AdminLayout user={user} branding={branding} onLogout={onLogout}>
    <Routes>
      <Route index element={<Dashboard/>}/>
      <Route path="surveys" element={<SurveysPage/>}/>
      <Route path="responses" element={<Responses/>}/>
      <Route path="settings" element={<SettingsPage/>}/>
      <Route path="qr" element={<QRPage/>}/>
      <Route path="users" element={isSuper ? <UsersPage me={user}/> : <Navigate to="/admin"/>}/>
      <Route path="branding" element={isSuper ? <BrandingPage onBrandingChange={onBrandingChange}/> : <Navigate to="/admin"/>}/>
    </Routes>
  </AdminLayout>;
}

function App() {
  const [user, setUser] = useState(null);
  const [branding, setBranding] = useState(null);
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    api.get("/auth/me").then(r => setUser(r.data)).catch(() => {}).finally(() => setChecking(false));
    api.get("/branding").then(r => setBranding(r.data)).catch(() => {});
  }, []);
  useEffect(() => {
    if (branding?.accent_color) document.documentElement.style.setProperty("--brand", branding.accent_color);
  }, [branding]);
  const logout = async () => {
    try { await api.post("/auth/logout"); } catch (_) {}
    localStorage.removeItem("survey_access_token");
    setUser(null);
  };
  if (checking) return <div className="loading-state">Menyiapkan aplikasi...</div>;
  return <BrowserRouter><Routes>
    <Route path="/" element={<PublicSurvey/>}/>
    <Route path="/survey/:slug" element={<PublicSurvey/>}/>
    <Route path="/admin/login" element={user ? <Navigate to="/admin"/> : <AdminLogin onLogin={setUser}/>}/>
    <Route path="/admin/*" element={user ? <AdminApp user={user} branding={branding} onBrandingChange={setBranding} onLogout={logout}/> : <Navigate to="/admin/login"/>}/>
    <Route path="*" element={<Navigate to="/"/>}/>
  </Routes></BrowserRouter>;
}
export default App;
