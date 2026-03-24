import { useCallback, useEffect, useState } from "react";
import { useAbortController } from "./useAbortController";
import { useErrorHandler } from "./useErrorHandler";

interface UseResourceOptions<TItem, TCreateReq, TCreateRes> {
    fetcher: (signal?: AbortSignal) => Promise<TItem[]>;
    creator: (payload: TCreateReq, signal?: AbortSignal) => Promise<TCreateRes>;
    loadErrorMessage: string;
    createErrorMessage: string;
    autoLoad?: boolean;
}

export function useResource<TItem, TCreateReq, TCreateRes = TItem>(
    options: UseResourceOptions<TItem, TCreateReq, TCreateRes>,
) {
    const {
        fetcher,
        creator,
        loadErrorMessage,
        createErrorMessage,
        autoLoad = true,
    } = options;

    const [items, setItems] = useState<TItem[]>([]);
    const [loading, setLoading] = useState(false);
    const { error, handleError, clearError } = useErrorHandler();
    const { refreshController } = useAbortController();

    const reload = useCallback(async () => {
        const controller = refreshController();
        setLoading(true);
        try {
            const data = await fetcher(controller.signal);
            setItems(data);
            clearError();
            return data;
        } catch (e: unknown) {
            handleError(e, loadErrorMessage);
            throw e;
        } finally {
            setLoading(false);
        }
    }, [refreshController, fetcher, clearError, handleError, loadErrorMessage]);

    const create = useCallback(
        async (payload: TCreateReq) => {
            const controller = refreshController();
            setLoading(true);
            try {
                const created = await creator(payload, controller.signal);
                clearError();
                await reload();
                return created;
            } catch (e: unknown) {
                handleError(e, createErrorMessage);
                throw e;
            } finally {
                setLoading(false);
            }
        },
        [refreshController, creator, clearError, reload, handleError, createErrorMessage],
    );

    useEffect(() => {
        if (!autoLoad) {
            return;
        }
        void reload();
    }, [autoLoad, reload]);

    return {
        items,
        loading,
        error,
        reload,
        create,
        setItems,
        clearError,
    };
}
