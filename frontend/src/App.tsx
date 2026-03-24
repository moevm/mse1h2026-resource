import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { Spinner } from "./shared/components/Spinner";

const DashboardPage = lazy(() => import("./components/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const GraphPage = lazy(() => import("./components/pages/GraphPage").then((m) => ({ default: m.GraphPage })));
const AgentsPage = lazy(() => import("./components/pages/AgentsPage").then((m) => ({ default: m.AgentsPage })));
const MapperPage = lazy(() => import("./components/mapper/MapperPage").then((m) => ({ default: m.MapperPage })));

export default function App() {
    return (
        <ErrorBoundary>
            <BrowserRouter>
                <Suspense
                    fallback={
                        <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-300">
                            <Spinner size="lg" label="Loading page..." />
                        </div>
                    }
                >
                    <Routes>
                        <Route path="/graph" element={<GraphPage />} />
                        <Route
                            path="/"
                            element={
                                <AppLayout>
                                    <DashboardPage />
                                </AppLayout>
                            }
                        />
                        <Route
                            path="/agents"
                            element={
                                <AppLayout>
                                    <AgentsPage />
                                </AppLayout>
                            }
                        />
                        <Route
                            path="/mapper"
                            element={
                                <AppLayout>
                                    <MapperPage />
                                </AppLayout>
                            }
                        />
                    </Routes>
                </Suspense>
            </BrowserRouter>
        </ErrorBoundary>
    );
}