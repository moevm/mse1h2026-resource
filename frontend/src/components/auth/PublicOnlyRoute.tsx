import { Navigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { Spinner } from "../common/Spinner";

export function PublicOnlyRoute({ children }: Readonly<{ children: React.ReactNode }>) {
    const user = useAuthStore((s) => s.user);
    const isInitialized = useAuthStore((s) => s.isInitialized);

    if (!isInitialized) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <Spinner size="lg" label="Loading..." />
            </div>
        );
    }

    if (user) {
        return <Navigate to="/" replace />;
    }

    return <>{children}</>;
}
