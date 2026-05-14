import { FormEvent, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { api } from "../api";
import { isAuthenticated, setAuthToken, setRefreshToken } from "../auth";

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("admin@complyai.io");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const nextPath = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const next = params.get("next") || "/dashboard/upload";
    return next.startsWith("/") ? next : "/dashboard/upload";
  }, [location.search]);

  useEffect(() => {
    if (isAuthenticated()) {
      navigate(nextPath, { replace: true });
    }
  }, [navigate, nextPath]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }

    try {
      setSubmitting(true);
      setError("");

      const formData = new URLSearchParams();
      formData.append("username", email.trim());
      formData.append("password", password);

      const response = await api.post("/login", formData, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      const token = response.data?.access_token;
      if (!token || typeof token !== "string") {
        throw new Error("Missing token in login response");
      }

      setAuthToken(token);
      setRefreshToken(typeof response.data?.refresh_token === "string" ? response.data.refresh_token : null);
      toast.success("Signed in successfully");
      navigate(nextPath, { replace: true });
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || "Login failed";
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 space-y-6">
        <div className="text-center space-y-2">
          <img src="/comply.png" alt="ComplyAI logo" className="mx-auto h-12 w-auto" />
          <h1 className="text-2xl font-semibold text-slate-900">ComplyAI Sign In</h1>
          <p className="text-sm text-slate-600">Access your organization compliance workspace.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm text-slate-700 mb-1">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm text-slate-700 mb-1">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your password"
            />
          </div>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="text-xs text-center text-slate-500">Default local admin: admin@complyai.io</p>
      </div>
    </div>
  );
};

export default LoginPage;
