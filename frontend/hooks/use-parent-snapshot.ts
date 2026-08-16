import { useCallback, useEffect, useState } from 'react';

import {
  fetchParentSnapshot,
  isParentSnapshotCredentialReady,
  ParentSnapshotPollingController,
  type ParentSnapshot,
  type ParentSnapshotPollingState,
} from '@/services/parent-snapshot-adapter';

const POLL_INTERVAL_MS = 3_000;
const pollingCache = new Map<string, ParentSnapshotPollingState>();
const unavailableCredentialsMessage = '실제 미션이 연결되면 위치를 확인할 수 있습니다.';

type SnapshotState = {
  snapshot: ParentSnapshot | null;
  events: ParentSnapshotPollingState['events'];
  loading: boolean;
  error: string | null;
};

export function useParentSnapshot(missionId: string | undefined, parentToken: string | undefined) {
  const credentialsReady = isParentSnapshotCredentialReady(missionId, parentToken);
  const cacheKey = credentialsReady ? `${missionId}:${parentToken}` : undefined;
  const [state, setState] = useState<SnapshotState>({
    snapshot: null,
    events: [],
    loading: credentialsReady,
    error: credentialsReady ? null : unavailableCredentialsMessage,
  });
  const [refreshRequest, setRefreshRequest] = useState(0);

  const refresh = useCallback(() => setRefreshRequest((current) => current + 1), []);

  useEffect(() => {
    if (!cacheKey || !missionId || !parentToken) {
      setState({ snapshot: null, events: [], loading: false, error: unavailableCredentialsMessage });
      return;
    }

    let mounted = true;
    const controller = new ParentSnapshotPollingController(
      pollingCache.get(cacheKey) ?? { cursor: 0, events: [] },
      (afterEventId) => fetchParentSnapshot(missionId, parentToken, afterEventId),
    );

    const poll = async () => {
      const result = await controller.refresh();
      if (!mounted || result.kind === 'skipped') return;
      if (result.kind === 'error') {
        const message = result.error instanceof Error ? result.error.message : '위치 정보를 불러오지 못했습니다.';
        setState((current) => ({ ...current, loading: false, error: message }));
        return;
      }

      pollingCache.set(cacheKey, result.polling);
      setState({ snapshot: result.snapshot, events: result.polling.events, loading: false, error: null });
    };

    void poll();
    const interval = setInterval(() => void poll(), POLL_INTERVAL_MS);
    return () => {
      mounted = false;
      controller.dispose();
      clearInterval(interval);
    };
  }, [cacheKey, missionId, parentToken, refreshRequest]);

  return { ...state, refresh };
}
