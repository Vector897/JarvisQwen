"use client";

import { useEffect, useState } from "react";
import { api, post, put, del } from "@/lib/api";
import { useToast } from "@/components/toast";

const PROVIDER_LABEL: Record<string, string> = {
  anthropic: "Anthropic (Claude)",
  openai: "OpenAI (GPT)",
  google: "Google (Gemini)",
  deepseek: "DeepSeek",
  openrouter: "OpenRouter（聚合网关）",
  custom: "自定义 OpenAI 兼容端点",
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

// ---------- API Key 管理（BYOK）----------
function KeysSection() {
  const [keys, setKeys] = useState<any[]>([]);
  const [raw, setRaw] = useState("");
  const [provider, setProvider] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [msg, setMsg] = useState("");
  const [needProvider, setNeedProvider] = useState(false);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

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
        toast(`已保存 ${r.masked}（${r.provider}）· ${r.message}`, "success");
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
                onClick={() => post(`/api/keys/${k.id}/probe`, {}).then((r) => { toast(r.message, r.ok ? "success" : "error"); load(); })}>
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
  const toast = useToast();

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
      toast("已保存，立即生效", "success");
    } catch (err: any) { toast(err.message, "error"); }
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
          启用语义缓存（相同/相近请求直接复用历史结果，省钱）
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!s.cascade_enabled} onChange={set("cascade_enabled")} />
          启用模型级联（跨库问答等场景先用轻量层回答，置信度不足才升级前沿层）
        </label>
        {s.cascade_enabled && (
          <label className="block max-w-xs">
            <span className="mb-1 block font-medium">级联置信度阈值（0-1，越低越少升级）</span>
            <input className="input" type="number" step="0.05" min="0" max="1"
              value={s.cascade_confidence_threshold} onChange={set("cascade_confidence_threshold")} />
          </label>
        )}
        <button className="btn-primary" onClick={save}>保存设置</button>
      </div>
    </section>
  );
}

// ---------- 推送通知 ----------
function NotifySection() {
  const [s, setS] = useState<any>(null);
  const toast = useToast();

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
      // 密钥字段：留空则不提交（后端也会兜底跳过空值，双重保险）
      if (s.telegram_bot_token) values.telegram_bot_token = s.telegram_bot_token;
      if (s.smtp_password) values.smtp_password = s.smtp_password;
      await put("/api/settings", { values });
      toast("推送设置已保存", "success");
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
      <h2 className="text-lg font-semibold">推送通知</h2>
      <p className="text-sm text-slate-500">简报生成、预算熔断时推送到 Telegram 或邮箱，离开网页也能收到。</p>
      <div className="card space-y-4 text-sm">
        <label className="flex items-center gap-2 font-medium">
          <input type="checkbox" checked={!!s.notify_telegram_enabled} onChange={set("notify_telegram_enabled")} />
          启用 Telegram 推送
        </label>
        {s.notify_telegram_enabled && (
          <div className="grid gap-3 pl-6 md:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs text-slate-500">Bot Token（找 @BotFather 申请）</span>
              <input className="input font-mono" placeholder={s.telegram_bot_token_is_set ? "已配置，留空保持不变" : ""}
                value={s.telegram_bot_token || ""} onChange={set("telegram_bot_token")} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-slate-500">Chat ID</span>
              <input className="input font-mono" value={s.telegram_chat_id || ""} onChange={set("telegram_chat_id")} />
            </label>
          </div>
        )}
        <label className="flex items-center gap-2 font-medium">
          <input type="checkbox" checked={!!s.notify_email_enabled} onChange={set("notify_email_enabled")} />
          启用邮件推送（SMTP）
        </label>
        {s.notify_email_enabled && (
          <div className="grid gap-3 pl-6 md:grid-cols-2">
            <input className="input" placeholder="SMTP 服务器，如 smtp.gmail.com" value={s.smtp_host || ""} onChange={set("smtp_host")} />
            <input className="input" type="number" placeholder="端口（587）" value={s.smtp_port || 587} onChange={set("smtp_port")} />
            <input className="input" placeholder="用户名" value={s.smtp_user || ""} onChange={set("smtp_user")} />
            <input className="input" type="password" placeholder={s.smtp_password_is_set ? "已配置，留空保持不变" : "密码/App Password"}
              value={s.smtp_password || ""} onChange={set("smtp_password")} />
            <input className="input" placeholder="发件地址" value={s.smtp_from || ""} onChange={set("smtp_from")} />
            <input className="input" placeholder="收件地址" value={s.smtp_to || ""} onChange={set("smtp_to")} />
          </div>
        )}
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={!!s.notify_on_budget_cutoff} onChange={set("notify_on_budget_cutoff")} />
          预算熔断时也推送（强烈建议开启，避免任务静默挂起没人知道）
        </label>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={save}>保存</button>
          <button className="btn-ghost" onClick={testNotify}>发送测试推送</button>
        </div>
      </div>
    </section>
  );
}

// ---------- Zotero 同步 ----------
function ZoteroSection() {
  const [s, setS] = useState<any>(null);
  const toast = useToast();
  useEffect(() => { api("/api/settings").then(setS).catch(() => {}); }, []);
  if (!s) return null;

  async function save() {
    try {
      const values: Record<string, any> = {
        zotero_library_id: s.zotero_library_id, zotero_library_type: s.zotero_library_type,
      };
      if (s.zotero_api_key) values.zotero_api_key = s.zotero_api_key;
      await put("/api/settings", { values });
      toast("Zotero 配置已保存", "success");
    } catch (err: any) { toast(err.message, "error"); }
  }

  const set = (k: string) => (e: any) => setS({ ...s, [k]: e.target.value });

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Zotero 同步</h2>
      <p className="text-sm text-slate-500">
        单向推送：在知识库页把归档论文一键推入你的 Zotero 文献库。API Key 在 Zotero 设置 → Security 里生成。
      </p>
      <div className="card grid gap-3 text-sm md:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-xs text-slate-500">Zotero API Key</span>
          <input className="input font-mono" placeholder={s.zotero_api_key_is_set ? "已配置，留空保持不变" : ""}
            value={s.zotero_api_key || ""} onChange={set("zotero_api_key")} />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-slate-500">Library ID</span>
          <input className="input font-mono" value={s.zotero_library_id || ""} onChange={set("zotero_library_id")} />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-slate-500">Library 类型</span>
          <select className="input" value={s.zotero_library_type || "user"} onChange={set("zotero_library_type")}>
            <option value="user">个人库（user）</option>
            <option value="group">团队库（group）</option>
          </select>
        </label>
        <div className="flex items-end">
          <button className="btn-primary" onClick={save}>保存</button>
        </div>
      </div>
    </section>
  );
}

// ---------- 用户管理（管理员）----------
function UsersSection() {
  const [users, setUsers] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [role, setRole] = useState("member");
  const toast = useToast();

  const load = () => api("/api/users").then(setUsers).catch(() => {});
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      const r = await post("/api/users", { name, role });
      toast(`已创建 ${r.name}，临时密码：${r.temp_password}（请截图告知对方）`, "success");
      setName("");
      load();
    } catch (err: any) { toast(err.message, "error"); }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">用户管理（管理员）</h2>
      <form onSubmit={create} className="card flex flex-col gap-2 md:flex-row">
        <input className="input flex-1" placeholder="用户名" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="input md:w-40" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="member">member（可下任务）</option>
          <option value="viewer">viewer（只读）</option>
          <option value="admin">admin（全权限）</option>
        </select>
        <button className="btn-primary justify-center">创建账号</button>
      </form>
      <div className="space-y-2">
        {users.map((u) => (
          <div key={u.id} className="card flex items-center justify-between text-sm">
            <span className="font-medium">{u.name}</span>
            <div className="flex items-center gap-2">
              <select className="input w-36" value={u.role}
                onChange={(e) => put(`/api/users/${u.id}/role`, { role: e.target.value })
                  .then(() => { toast("角色已更新", "success"); load(); })
                  .catch((err) => toast(err.message, "error"))}>
                <option value="member">member</option>
                <option value="viewer">viewer</option>
                <option value="admin">admin</option>
              </select>
              <button className="btn-ghost text-xs text-red-600"
                onClick={() => del(`/api/users/${u.id}`).then(() => { toast("已删除用户", "info"); load(); })}>
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------- 修改密码 ----------
function PasswordSection() {
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const toast = useToast();

  async function change(e: React.FormEvent) {
    e.preventDefault();
    try {
      await post("/api/auth/change-password", { old_password: oldPw, new_password: newPw });
      toast("密码已修改", "success"); setOldPw(""); setNewPw("");
    } catch (err: any) { toast(err.message, "error"); }
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
    </section>
  );
}
