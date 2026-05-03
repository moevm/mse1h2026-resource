import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { Spinner } from "../common/Spinner";

export function ProtectedRoute({ children }: Readonly<{ children: React.ReactNode }>) {
    const accessToken = useAuthStore((s) => s.accessToken);
    const isLoading = useAuthStore((s) => s.isLoading);
    const location = useLocation();

    if (isLoading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                <Spinner size="lg" label="Loading..." />
            </div>
        );
    }

    if (!accessToken) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return <>{children}</>;
}
