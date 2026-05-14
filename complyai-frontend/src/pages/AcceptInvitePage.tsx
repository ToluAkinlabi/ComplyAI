// src/pages/AcceptInvitePage.tsx
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { api } from "../api";
import { setAuthToken, setRefreshToken } from "../auth";

interface InvitePreview {
  email: string;
  role: string;
  organization_name: string;
  expires_at: string;
}

const AcceptInvitePage = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(true);

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setPreviewError("No invite token provided.");
      setLoadingPreview(false);
      return;
    }
    api
      .get<InvitePreview>(`/auth/invite/preview/${token}`)
      .then((res: { data: InvitePreview }) => {
        setPreview(res.data);
      })
      .catch((err: unknown) => {
        const detail =
          typeof err === "object" &&
          err !== null &&
          "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined;
        setPreviewError(detail ?? "This invite is invalid or has expired.");
      })
      .finally(() => {
        setLoadingPreview(false);
      });
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post<{ access_token: string; refresh_token: string }>("/auth/register-invite", {
        invite_token: token,
        full_name: fullName.trim(),
        password,
      });
      setAuthToken(res.data.access_token);
      setRefreshToken(res.data.refresh_token);
      toast.success("Welcome to ComplyAI!");
      navigate("/dashboard");
    } catch (err: unknown) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      toast.error(detail ?? "Registration failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingPreview) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-white">
        <p>Verifying invite…</p>
      </div>
    );
  }

  if (previewError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 px-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-8 max-w-md w-full text-center space-y-4">
          <div className="text-4xl">🔒</div>
          <h1 className="text-xl font-semibold text-red-600 dark:text-red-400">Invite Invalid</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{previewError}</p>
          <a href="/login" className="inline-block mt-2 text-sm text-blue-600 hover:underline">
            Go to Login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 px-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-8 max-w-md w-full space-y-6">
        {/* Header */}
        <div className="text-center space-y-1">
          <div className="text-3xl">🎉</div>
          <h1 className="text-xl font-semibold text-gray-800 dark:text-white">You're invited!</h1>
          {preview && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Join <span className="font-medium text-gray-700 dark:text-gray-200">{preview.organization_name}</span> as a{" "}
              <span className="capitalize font-medium text-gray-700 dark:text-gray-200">{preview.role}</span>
            </p>
          )}
          {preview && (
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Registering as: {preview.email}
            </p>
          )}
        </div>

        {/* Registration Form */}
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Jane Smith"
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
              Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
              minLength={8}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
              Confirm Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat password"
              required
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {submitting ? "Creating account…" : "Create Account & Join"}
          </button>
        </form>

        <p className="text-xs text-center text-gray-400">
          Already have an account?{" "}
          <a href="/login" className="text-blue-500 hover:underline">
            Log in
          </a>
        </p>
      </div>
    </div>
  );
};

export default AcceptInvitePage;
