"use client";

import { useState } from "react";
import { post } from "@/lib/api";
import { useLang } from "@/lib/i18n";

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { t, lang, toggle } = useLang();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await post("/api/auth/login", { username, password });
      window.location.href = "/dashboard";
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4 relative">
        <button type="button" onClick={toggle}
          className="btn-ghost absolute right-4 top-4 px-2 py-1 text-xs">{lang === "zh" ? "EN" : "中"}</button>
        <h1 className="text-xl font-bold">{t("login.title")}</h1>
        <p className="text-xs text-slate-500">{t("login.hint")}</p>
        <input className="input" placeholder={t("login.username")} value={username}
          onChange={(e) => setUsername(e.target.value)} />
        <input className="input" type="password" placeholder={t("login.password")} value={password}
          onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="btn-primary w-full justify-center" type="submit">{t("login.submit")}</button>
      </form>
    </div>
  );
}
