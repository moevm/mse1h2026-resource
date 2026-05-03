import { Suspense, lazy, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { Spinner } from "./shared/components/Spinner";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { LoginPage } from "./components/auth/LoginPage";
import { RegisterPage } from "./components/auth/RegisterPage";
import { useAuthStore } from "./store/authStore";

const DashboardPage = lazy(() => import("./components/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const GraphPage = lazy(() => import("./components/pages/GraphPage").then((m) => ({ default: m.GraphPage })));
const AgentsPage = lazy(() => import("./components/pages/AgentsPage").then((m) => ({ default: m.AgentsPage })));
const MapperPage = lazy(() => import("./components/mapper/MapperPage").then((m) => ({ default: m.MapperPage })));

function AuthInitializer({ children }: Readonly<{ children: React.ReactNode }>) {
    const initializeAuth = useAuthStore((s) => s.initializeAuth);

    useEffect(() => {
        void initializeAuth();
    }, [initializeAuth]);

    return <>{children}</>;
}

export default function App() {
    return (
        <ErrorBoundary>
            <BrowserRouter>
                <AuthInitializer>
                    <Suspense
                        fallback={
                            <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-300">
                                <Spinner size="lg" label="Loading page..." />
                            </div>
                        }
                    >
                        <Routes>
                            <Route path="/login" element={<LoginPage />} />
                            <Route path="/register" element={<RegisterPage />} />
                            <Route
                                path="/graph"
                                element={
                                    <ProtectedRoute>
                                        <GraphPage />
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="/"
                                element={
                                    <ProtectedRoute>
                                        <AppLayout>
                                            <DashboardPage />
                                        </AppLayout>
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="/agents"
                                element={
                                    <ProtectedRoute>
                                        <AppLayout>
                                            <AgentsPage />
                                        </AppLayout>
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="/mapper"
                                element={
                                    <ProtectedRoute>
                                        <AppLayout>
                                            <MapperPage />
                                        </AppLayout>
                                    </ProtectedRoute>
                                }
                            />
                        </Routes>
                    </Suspense>
                </AuthInitializer>
            </BrowserRouter>
        </ErrorBoundary>
    );
}
