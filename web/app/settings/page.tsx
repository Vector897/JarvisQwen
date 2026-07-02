"use client";

import { useEffect, useState } from "react";
import { api, post, put, del } from "@/lib/api";

const PROVIDER_LABEL: Record<string, string> = {
  anthropic: "Anthropic (Claude)",
  openai: "OpenAI (GPT)",
  google: "Google (Gemini)",
  deepseek: "DeepSeek",
  openrouter: "OpenRouter（聚合网关）",
  custom: "自定义 OpenAI 兼容端点",
};

export default function Settings() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">设置</h1>
      <KeysSection />
      <GeneralSection />
      <PasswordSection />
    </div>
  );
}

// ---------- API Key 管理（BYOK）----------
function KeysSection() {
  const [keys, setKeys] = useState<any[]>([]);
  const [raw, setRaw] = useState("");
  const [provider, setProvider] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [msg, setMsg] = useState("");
  const [needProvider, setNeedProvider] = useState(false);
  const [busy, setBusy] = useState(false);

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
        setMsg(`已保存 ${r.masked}（${r.provider}）· ${r.message}`);
        setRaw(""); setProvider(""); setBaseUrl(""); setNeedProvider(false);
        load();
      }
    } catch (err: any) {
      setMsg(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">API Key</h2>
      <p className="text-sm text-slate-500">
        粘贴即可——自动去除空格/引号/Bearer 前缀、全角转半角、识别厂商，保存时实时探活校验。
      </p>
      <form onSubmit={add} className="card space-y-2">
        <textarea className="input font-mono" rows={2} value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder="粘贴你的 API Key（怎么粘都行，系统会自动修正格式）" />
        {(needProvider || provider || baseUrl) && (
          <select className="input" value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="">选择厂商…</option>
            {Object.entries(PROVIDER_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        )}
        <details>
          <summary className="cursor-pointer text-xs text-slate-400">
            高级：自定义 OpenAI 兼容端点（各类中转站/自部署 vLLM）
          </summary>
          <input className="input mt-2" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://your-gateway.example.com/v1" />
        </details>
        <button className="btn-primary" disabled={busy}>{busy ? "校验中…" : "保存并校验"}</button>
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
                onClick={() => post(`/api/keys/${k.id}/probe`, {}).then((r) => { alert(r.message); load(); })}>
                探活
              </button>
              <button className="btn-ghost text-xs text-red-600"
                onClick={() => del(`/api/keys/${k.id}`).then(load)}>删除</button>
            </div>
          </div>
        ))}
        {keys.length === 0 && (
          <p className="text-sm text-amber-600">
            尚未配置任何 Key——系统当前运行在 dry-run 模式（LLM 返回模拟响应，不产生费用）。
          </p>
        )}
      </div>
    </section>
  );
}

// ---------- 业务设置 ----------
function GeneralSection() {
  const [s, setS] = useState<any>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => { api("/api/settings").then(setS).catch(() => {}); }, []);
  if (!s) return null;

  async function save() {
    setMsg("");
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
        },
      });
      setMsg("已保存，立即生效");
    } catch (err: any) { setMsg(err.message); }
  }

  const set = (k: string) => (e: any) =>
    setS({ ...s, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">运行参数</h2>
      <div className="card space-y-4 text-sm">
        <label className="block">
          <span className="mb-1 block font-medium">我的研究方向（用于论文初筛与总结）</span>
          <textarea className="input" rows={2} value={s.research_profile} onChange={set("research_profile")}
            placeholder="如：离散 CFR 与多智能体辩论中的灾难性遗忘问题" />
        </label>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className="mb-1 block font-medium">每日预算上限（美元）</span>
            <input className="input" type="number" step="0.5" min="0"
              value={s.daily_budget_usd} onChange={set("daily_budget_usd")} />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">脱敏等级</span>
            <select className="input" value={s.redact_level} onChange={set("redact_level")}>
              <option value="low">低（只拦截明确凭证）</option>
              <option value="medium">中（凭证+PII 占位符替换）</option>
              <option value="high">高（高危命中直接阻断出境）</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">轻量层模型（解析/初筛/简报）</span>
            <input className="input font-mono" value={s.model_light} onChange={set("model_light")} />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">前沿层模型（总结/综述）</span>
            <input className="input font-mono" value={s.model_frontier} onChange={set("model_frontier")} />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">初筛相关度阈值（0-1）</span>
            <input className="input" type="number" step="0.05" min="0" max="1"
              value={s.relevance_threshold} onChange={set("relevance_threshold")} />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">简报生成时间（小时，0-23）</span>
            <input className="input" type="number" min="0" max="23"
              value={s.briefing_hour} onChange={set("briefing_hour")} />
          </label>
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!s.cache_enabled} onChange={set("cache_enabled")} />
          启用语义缓存（相同请求直接复用历史结果，省钱）
        </label>
        <button className="btn-primary" onClick={save}>保存设置</button>
        {msg && <p className="text-slate-600">{msg}</p>}
      </div>
    </section>
  );
}

// ---------- 修改密码 ----------
function PasswordSection() {
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [msg, setMsg] = useState("");

  async function change(e: React.FormEvent) {
    e.preventDefault();
    try {
      await post("/api/auth/change-password", { old_password: oldPw, new_password: newPw });
      setMsg("密码已修改"); setOldPw(""); setNewPw("");
    } catch (err: any) { setMsg(err.message); }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">账号</h2>
      <form onSubmit={change} className="card flex flex-col gap-2 md:flex-row">
        <input className="input" type="password" placeholder="原密码" value={oldPw}
          onChange={(e) => setOldPw(e.target.value)} />
        <input className="input" type="password" placeholder="新密码（至少 8 位）" value={newPw}
          onChange={(e) => setNewPw(e.target.value)} />
        <button className="btn-primary justify-center">修改密码</button>
      </form>
      {msg && <p className="text-sm text-slate-600">{msg}</p>}
    </section>
  );
}
