"use client";

import { useState } from "react";
import { post } from "@/lib/api";

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

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
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold">登录 AAOS</h1>
        <p className="text-xs text-slate-500">
          首次部署的初始密码在服务器 data/admin_password.txt
        </p>
        <input className="input" placeholder="用户名" value={username}
          onChange={(e) => setUsername(e.target.value)} />
        <input className="input" type="password" placeholder="密码" value={password}
          onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="btn-primary w-full justify-center" type="submit">登录</button>
      </form>
    </div>
  );
}
