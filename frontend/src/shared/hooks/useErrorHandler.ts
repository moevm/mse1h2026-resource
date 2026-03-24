import { useCallback, useState } from "react";

export function useErrorHandler() {
    const [error, setError] = useState<string | null>(null);

    const asMessage = useCallback((value: unknown, fallback: string) => {
        if (value instanceof DOMException && value.name === "AbortError") {
            return null;
        }
        if (value instanceof Error && value.message) {
            return value.message;
        }
        return fallback;
    }, []);

    const handleError = useCallback(
        (value: unknown, fallback: string) => {
            const message = asMessage(value, fallback);
            if (message) {
                setError(message);
            }
            return message;
        },
        [asMessage],
    );

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    return {
        error,
        setError,
        handleError,
        clearError,
    };
}
