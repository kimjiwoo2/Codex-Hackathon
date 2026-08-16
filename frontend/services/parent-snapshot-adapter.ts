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
