// src/dashboard/InviteManagePage.tsx
import { useState, useEffect, useCallback } from "react";
import toast from "react-hot-toast";
import { api } from "../api";

interface Invite {
  id: number;
  email: string;
  role: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string | null;
  organization_name: string;
  is_pending: boolean;
}

const ROLE_OPTIONS = ["member", "analyst", "admin"];

const InviteManagePage = () => {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [submitting, setSubmitting] = useState(false);

  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchInvites = useCallback(async () => {
    try {
      const res = await api.get<{ invites: Invite[] }>("/auth/invites");
      setInvites(res.data.invites);
    } catch (err: unknown) {
      const status =
        typeof err === "object" && err !== null && "response" in err
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
      if (status === 403) {
        setAccessDenied(true);
      } else {
        toast.error("Failed to load invites");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchInvites();
  }, [fetchInvites]);

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      toast.error("Email is required");
      return;
    }
    setSubmitting(true);
    setGeneratedLink(null);
    setCopied(false);
    try {
      const res = await api.post<{ invite_token: string }>("/auth/invite", { email: email.trim(), role });
      const token = res.data.invite_token;
      const link = `${window.location.origin}/invite/${token}`;
      setGeneratedLink(link);
      setEmail("");
      toast.success("Invite created");
      void fetchInvites();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Failed to create invite"
            : "Failed to create invite";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (!generatedLink) return;
    navigator.clipboard.writeText(generatedLink).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      toast.error("Could not copy to clipboard");
    });
  };

  const pendingInvites = invites.filter((i) => i.is_pending);
  const pastInvites = invites.filter((i) => !i.is_pending);

  if (accessDenied) {
    return (
      <div className="bg-gray-100 dark:bg-gray-800 min-h-screen py-10 px-4 flex items-start justify-center">
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow p-8 max-w-md w-full text-center space-y-3 mt-10">
          <div className="text-3xl">🔒</div>
          <h2 className="text-lg font-semibold text-red-600 dark:text-red-400">Admin Access Required</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Only organization admins can manage team invites.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-100 dark:bg-gray-800 min-h-screen py-10 px-4 text-gray-800 dark:text-white">
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-semibold">Team Invites</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Invite team members to your organization by email. Share the generated link with them.
          </p>
        </div>

        {/* Create Invite Form */}
        <section className="bg-white dark:bg-gray-900 rounded-xl shadow p-6 space-y-4">
          <h2 className="font-semibold text-lg">Create Invite</h2>
          <form onSubmit={(e) => void handleCreateInvite(e)} className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="email"
                placeholder="colleague@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {r.charAt(0).toUpperCase() + r.slice(1)}
                  </option>
                ))}
              </select>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {submitting ? "Sending…" : "Send Invite"}
              </button>
            </div>
          </form>

          {/* Generated Link */}
          {generatedLink && (
            <div className="mt-2 p-3 bg-green-50 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-lg space-y-2">
              <p className="text-xs text-green-700 dark:text-green-300 font-medium">
                Invite link created — share it with the recipient:
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs break-all text-green-800 dark:text-green-200 bg-green-100 dark:bg-green-900/50 px-2 py-1 rounded">
                  {generatedLink}
                </code>
                <button
                  onClick={handleCopy}
                  className="shrink-0 px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition"
                >
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Pending Invites */}
        <section className="bg-white dark:bg-gray-900 rounded-xl shadow p-6">
          <h2 className="font-semibold text-lg mb-4">Pending Invites</h2>
          {loading ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : pendingInvites.length === 0 ? (
            <p className="text-sm text-gray-400">No pending invites.</p>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {pendingInvites.map((inv) => (
                <li key={inv.id} className="py-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium">{inv.email}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Role: <span className="capitalize">{inv.role}</span> · Expires:{" "}
                      {new Date(inv.expires_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300">
                    Pending
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Past Invites */}
        {pastInvites.length > 0 && (
          <section className="bg-white dark:bg-gray-900 rounded-xl shadow p-6">
            <h2 className="font-semibold text-lg mb-4">Past Invites</h2>
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {pastInvites.map((inv) => (
                <li key={inv.id} className="py-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium">{inv.email}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Role: <span className="capitalize">{inv.role}</span>
                    </p>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      inv.accepted_at
                        ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
                        : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                    }`}
                  >
                    {inv.accepted_at ? "Accepted" : "Expired"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
};

export default InviteManagePage;
