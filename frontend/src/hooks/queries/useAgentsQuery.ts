import { useQuery } from "@tanstack/react-query";
import { fetchAgents } from "../../api";

export function useAgentsQuery() {
    return useQuery({
        queryKey: ["agents"],
        queryFn: fetchAgents,
    });
}
