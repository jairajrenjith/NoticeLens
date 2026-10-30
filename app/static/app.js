const LS = {
  get: (k, d) => { try { const v = localStorage.getItem("nl_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set: (k, v) => localStorage.setItem("nl_" + k, JSON.stringify(v)),
};
const LOCALE = { en: "en-IN", ml: "ml-IN", hi: "hi-IN", ta: "ta-IN" };
const CATS = ["exam", "fee", "placement", "event", "scholarship", "holiday", "hostel", "academic"];
const CAT_EMOJI = { exam: "📝", fee: "💰", placement: "💼", event: "🎉", holiday: "🏖️", scholarship: "🎓", hostel: "🏠", academic: "📚" };

function app() {
  return {
    langs: window.LANGS, cats: CATS, catEmoji: CAT_EMOJI,
    sems: ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"],
    branches: ["CSE", "ECE", "EEE", "ME", "CE", "IE", "AE", "ARCH"],
    lang: LS.get("lang", "en"),
    dark: LS.get("dark", window.matchMedia("(prefers-color-scheme: dark)").matches),
    profile: { email: "", ...LS.get("profile", { semester: "", branch: "" }) }, emailing: false,
    onboard: !LS.get("onboarded", false), step: 0,
    tab: "summarize", text: "", loading: false, loadStep: 0, result: null, error: "",
    board: LS.get("board", []), checked: LS.get("checked", {}),
    useAi: LS.get("useAi", true), health: { ai_enabled: false }, samples: [], showSamples: false,
    showPipeline: false, filter: "all", forMe: false, speaking: false, toastMsg: "", dragging: false,
    askQ: "", chat: [], asking: false, uploading: false, aiFailed: "",

    async init() {
      this.applyTheme();
      this.$watch("lang", (v) => { LS.set("lang", v); document.documentElement.lang = v; this.onLangChange(); });
      this.$watch("dark", (v) => { LS.set("dark", v); this.applyTheme(); });
      this.$watch("profile", (v) => LS.set("profile", v), { deep: true });
      this.$watch("useAi", (v) => { LS.set("useAi", v); if (!v) this.aiFailed = ""; });
      this.$watch("tab", (v) => v === "plan" && this.jumpToNextEvent());
      document.documentElement.lang = this.lang;
      fetch("/api/health").then((r) => r.json()).then((h) => { this.health = h; if (!this.profile.email && h.mail_default_to) this.profile.email = h.mail_default_to; }).catch(() => {});
      fetch("/api/samples").then((r) => r.json()).then((s) => (this.samples = s)).catch(() => {});
      window.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && this.tab === "summarize") this.summarize();
      });
    },

    t(k) { const d = window.I18N[this.lang] || window.I18N.en; return d[k] ?? window.I18N.en[k] ?? k; },
    tf(k, vars) { return Object.entries(vars).reduce((s, [a, b]) => s.replace(`{${a}}`, b), this.t(k)); },
    applyTheme() { document.documentElement.classList.toggle("dark", this.dark); },
    toast(m) { this.toastMsg = m; clearTimeout(this._tt); this._tt = setTimeout(() => (this.toastMsg = ""), 2200); },
    get wordCount() { return this.text.trim() ? this.text.trim().split(/\s+/).length : 0; },
    get aiActive() { return this.useAi && this.health.ai_enabled; },

    // ---------- Summarize ----------
    async summarize(textOverride) {
      const text = (textOverride ?? this.text).trim();
      if (!text || this.loading) return;
      this.text = text; this.loading = true; this.error = ""; this.loadStep = 1; this.tab = "summarize";
      const timers = [setTimeout(() => (this.loadStep = 2), 450), setTimeout(() => (this.loadStep = 3), 900)];
      try {
        const res = await fetch("/api/summarize", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, lang: this.lang, profile: this.profile, use_ai: this.useAi }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || this.t("error"));
        this.result = data; this.saveToBoard(text, data);
        this.aiFailed = this.useAi && this.health.ai_enabled ? (data.tiers.ai_error || "") : "";
        if (this.aiFailed) this.toast("⚠ AI tier failed — showing Rules + ML summary");
        this.$nextTick(() => document.getElementById("result")?.scrollIntoView({ behavior: "smooth", block: "start" }));
      } catch (e) { this.error = e.message || this.t("error"); }
      finally { timers.forEach(clearTimeout); this.loading = false; this.loadStep = 0; }
    },
    async onLangChange() {
      if (!this.result || this.result.lang === this.lang || !this.aiActive) return;
      const item = this.board.find((b) => b.id === this.result.id);
      if (item?.views?.[this.lang]) { this.result = item.views[this.lang]; return; }
      this.toast(this.t("translating"));
      await this.summarize(item?.text || this.text);
    },
    saveToBoard(text, data) {
      let item = this.board.find((b) => b.id === data.id);
      if (!item) { item = { id: data.id, text, created: Date.now(), views: {} }; this.board.unshift(item); }
      item.views[data.lang] = data;
      // A revised notice supersedes the earlier one: its old deadlines leave the planner & calendar.
      const old = data.summary.update && this.board.find((b) => b.id === data.summary.update.of.id);
      if (old) old.supersededBy = { id: data.id, title: data.summary.title };
      this.board = this.board.slice(0, 40); LS.set("board", this.board);
    },
    loadSample(s) { this.showSamples = false; this.text = s.text; this.summarize(); },
    clearAll() { this.text = ""; this.result = null; this.error = ""; this.stopSpeak(); },

    async upload(file) {
      if (!file) return;
      this.uploading = true; this.error = "";
      const fd = new FormData(); fd.append("file", file);
      try {
        const res = await fetch("/api/extract", { method: "POST", body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        this.text = data.text; this.toast("✓ " + file.name);
      } catch (e) { this.error = e.message; }
      finally { this.uploading = false; }
    },
    onDrop(e) { this.dragging = false; const f = e.dataTransfer.files?.[0]; if (f) this.upload(f); },

    // ---------- Helpers for the card ----------
    get s() { return this.result?.summary; },
    daysLeft(iso) {
      const d = new Date(iso + "T00:00:00"); const n = new Date(); n.setHours(0, 0, 0, 0);
      return Math.round((d - n) / 86400000);
    },
    fmtDate(iso) {
      try { return new Intl.DateTimeFormat(LOCALE[this.lang], { weekday: "short", day: "numeric", month: "short" }).format(new Date(iso + "T00:00:00")); }
      catch { return iso; }
    },
    countdown(iso) {
      const n = this.daysLeft(iso);
      if (n < 0) return this.t("overdue"); if (n === 0) return this.t("today"); if (n === 1) return this.t("tomorrow");
      return this.tf("days_left", { n });
    },
    nextDeadline(sum) {
      sum = sum || this.s; if (!sum) return null;
      const valid = (sum.dates || []).filter((d) => d.date && this.daysLeft(d.date) >= 0);
      const pick = valid.filter((d) => d.is_deadline).sort((a, b) => a.date.localeCompare(b.date))[0]
        || valid.sort((a, b) => a.date.localeCompare(b.date))[0];
      return pick || null;
    },
    urgencyClasses(u) {
      return { high: "from-rose-500 to-orange-500", medium: "from-amber-400 to-yellow-500", low: "from-emerald-500 to-teal-500" }[u] || "from-slate-400 to-slate-500";
    },
    urgencyChip(u) {
      return { high: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300", medium: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300", low: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" }[u];
    },
    relChip(v) {
      return { yes: "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300", no: "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300", maybe: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300" }[v] || "";
    },
    toggleCheck(key) { this.checked[key] = !this.checked[key]; LS.set("checked", this.checked); },
    plainSummary() {
      const s = this.s; if (!s) return "";
      const lines = [`${s.emoji} *${s.title}*`, "", s.tldr, ""];
      (s.key_points || []).forEach((p) => lines.push("• " + p));
      if (s.actions?.length) { lines.push("", "✅ " + this.t("actions") + ":"); s.actions.forEach((a) => lines.push("☐ " + a.task + (a.deadline ? ` (${this.fmtDate(a.deadline)})` : ""))); }
      const nd = this.nextDeadline(); if (nd) lines.push("", `⏳ ${this.t("next_deadline")}: ${this.fmtDate(nd.date)}`);
      lines.push("", "— via NoticeLens");
      return lines.join("\n");
    },
    share() { window.open("https://wa.me/?text=" + encodeURIComponent(this.plainSummary()), "_blank"); },
    async copy() { await navigator.clipboard.writeText(this.plainSummary()); this.toast(this.t("copied")); },
    addCalendar(only) {
      const s = this.s; const dates = only ? [only] : (s.dates || []).filter((d) => d.date);
      if (!dates.length) return;
      const esc = (x) => String(x || "").replace(/[,;\\]/g, (m) => "\\" + m).replace(/\n/g, "\\n");
      const ev = dates.map((d, i) => {
        const day = d.date.replaceAll("-", ""); const next = new Date(d.date + "T00:00:00"); next.setDate(next.getDate() + 1);
        const end = next.toISOString().slice(0, 10).replaceAll("-", "");
        return ["BEGIN:VEVENT", `UID:${this.result.id}-${i}@noticelens`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").split(".")[0]}Z`,
          `DTSTART;VALUE=DATE:${day}`, `DTEND;VALUE=DATE:${end}`, `SUMMARY:${esc((d.is_deadline ? "⏰ " : "") + s.title + " – " + (d.label || ""))}`,
          `DESCRIPTION:${esc(s.tldr + (d.time ? " @ " + d.time : ""))}`,
          "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", `DESCRIPTION:${esc(s.title)}`, "END:VALARM", "END:VEVENT"].join("\r\n");
      });
      const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NoticeLens//EN", ...ev, "END:VCALENDAR"].join("\r\n");
      const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
      a.download = (s.title || "notice").replace(/[^\w\u0080-￿]+/g, "_").slice(0, 40) + ".ics"; a.click();
    },
    async speak() {
      if (this.speaking) return this.stopSpeak();
      const s = this.s; if (!s) return;
      const text = [s.title, s.tldr, ...(s.key_points || []), ...(s.actions || []).map((a) => a.task)].join(". ");
      const lang = this.result.lang || this.lang;
      this.speaking = true;
      try {  // 1) server voice (works for ml/hi/ta even when the browser has no voice)
        const res = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, lang }) });
        if (!res.ok) throw new Error();
        this._audio = new Audio(URL.createObjectURL(await res.blob()));
        this._audio.onended = this._audio.onerror = () => (this.speaking = false);
        if (!this.speaking) return;  // stopped while loading
        await this._audio.play(); return;
      } catch { this.speaking = false; }
      // 2) fallback: browser speech synthesis
      if (!window.speechSynthesis) return this.toast("🔇 Speech not available");
      const u = new SpeechSynthesisUtterance(text);
      const code = this.langs.find((l) => l.code === (this.result.lang || this.lang)).speech;
      u.lang = code; const v = speechSynthesis.getVoices().find((x) => x.lang.replace("_", "-").startsWith(code.slice(0, 2)));
      if (v) u.voice = v; u.rate = 0.95;
      u.onend = u.onerror = () => (this.speaking = false);
      speechSynthesis.cancel(); speechSynthesis.speak(u); this.speaking = true;
    },
    stopSpeak() { window.speechSynthesis?.cancel(); this._audio?.pause(); this._audio = null; this.speaking = false; },

    // ---------- Board ----------
    viewOf(item) { return item.views[this.lang] || Object.values(item.views)[0]; },
    get boardItems() {
      return this.board.map((b) => ({ ...b, v: this.viewOf(b) })).filter((b) => b.v)
        .filter((b) => this.filter === "all" || b.v.summary.category === this.filter)
        .filter((b) => !this.forMe || b.v.summary.relevance?.verdict !== "no")
        .sort((a, b) => {
          const r = { high: 0, medium: 1, low: 2 }; const ua = r[a.v.summary.urgency] ?? 3, ub = r[b.v.summary.urgency] ?? 3;
          const da = this.nextDeadline(a.v.summary)?.date || "9999", db = this.nextDeadline(b.v.summary)?.date || "9999";
          return (!!a.supersededBy - !!b.supersededBy) || da.localeCompare(db) || ua - ub;
        });
    },
    openItem(b) { this.result = b.v; this.text = b.text; this.tab = "summarize"; window.scrollTo({ top: 0, behavior: "smooth" }); },
    deleteItem(b) { this.board = this.board.filter((x) => x.id !== b.id); LS.set("board", this.board); },

    // ---------- Ask ----------
    async ask(q) {
      q = (q ?? this.askQ).trim(); if (!q || this.asking) return;
      this.chat.push({ role: "user", text: q }); this.askQ = ""; this.asking = true;
      try {
        const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q, lang: this.lang, profile: this.profile, use_ai: this.useAi }) });
        const d = await res.json();
        this.chat.push({ role: "bot", text: d.answer || this.t("no_answer"), sources: d.sources || [], source: d.source });
      } catch { this.chat.push({ role: "bot", text: this.t("error"), sources: [] }); }
      finally { this.asking = false; this.$nextTick(() => document.getElementById("chatEnd")?.scrollIntoView({ behavior: "smooth" })); }
    },

    // ---------- Planner: tasks across all notices ----------
    calMonth: (() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); })(),
    calSel: null, showAllTasks: false, tip: { show: false, x: 0, y: 0, title: "", lines: [] }, loadingSamples: false,

    get allTasks() {
      const W = { high: 3, medium: 2, low: 1 }, R = { yes: 8, maybe: 0, no: -25 };
      const out = [];
      for (const b of this.board) {
        const v = this.viewOf(b); if (!v || b.supersededBy) continue;
        const s = v.summary, nd = this.nextDeadline(s)?.date || null;
        const acts = s.actions?.length ? s.actions
          : (s.dates || []).filter((d) => d.is_deadline).map((d) => ({ task: d.label, deadline: d.date }));
        acts.forEach((a, i) => {
          const key = v.id + "-" + i, date = a.deadline || nd, days = date ? this.daysLeft(date) : null;
          const score = (W[s.urgency] || 1) * 10 + (date ? (days < 0 ? -40 : Math.max(0, 21 - days) * 3) : 0) + (R[s.relevance?.verdict] ?? 0);
          out.push({ key, task: a.task, date, days, score, done: !!this.checked[key], item: b, title: s.title, emoji: s.emoji,
            category: s.category, urgency: s.urgency, rel: s.relevance?.verdict });
        });
      }
      return out.sort((a, b) => b.score - a.score);
    },
    get openTasks() { return this.allTasks.filter((t) => !t.done && (t.days === null || t.days >= 0)); },
    get visibleTasks() { return this.showAllTasks ? this.allTasks : this.openTasks.slice(0, 5); },
    get kpis() {
      const open = this.openTasks;
      return [
        { k: "kpi_open", v: open.length, icon: "📋" },
        { k: "kpi_week", v: open.filter((t) => t.days !== null && t.days <= 7).length, icon: "⏳" },
        { k: "kpi_overdue", v: this.allTasks.filter((t) => !t.done && t.days !== null && t.days < 0).length, icon: "⚠️" },
        { k: "kpi_forme", v: this.board.filter((b) => this.viewOf(b)?.summary.relevance?.verdict === "yes").length, icon: "👤" },
      ];
    },
    taskWhen(t) { return t.date ? this.countdown(t.date) + " · " + this.fmtDate(t.date) : this.t("no_date"); },

    // Workload column chart (single series, next 14 days)
    get workload() {
      const days = [], base = new Date(); base.setHours(0, 0, 0, 0);
      for (let i = 0; i < 14; i++) {
        const d = new Date(base); d.setDate(base.getDate() + i);
        const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
        const tasks = this.allTasks.filter((t) => t.date === iso && !t.done);
        days.push({ iso, i, d, tasks, n: tasks.length });
      }
      const max = Math.max(1, ...days.map((d) => d.n));
      const W = 640, H = 190, L = 30, Rr = 8, T = 18, B = 34, pw = W - L - Rr, ph = H - T - B, band = pw / 14, bw = Math.min(26, band * 0.62);
      const y = (v) => T + ph - (v / max) * ph;
      const ticks = [...new Set([0, Math.ceil(max / 2), max])];
      const peak = days.reduce((a, b) => (b.n > a.n ? b : a), days[0]);
      return { W, H, L, T, B, ph, band, bw, max, ticks, y, peak, base: T + ph,
        bars: days.map((d) => ({ ...d, x: L + d.i * band + (band - bw) / 2, hx: L + d.i * band, h: (d.n / max) * ph,
          label: d.i === 0 ? this.t("today_lbl") : d.i % 2 === 0 ? String(d.d.getDate()) : "" })) };
    },
    barPath(x, base, w, h) {
      if (h <= 0) return ""; const r = Math.min(4, h, w / 2), y = base - h;
      return `M${x},${base} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${base} Z`;
    },

    // Per-notice task timeline
    get timeline() {
      const s = this.s; if (!s) return null;
      const rows = (s.dates || []).filter((d) => d.date).slice().sort((a, b) => a.date.localeCompare(b.date));
      if (!rows.length) return null;
      const toT = (iso) => new Date(iso + "T00:00:00").getTime(), today = new Date(); today.setHours(0, 0, 0, 0);
      const t0 = Math.min(today.getTime(), toT(rows[0].date)) - 86400000, t1 = Math.max(today.getTime(), toT(rows[rows.length - 1].date)) + 2 * 86400000;
      const W = 640, L = 190, Rr = 70, T = 26, rowH = 34, H = T + rows.length * rowH + 8;
      const x = (t) => L + ((t - t0) / (t1 - t0)) * (W - L - Rr);
      const tx = x(today.getTime());
      return { W, H, T, L, tx, rows: rows.map((d, i) => {
        const dx = x(toT(d.date)), past = this.daysLeft(d.date) < 0;
        return { ...d, i, cy: T + i * rowH + rowH / 2, dx, past, short: (d.label || "").length > 30 ? d.label.slice(0, 29) + "…" : d.label || "" };
      }) };
    },
    // SVG markup is built as strings: Alpine's x-for can't clone <template> inside <svg>.
    get workloadSvg() {
      const w = this.workload, esc = this.esc;
      let g = w.ticks.map((tv) => `<line x1="${w.L}" x2="${w.W - 8}" y1="${w.y(tv)}" y2="${w.y(tv)}" stroke="var(${tv === 0 ? "--axis" : "--grid"})" stroke-width="1"/>`
        + `<text x="${w.L - 8}" y="${w.y(tv) + 4}" text-anchor="end" font-size="11" fill="var(--text-muted)">${tv}</text>`).join("");
      for (const b of w.bars) {
        const cx = b.x + w.bw / 2;
        g += `<g data-i="${b.i}"><rect x="${b.hx}" y="${w.T}" width="${w.band}" height="${w.ph}" fill="transparent"/>`
          + (b.h > 0 ? `<path d="${this.barPath(b.x, w.base, w.bw, b.h)}" fill="var(--series-1)"/>` : "")
          + (b.n && b.iso === w.peak.iso ? `<text x="${cx}" y="${w.base - b.h - 6}" text-anchor="middle" font-size="11" font-weight="600" fill="currentColor">${b.n}</text>` : "")
          + `<text x="${cx}" y="${w.base + 18}" text-anchor="middle" font-size="11" font-weight="${b.i === 0 ? 700 : 400}" fill="var(--text-muted)">${esc(b.label)}</text></g>`;
      }
      return g;
    },
    workloadHover(e) {
      const el = e.target.closest("[data-i]"); if (!el) return this.hideTip();
      const b = this.workload.bars[+el.dataset.i];
      this.showTip(e, this.fmtDate(b.iso) + " · " + this.tf("tasks_n", { n: b.n }), b.tasks.map((x) => "• " + (x.task.length > 60 ? x.task.slice(0, 59) + "…" : x.task)));
    },
    get timelineSvg() {
      const tl = this.timeline; if (!tl) return ""; const esc = this.esc;
      let g = tl.rows.map((r) => `<line x1="${tl.L}" x2="${tl.W - 70}" y1="${r.cy}" y2="${r.cy}" stroke="var(--grid)" stroke-width="1"/>`).join("");
      g += `<line x1="${tl.tx}" x2="${tl.tx}" y1="${tl.T - 8}" y2="${tl.H - 4}" stroke="var(--text-muted)" stroke-width="1.5" stroke-dasharray="3 3"/>`
        + `<text x="${tl.tx}" y="${tl.T - 12}" text-anchor="middle" font-size="11" font-weight="600" fill="var(--text-muted)">${esc(this.t("today_lbl"))}</text>`;
      for (const r of tl.rows) {
        const col = r.past ? "var(--text-muted)" : "var(--series-1)";
        g += `<g data-i="${r.i}"><rect x="0" y="${r.cy - 17}" width="${tl.W}" height="34" fill="transparent"/>`
          + `<text x="0" y="${r.cy + 4}" font-size="12" fill="currentColor">${esc(r.short)}</text>`
          + (r.past ? "" : `<line x1="${Math.min(tl.tx, r.dx)}" x2="${Math.max(tl.tx, r.dx)}" y1="${r.cy}" y2="${r.cy}" stroke="var(--series-1)" stroke-width="2" stroke-linecap="round" opacity=".55"/>`)
          + (r.is_deadline ? `<path d="${this.diamond(r.dx, r.cy, 7)}" fill="${col}" stroke="var(--surface)" stroke-width="2"/>`
            : `<circle cx="${r.dx}" cy="${r.cy}" r="5" fill="var(--surface)" stroke="${col}" stroke-width="2"/>`)
          + `<text x="${r.dx + 12}" y="${r.cy + 4}" font-size="11" fill="var(--text-muted)">${esc(this.fmtDate(r.date).replace(/^[^ ]+ /, ""))}</text></g>`;
      }
      return g;
    },
    timelineHover(e) {
      const el = e.target.closest("[data-i]"); if (!el) return this.hideTip();
      const r = this.timeline.rows[+el.dataset.i];
      this.showTip(e, r.label, [this.fmtDate(r.date) + (r.time ? " · " + r.time : ""), this.countdown(r.date)]);
    },
    esc(s) { return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]); },
    diamond(cx, cy, r = 6) { return `M${cx},${cy - r} L${cx + r},${cy} L${cx},${cy + r} L${cx - r},${cy} Z`; },

    // Calendar
    get calTitle() { return new Intl.DateTimeFormat(LOCALE[this.lang], { month: "long", year: "numeric" }).format(this.calMonth); },
    get weekdays() {
      const f = new Intl.DateTimeFormat(LOCALE[this.lang], { weekday: "short" });
      return [...Array(7)].map((_, i) => f.format(new Date(2026, 10, 2 + i))); // Mon..Sun
    },
    get calEvents() {
      const ev = {};
      for (const b of this.board) {
        const v = this.viewOf(b); if (!v || b.supersededBy) continue;
        for (const d of v.summary.dates || []) {
          if (!d.date) continue;
          (ev[d.date] ||= []).push({ ...d, title: v.summary.title, emoji: v.summary.emoji, item: b });
        }
      }
      return ev;
    },
    get calCells() {
      const m = this.calMonth, first = (m.getDay() + 6) % 7, start = new Date(m); start.setDate(1 - first);
      const ev = this.calEvents, todayIso = this.isoOf(new Date());
      return [...Array(42)].map((_, i) => {
        const d = new Date(start); d.setDate(start.getDate() + i); const iso = this.isoOf(d);
        return { iso, day: d.getDate(), inMonth: d.getMonth() === m.getMonth(), today: iso === todayIso, events: ev[iso] || [] };
      });
    },
    isoOf(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; },
    jumpToNextEvent() {
      // Open the calendar on the month of the next upcoming deadline/event.
      const today = this.isoOf(new Date());
      const next = Object.keys(this.calEvents).filter((d) => d >= today).sort()[0];
      if (next) { const [y, m] = next.split("-").map(Number); this.calMonth = new Date(y, m - 1, 1); this.calSel = next; }
    },
    shiftMonth(n) { this.calMonth = new Date(this.calMonth.getFullYear(), this.calMonth.getMonth() + n, 1); },

    showTip(e, title, lines) { this.tip = { show: true, x: e.clientX, y: e.clientY, title, lines }; },
    hideTip() { this.tip.show = false; },

    async loadAllSamples() {
      this.loadingSamples = true;
      for (const s of this.samples.filter((x) => x.id !== "fee_revised")) {
        try {
          const res = await fetch("/api/summarize", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: s.text, lang: this.lang, profile: this.profile, use_ai: this.useAi }) });
          if (res.ok) this.saveToBoard(s.text, await res.json());
        } catch {}
      }
      this.loadingSamples = false;
    },

    // ---------- Email (Gmail SMTP) ----------
    async sendMail(url, payload) {
      if (this.emailing) return;
      let to = this.profile.email;
      if (!to) { to = prompt(this.t("your_email")); if (!to) return; this.profile.email = to.trim(); }
      this.emailing = true;
      try {
        const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ to, ...payload }) });
        const d = await res.json();
        if (!res.ok) throw new Error(d.detail);
        this.toast("📧 " + this.t("email_sent") + " " + d.to);
      } catch (e) { this.toast("⚠️ " + (e.message || this.t("error"))); }
      finally { this.emailing = false; }
    },
    emailSummary() { this.sendMail("/api/email/summary", { summary: this.s }); },
    emailDigest() {
      const tasks = this.openTasks.slice(0, 10).map(({ task, date, urgency, title, emoji, category }) => ({ task, date, urgency, title, emoji, category }));
      const kpis = Object.fromEntries(this.kpis.map((k) => [this.t(k.k), k.v]));
      this.sendMail("/api/email/digest", { tasks, kpis });
    },

    // ---------- Onboarding ----------
    finishOnboard(trySample) {
      this.onboard = false; this.step = 0; LS.set("onboarded", true);
      if (trySample && this.samples[0]) this.loadSample(this.samples[0]);
    },
  };
}
