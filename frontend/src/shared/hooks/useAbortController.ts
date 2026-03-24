import { useCallback, useEffect, useRef } from "react";

export function useAbortController() {
    const controllerRef = useRef<AbortController | null>(null);

    const refreshController = useCallback(() => {
        controllerRef.current?.abort();
        const next = new AbortController();
        controllerRef.current = next;
        return next;
    }, []);

    const abort = useCallback(() => {
        controllerRef.current?.abort();
    }, []);

    useEffect(() => {
        return () => {
            controllerRef.current?.abort();
        };
    }, []);

    return {
        refreshController,
        abort,
        getSignal: () => controllerRef.current?.signal,
    };
}
