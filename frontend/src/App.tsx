import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { DashboardPage } from "./components/pages/DashboardPage";
import { GraphPage } from "./components/pages/GraphPage";
import { AgentsPage } from "./components/pages/AgentsPage";

export default function App() {
    return (
        <BrowserRouter>
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
            </Routes>
        </BrowserRouter>
    );
}
