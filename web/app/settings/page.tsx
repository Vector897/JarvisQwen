"use client";

import { useEffect, useState } from "react";
import { api, post, put, del } from "@/lib/api";
import { useToast } from "@/components/toast";
import { useLang } from "@/lib/i18n";

const PROVIDER_LABEL: Record<string, string> = {
  qwen: "Qwen Cloud (DashScope)",
  anthropic: "Anthropic (Claude)",
  openai: "OpenAI (GPT)",
  google: "Google (Gemini)",
  deepseek: "DeepSeek",
  openrouter: "OpenRouter",
  custom: "Custom OpenAI-compatible",
};

export default function Settings() {
  const [me, setMe] = useState<{ role: string } | null>(null);
  useEffect(() => { api("/api/auth/me").then(setMe).catch(() => {}); }, []);

  return (
    <div className="space-y-8">
      <KeysSection />
      <GeneralSection />
      <NotifySection />
      <ZoteroSection />
      {me?.role === "admin" && <UsersSection />}
      <PasswordSection />
    </div>
  );
}

// ---------- API key management (BYOK) ----------
function KeysSection() {
  const [keys, setKeys] = useState<any[]>([]);
  const [raw, setRaw] = useState("");
  const [provider, setProvider] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [msg, setMsg] = useState("");
  const [needProvider, setNeedProvider] = useState(false);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const { t } = useLang();

  const load = () => api("/api/keys").then(setKeys).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setMsg(""); setBusy(true);
    try {
      const r = await post("/api/keys", { raw_key: raw, provider, base_url: baseUrl });
      if (r.need_provider) {
        setNeedProvider(true);
        setMsg(r.message);
      } else {
        toast(`${r.masked}（${r.provider}）· ${r.message}`, "success");
        setMsg("");
        setRaw(""); setProvider(""); setBaseUrl(""); setNeedProvider(false);
        load();
      }
    } catch (err: any) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{t("settings.keysTitle")}</h2>
      <p className="text-sm text-slate-500">{t("settings.keysHint")}</p>
      <form onSubmit={add} className="card space-y-2">
        <textarea className="input font-mono" rows={2} value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder={t("settings.keysPlaceholder")} />
        {(needProvider || provider || baseUrl) && (
          <select className="input" value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="">{t("settings.selectProvider")}</option>
            {Object.entries(PROVIDER_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        )}
        <details>
          <summary className="cursor-pointer text-xs text-slate-400">{t("settings.keysAdvanced")}</summary>
          <input className="input mt-2" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://your-gateway.example.com/v1" />
        </details>
        <button className="btn-primary" disabled={busy}>{busy ? t("settings.keysVerifying") : t("settings.keysSave")}</button>
        {msg && <p className="text-sm text-slate-600">{msg}</p>}
      </form>
      <div className="space-y-2">
        {keys.map((k) => (
          <div key={k.id} className="card flex items-center justify-between text-sm">
            <div>
              <span className="badge bg-slate-100 mr-2">{PROVIDER_LABEL[k.provider] || k.provider}</span>
              <span className="font-mono">{k.masked}</span>
              {k.base_url && <span className="ml-2 text-xs text-slate-400">{k.base_url}</span>}
              <span className={`ml-2 badge ${k.status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                {k.status}
              </span>
            </div>
            <div className="flex gap-2">
              <button className="btn-ghost text-xs"
                onClick={() => post(`/api/keys/${k.id}/probe`, {}).then((r) => { toast(r.message, r.ok ? "success" : "error"); load(); })}>
                {t("settings.keysProbe")}
              </button>
              <button className="btn-ghost text-xs text-red-600"
                onClick={() => del(`/api/keys/${k.id}`).then(load)}>{t("common.delete")}</button>
            </div>
          </div>
        ))}
        {keys.length === 0 && (
          <p className="text-sm text-amber-600">{t("settings.keysEmpty")}</p>
        )}
      </div>
    </section>
  );
}

// ---------- Business settings ----------
function GeneralSection() {
  const [s, setS] = useState<any>(null);
  const toast = useToast();
  const { t } = useLang();

  useEffect(() => { api("/api/settings").then(setS).catch(() => {}); }, []);
  if (!s) return null;

  async function save() {
    try {
      await put("/api/settings", {
        values: {
          daily_budget_usd: Number(s.daily_budget_usd),
          redact_level: s.redact_level,
          cache_enabled: !!s.cache_enabled,
          model_light: s.model_light,
          model_frontier: s.model_frontier,
          research_profile: s.research_profile,
          relevance_threshold: Number(s.relevance_threshold),
          briefing_hour: Number(s.briefing_hour),
          cascade_enabled: !!s.cascade_enabled,
          cascade_confidence_threshold: Number(s.cascade_confidence_threshold),
        },
      });
      toast(t("settings.saved"), "success");
    } catch (err: any) { toast(err.message, "error"); }
  }

  const set = (k: string) => (e: any) =>
    setS({ ...s, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{t("settings.generalTitle")}</h2>
      <div className="card space-y-4 text-sm">
        <label className="block">
          <span className="mb-1 block font-medium">{t("settings.researchProfile")}</span>
          <textarea className="input" rows={2} value={s.research_profile} onChange={set("research_profile")}
            placeholder="e.g. LLM agent security / RL for portfolio optimization / protein design" />
        </label>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className="mb-1 block font-medium">{t("settings.dailyBudget")}</span>
            <input className="input" type="number" step="0.5" min="0"
              value={s.daily_budget_usd} onChange={set("daily_budget_usd")} />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">{t("settings.redactLevel")}</span>
            <select className="input" value={s.redact_level} onChange={set("redact_level")}>
              <option value="low">{t("settings.redactLow")}</option>
              <option value="medium">{t("settings.redactMed")}</option>
              <option value="high">{t("settings.redactHigh")}</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">{t("settings.modelLight")}</span>
            <input className="input font-mono" list="qwen-models" value={s.model_light} onChange={set("model_light")} />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">{t("settings.modelFrontier")}</span>
            <input className="input font-mono" list="qwen-models" value={s.model_frontier} onChange={set("model_frontier")} />
          </label>
          <datalist id="qwen-models">
            <option value="qwen/qwen3.6-flash">Qwen3.6 Flash — $0.25/$1.5 per MTok</option>
            <option value="qwen/qwen3.7-plus">Qwen3.7 Plus — $0.4/$1.6 per MTok</option>
            <option value="qwen/qwen3.7-max">Qwen3.7 Max — $2.5/$7.5 per MTok</option>
          </datalist>
          <label className="block">
            <span className="mb-1 block font-medium">{t("settings.relevanceThreshold")}</span>
            <input className="input" type="number" step="0.05" min="0" max="1"
              value={s.relevance_threshold} onChange={set("relevance_threshold")} />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">{t("settings.briefingHour")}</span>
            <input className="input" type="number" min="0" max="23"
              value={s.briefing_hour} onChange={set("briefing_hour")} />
          </label>
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!s.cache_enabled} onChange={set("cache_enabled")} />
          {t("settings.cacheEnabled")}
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!s.cascade_enabled} onChange={set("cascade_enabled")} />
          {t("settings.cascadeEnabled")}
        </label>
        {s.cascade_enabled && (
          <label className="block max-w-xs">
            <span className="mb-1 block font-medium">{t("settings.cascadeThreshold")}</span>
            <input className="input" type="number" step="0.05" min="0" max="1"
              value={s.cascade_confidence_threshold} onChange={set("cascade_confidence_threshold")} />
          </label>
        )}
        <button className="btn-primary" onClick={save}>{t("settings.save")}</button>
      </div>
    </section>
  );
}

// ---------- Push notifications ----------
function NotifySection() {
  const [s, setS] = useState<any>(null);
  const toast = useToast();
  const { t } = useLang();

  const load = () => api("/api/settings").then(setS).catch(() => {});
  useEffect(() => { load(); }, []);
  if (!s) return null;

  async function save() {
    try {
      const values: Record<string, any> = {
        notify_telegram_enabled: !!s.notify_telegram_enabled,
        telegram_chat_id: s.telegram_chat_id,
        notify_email_enabled: !!s.notify_email_enabled,
        smtp_host: s.smtp_host, smtp_port: Number(s.smtp_port || 587),
        smtp_user: s.smtp_user, smtp_from: s.smtp_from, smtp_to: s.smtp_to,
        notify_on_budget_cutoff: !!s.notify_on_budget_cutoff,
      };
      // Secret fields: if left blank, don't submit them (the backend also skips empty values as a fallback — belt and suspenders)
      if (s.telegram_bot_token) values.telegram_bot_token = s.telegram_bot_token;
      if (s.smtp_password) values.smtp_password = s.smtp_password;
      await put("/api/settings", { values });
      toast(t("settings.notifySaved"), "success");
      load();
    } catch (err: any) { toast(err.message, "error"); }
  }

  async function testNotify() {
    try {
      const r = await post("/api/settings/test-notify", {});
      toast(r.results.join("；"), "info");
    } catch (err: any) { toast(err.message, "error"); }
  }

  const set = (k: string) => (e: any) =>
    setS({ ...s, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{t("settings.notifyTitle")}</h2>
      <p className="text-sm text-slate-500">{t("settings.notifyHint")}</p>
      <div className="card space-y-4 text-sm">
        <label className="flex items-center gap-2 font-medium">
          <input type="checkbox" checked={!!s.notify_telegram_enabled} onChange={set("notify_telegram_enabled")} />
          {t("settings.telegramEnable")}
        </label>
        {s.notify_telegram_enabled && (
          <div className="grid gap-3 pl-6 md:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs text-slate-500">{t("settings.telegramToken")}</span>
              <input className="input font-mono" placeholder={s.telegram_bot_token_is_set ? t("settings.configuredKeepBlank") : ""}
                value={s.telegram_bot_token || ""} onChange={set("telegram_bot_token")} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-slate-500">{t("settings.telegramChatId")}</span>
              <input className="input font-mono" value={s.telegram_chat_id || ""} onChange={set("telegram_chat_id")} />
            </label>
          </div>
        )}
        <label className="flex items-center gap-2 font-medium">
          <input type="checkbox" checked={!!s.notify_email_enabled} onChange={set("notify_email_enabled")} />
          {t("settings.emailEnable")}
        </label>
        {s.notify_email_enabled && (
          <div className="grid gap-3 pl-6 md:grid-cols-2">
            <input className="input" placeholder={t("settings.smtpHost")} value={s.smtp_host || ""} onChange={set("smtp_host")} />
            <input className="input" type="number" placeholder={t("settings.smtpPort")} value={s.smtp_port || 587} onChange={set("smtp_port")} />
            <input className="input" placeholder={t("settings.smtpUser")} value={s.smtp_user || ""} onChange={set("smtp_user")} />
            <input className="input" type="password"
              placeholder={s.smtp_password_is_set ? t("settings.configuredKeepBlank") : t("settings.smtpPassword")}
              value={s.smtp_password || ""} onChange={set("smtp_password")} />
            <input className="input" placeholder={t("settings.smtpFrom")} value={s.smtp_from || ""} onChange={set("smtp_from")} />
            <input className="input" placeholder={t("settings.smtpTo")} value={s.smtp_to || ""} onChange={set("smtp_to")} />
          </div>
        )}
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!s.notify_on_budget_cutoff} onChange={set("notify_on_budget_cutoff")} />
          {t("settings.notifyOnCutoff")}
        </label>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={save}>{t("settings.save")}</button>
          <button className="btn-ghost" onClick={testNotify}>{t("settings.testNotify")}</button>
        </div>
      </div>
    </section>
  );
}

// ---------- Zotero sync ----------
function ZoteroSection() {
  const [s, setS] = useState<any>(null);
  const toast = useToast();
  const { t } = useLang();
  useEffect(() => { api("/api/settings").then(setS).catch(() => {}); }, []);
  if (!s) return null;

  async function save() {
    try {
      const values: Record<string, any> = {
        zotero_library_id: s.zotero_library_id, zotero_library_type: s.zotero_library_type,
      };
      if (s.zotero_api_key) values.zotero_api_key = s.zotero_api_key;
      await put("/api/settings", { values });
      toast(t("settings.zoteroSaved"), "success");
    } catch (err: any) { toast(err.message, "error"); }
  }

  const set = (k: string) => (e: any) => setS({ ...s, [k]: e.target.value });

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{t("settings.zoteroTitle")}</h2>
      <p className="text-sm text-slate-500">{t("settings.zoteroHint")}</p>
      <div className="card grid gap-3 text-sm md:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-xs text-slate-500">{t("settings.zoteroKey")}</span>
          <input className="input font-mono" placeholder={s.zotero_api_key_is_set ? t("settings.configuredKeepBlank") : ""}
            value={s.zotero_api_key || ""} onChange={set("zotero_api_key")} />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-slate-500">{t("settings.zoteroLibraryId")}</span>
          <input className="input font-mono" value={s.zotero_library_id || ""} onChange={set("zotero_library_id")} />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-slate-500">{t("settings.zoteroType")}</span>
          <select className="input" value={s.zotero_library_type || "user"} onChange={set("zotero_library_type")}>
            <option value="user">{t("settings.zoteroUser")}</option>
            <option value="group">{t("settings.zoteroGroup")}</option>
          </select>
        </label>
        <div className="flex items-end">
          <button className="btn-primary" onClick={save}>{t("settings.save")}</button>
        </div>
      </div>
    </section>
  );
}

// ---------- User management (admin) ----------
function UsersSection() {
  const [users, setUsers] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [role, setRole] = useState("member");
  const toast = useToast();
  const { t } = useLang();

  const load = () => api("/api/users").then(setUsers).catch(() => {});
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      const r = await post("/api/users", { name, role });
      toast(`${r.name} · temp password: ${r.temp_password}`, "success");
      setName("");
      load();
    } catch (err: any) { toast(err.message, "error"); }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{t("settings.usersTitle")}</h2>
      <form onSubmit={create} className="card flex flex-col gap-2 md:flex-row">
        <input className="input flex-1" placeholder={t("settings.usersNamePlaceholder")} value={name} onChange={(e) => setName(e.target.value)} />
        <select className="input md:w-40" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="member">{t("settings.roleMember")}</option>
          <option value="viewer">{t("settings.roleViewer")}</option>
          <option value="admin">{t("settings.roleAdmin")}</option>
        </select>
        <button className="btn-primary justify-center">{t("settings.usersCreate")}</button>
      </form>
      <div className="space-y-2">
        {users.map((u) => (
          <div key={u.id} className="card flex items-center justify-between text-sm">
            <span className="font-medium">{u.name}</span>
            <div className="flex items-center gap-2">
              <select className="input w-36" value={u.role}
                onChange={(e) => put(`/api/users/${u.id}/role`, { role: e.target.value })
                  .then(() => { toast(t("settings.roleUpdated"), "success"); load(); })
                  .catch((err) => toast(err.message, "error"))}>
                <option value="member">member</option>
                <option value="viewer">viewer</option>
                <option value="admin">admin</option>
              </select>
              <button className="btn-ghost text-xs text-red-600"
                onClick={() => del(`/api/users/${u.id}`).then(() => { toast(t("settings.userDeleted"), "info"); load(); })}>
                {t("settings.usersDelete")}
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------- Change password ----------
function PasswordSection() {
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const toast = useToast();
  const { t } = useLang();

  async function change(e: React.FormEvent) {
    e.preventDefault();
    try {
      await post("/api/auth/change-password", { old_password: oldPw, new_password: newPw });
      toast(t("settings.passwordChanged"), "success"); setOldPw(""); setNewPw("");
    } catch (err: any) { toast(err.message, "error"); }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{t("settings.accountTitle")}</h2>
      <form onSubmit={change} className="card flex flex-col gap-2 md:flex-row">
        <input className="input" type="password" placeholder={t("settings.oldPassword")} value={oldPw}
          onChange={(e) => setOldPw(e.target.value)} />
        <input className="input" type="password" placeholder={t("settings.newPassword")} value={newPw}
          onChange={(e) => setNewPw(e.target.value)} />
        <button className="btn-primary justify-center">{t("settings.changePassword")}</button>
      </form>
    </section>
  );
}
