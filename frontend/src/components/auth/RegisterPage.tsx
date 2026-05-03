import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

export function RegisterPage() {
    const [email, setEmail] = useState("");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const register = useAuthStore((s) => s.register);
    const isLoading = useAuthStore((s) => s.isLoading);
    const navigate = useNavigate();

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);

        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        try {
            await register({ email, username, password });
            navigate("/", { replace: true });
        } catch (err) {
            setError(err instanceof Error ? err.message : "Registration failed");
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
            <div className="w-full max-w-sm">
                <h1 className="text-2xl font-bold text-slate-100 text-center mb-8">Create Account</h1>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && (
                        <div className="rounded-md bg-red-900/30 px-3 py-2 text-sm text-red-400">
                            {error}
                        </div>
                    )}

                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            placeholder="you@example.com"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            minLength={3}
                            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            placeholder="Choose a username"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={6}
                            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            placeholder="Min 6 characters"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Confirm Password</label>
                        <input
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            placeholder="Repeat password"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {isLoading ? "Creating account..." : "Create Account"}
                    </button>
                </form>

                <p className="mt-6 text-center text-sm text-slate-500">
                    Already have an account?{" "}
                    <Link to="/login" className="text-blue-400 hover:text-blue-300">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}
