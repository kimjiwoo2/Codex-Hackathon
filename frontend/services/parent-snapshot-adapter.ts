export type ParentMissionStatus = 'WAITING' | 'GOING' | 'SHOPPING' | 'RETURNING' | 'COMPLETED' | 'CANCELED';

export type ParentSnapshotEvent = {
  eventId: number;
  eventType: string;
  payload: Record<string, unknown>;
  createdAt: string;
};

export type ParentSnapshot = {
  missionId: string;
  status: ParentMissionStatus;
  location: {
    latitude: number;
    longitude: number;
    observedAt: string;
    accuracyM: number | null;
  } | null;
  locationStale: boolean;
  remainingDistanceM: number;
  items: Array<{
    itemId: string;
    name: string;
    verdict: 'MATCH' | 'SIMILAR' | 'MISMATCH' | 'UNKNOWN';
    detectedLabel: string | null;
    verifiedAt: string | null;
  }>;
  events: ParentSnapshotEvent[];
  nextEventId: number;
};

export class ParentSnapshotRequestError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = 'ParentSnapshotRequestError';
  }
}

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export function isParentSnapshotCredentialReady(
  missionId: string | undefined,
  parentToken: string | undefined,
): missionId is string {
  return Boolean(
    missionId &&
      parentToken &&
      !missionId.startsWith('demo-') &&
      !parentToken.startsWith('mock-'),
  );
}

function apiBaseUrl(): string {
  const value = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (!value) {
    throw new ParentSnapshotRequestError('서버 주소가 설정되지 않아 위치를 불러올 수 없습니다.');
  }
  return value.replace(/\/$/, '');
}

export async function fetchParentSnapshot(
  missionId: string,
  parentToken: string,
  afterEventId: number,
  request: FetchLike = fetch,
): Promise<ParentSnapshot> {
  if (!isParentSnapshotCredentialReady(missionId, parentToken)) {
    throw new ParentSnapshotRequestError('실제 미션 연결 후 위치를 확인할 수 있습니다.');
  }
  const url = `${apiBaseUrl()}/missions/${encodeURIComponent(missionId)}/snapshot?afterEventId=${afterEventId}`;
  const response = await request(url, {
    headers: { Authorization: `Bearer ${parentToken}` },
  });
  if (!response.ok) {
    throw new ParentSnapshotRequestError('위치 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.', response.status);
  }
  return (await response.json()) as ParentSnapshot;
}

export type ParentSnapshotPollingState = {
  cursor: number;
  events: ParentSnapshotEvent[];
};

export function applySnapshot(
  current: ParentSnapshotPollingState,
  snapshot: ParentSnapshot,
): ParentSnapshotPollingState {
  const eventsById = new Map(current.events.map((event) => [event.eventId, event]));
  for (const event of snapshot.events) eventsById.set(event.eventId, event);

  return {
    cursor: Math.max(current.cursor, snapshot.nextEventId),
    events: [...eventsById.values()].sort((left, right) => left.eventId - right.eventId),
  };
}

type SnapshotFetcher = (afterEventId: number) => Promise<ParentSnapshot>;

export type ParentSnapshotRefreshResult =
  | { kind: 'updated'; snapshot: ParentSnapshot; polling: ParentSnapshotPollingState }
  | { kind: 'error'; error: unknown }
  | { kind: 'skipped' };

/** Serializes a credential session's requests and makes disposed responses inert. */
export class ParentSnapshotPollingController {
  private active = true;
  private inFlight = false;

  constructor(
    private polling: ParentSnapshotPollingState,
    private readonly fetchSnapshot: SnapshotFetcher,
  ) {}

  get current(): ParentSnapshotPollingState {
    return this.polling;
  }

  dispose() {
    this.active = false;
  }

  async refresh(): Promise<ParentSnapshotRefreshResult> {
    if (!this.active || this.inFlight) return { kind: 'skipped' };

    this.inFlight = true;
    try {
      const snapshot = await this.fetchSnapshot(this.polling.cursor);
      if (!this.active) return { kind: 'skipped' };

      this.polling = applySnapshot(this.polling, snapshot);
      return { kind: 'updated', snapshot, polling: this.polling };
    } catch (error) {
      return this.active ? { kind: 'error', error } : { kind: 'skipped' };
    } finally {
      this.inFlight = false;
    }
  }
}
