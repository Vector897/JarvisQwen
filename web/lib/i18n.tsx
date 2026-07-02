"use client";

import { createContext, useContext, useEffect, useState } from "react";

/**
 * 轻量 i18n 脚手架：覆盖导航、顶栏、帮助页标题等界面级文案。
 * 范围说明：后端返回的动态内容（任务标题、错误信息、审计摘要等）本身是中文语义生成，
 * 不在此翻译范围内——这是界面语言切换，不是全文机器翻译。V2 如需全量翻译，
 * 可在此字典基础上扩展 key 覆盖面，或接入 next-intl。
 */

const DICT = {
  zh: {
    "nav.dashboard": "仪表盘", "nav.tasks": "任务", "nav.subscriptions": "订阅",
    "nav.library": "知识库", "nav.briefings": "简报", "nav.approvals": "审批",
    "nav.audit": "审计", "nav.settings": "设置", "nav.help": "帮助",
    "topbar.logout": "登出", "topbar.online": "实时连接正常", "topbar.offline": "连接断开，重连中…",
    "common.save": "保存", "common.cancel": "取消", "common.delete": "删除",
  },
  en: {
    "nav.dashboard": "Dashboard", "nav.tasks": "Tasks", "nav.subscriptions": "Subscriptions",
    "nav.library": "Library", "nav.briefings": "Briefings", "nav.approvals": "Approvals",
    "nav.audit": "Audit", "nav.settings": "Settings", "nav.help": "Help",
    "topbar.logout": "Log out", "topbar.online": "Live", "topbar.offline": "Reconnecting…",
    "common.save": "Save", "common.cancel": "Cancel", "common.delete": "Delete",
  },
} as const;

type Lang = keyof typeof DICT;
type Key = keyof typeof DICT["zh"];

const LangCtx = createContext<{ lang: Lang; t: (k: Key) => string; toggle: () => void }>({
  lang: "zh",
  t: (k) => DICT.zh[k] ?? k,
  toggle: () => {},
});
export const useLang = () => useContext(LangCtx);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("zh");

  useEffect(() => {
    const saved = localStorage.getItem("aaos-lang") as Lang | null;
    if (saved && DICT[saved]) setLang(saved);
  }, []);

  function toggle() {
    const next: Lang = lang === "zh" ? "en" : "zh";
    setLang(next);
    localStorage.setItem("aaos-lang", next);
  }

  const t = (k: Key) => DICT[lang][k] ?? DICT.zh[k] ?? k;

  return <LangCtx.Provider value={{ lang, t, toggle }}>{children}</LangCtx.Provider>;
}
