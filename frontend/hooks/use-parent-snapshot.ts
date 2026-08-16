import { useCallback, useEffect, useRef, useState } from 'react';

import {
  applySnapshot,
  fetchParentSnapshot,
  type ParentSnapshot,
  type ParentSnapshotPollingState,
} from '@/services/parent-snapshot-adapter';

const POLL_INTERVAL_MS = 3_000;
const pollingCache = new Map<string, ParentSnapshotPollingState>();

type SnapshotState = {
  snapshot: ParentSnapshot | null;
  events: ParentSnapshotPollingState['events'];
  loading: boolean;
  error: string | null;
};

export function useParentSnapshot(missionId: string | undefined, parentToken: string | undefined) {
  const cacheKey = missionId && parentToken ? `${missionId}:${parentToken}` : undefined;
  const cacheRef = useRef<ParentSnapshotPollingState>(cacheKey ? pollingCache.get(cacheKey) ?? { cursor: 0, events: [] } : { cursor: 0, events: [] });
  const [state, setState] = useState<SnapshotState>({
    snapshot: null,
    events: cacheRef.current.events,
    loading: Boolean(cacheKey),
    error: null,
  });

  const refresh = useCallback(async () => {
    if (!missionId || !parentToken || !cacheKey) {
      setState({ snapshot: null, events: [], loading: false, error: '조회할 미션 정보가 없습니다.' });
      return;
    }

    try {
      const snapshot = await fetchParentSnapshot(missionId, parentToken, cacheRef.current.cursor);
      cacheRef.current = applySnapshot(cacheRef.current, snapshot);
      pollingCache.set(cacheKey, cacheRef.current);
      setState({ snapshot, events: cacheRef.current.events, loading: false, error: null });
    } catch (error) {
      const message = error instanceof Error ? error.message : '위치 정보를 불러오지 못했습니다.';
      setState((current) => ({ ...current, loading: false, error: message }));
    }
  }, [cacheKey, missionId, parentToken]);

  useEffect(() => {
    cacheRef.current = cacheKey ? pollingCache.get(cacheKey) ?? { cursor: 0, events: [] } : { cursor: 0, events: [] };
    void refresh();
    if (!cacheKey) return;

    const interval = setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [cacheKey, refresh]);

  return { ...state, refresh };
}
