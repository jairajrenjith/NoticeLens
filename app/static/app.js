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
    profile: LS.get("profile", { semester: "", branch: "" }),
    onboard: !LS.get("onboarded", false), step: 0,
    tab: "summarize", text: "", loading: false, loadStep: 0, result: null, error: "",
    board: LS.get("board", []), checked: LS.get("checked", {}),
    useAi: LS.get("useAi", true), health: { ai_enabled: false }, samples: [], showSamples: false,
    showPipeline: false, filter: "all", forMe: false, speaking: false, toastMsg: "", dragging: false,
    askQ: "", chat: [], asking: false, uploading: false,

    async init() {
      this.applyTheme();
      this.$watch("lang", (v) => { LS.set("lang", v); document.documentElement.lang = v; this.onLangChange(); });
      this.$watch("dark", (v) => { LS.set("dark", v); this.applyTheme(); });
      this.$watch("profile", (v) => LS.set("profile", v), { deep: true });
      this.$watch("useAi", (v) => LS.set("useAi", v));
      document.documentElement.lang = this.lang;
      fetch("/api/health").then((r) => r.json()).then((h) => (this.health = h)).catch(() => {});
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
    speak() {
      if (this.speaking) return this.stopSpeak();
      const s = this.s; if (!s || !window.speechSynthesis) return;
      const text = [s.title, s.tldr, ...(s.key_points || []), ...(s.actions || []).map((a) => a.task)].join(". ");
      const u = new SpeechSynthesisUtterance(text);
      const code = this.langs.find((l) => l.code === (this.result.lang || this.lang)).speech;
      u.lang = code; const v = speechSynthesis.getVoices().find((x) => x.lang.replace("_", "-").startsWith(code.slice(0, 2)));
      if (v) u.voice = v; u.rate = 0.95;
      u.onend = u.onerror = () => (this.speaking = false);
      speechSynthesis.cancel(); speechSynthesis.speak(u); this.speaking = true;
    },
    stopSpeak() { window.speechSynthesis?.cancel(); this.speaking = false; },

    // ---------- Board ----------
    viewOf(item) { return item.views[this.lang] || Object.values(item.views)[0]; },
    get boardItems() {
      return this.board.map((b) => ({ ...b, v: this.viewOf(b) })).filter((b) => b.v)
        .filter((b) => this.filter === "all" || b.v.summary.category === this.filter)
        .filter((b) => !this.forMe || b.v.summary.relevance?.verdict !== "no")
        .sort((a, b) => {
          const r = { high: 0, medium: 1, low: 2 }; const ua = r[a.v.summary.urgency] ?? 3, ub = r[b.v.summary.urgency] ?? 3;
          const da = this.nextDeadline(a.v.summary)?.date || "9999", db = this.nextDeadline(b.v.summary)?.date || "9999";
          return da.localeCompare(db) || ua - ub;
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

    // ---------- Onboarding ----------
    finishOnboard(trySample) {
      this.onboard = false; this.step = 0; LS.set("onboarded", true);
      if (trySample && this.samples[0]) this.loadSample(this.samples[0]);
    },
  };
}
