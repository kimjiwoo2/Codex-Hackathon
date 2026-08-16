import type { ItemVerificationResult, JoinMissionResult, MissionItemDto } from '../mission/types';

export type ChildMissionState = {
  session: JoinMissionResult | null;
  selectedItem: MissionItemDto | null;
};

export function createChildMissionState(session: JoinMissionResult): ChildMissionState {
  return {
    session,
    selectedItem: selectNextPendingItem(session.items),
  };
}

export function applyVerificationToMission(
  current: ChildMissionState,
  result: ItemVerificationResult,
): ChildMissionState {
  if (!current.session || !current.selectedItem) {
    return current;
  }

  const items = current.session.items.map((item) =>
    item.itemId === current.selectedItem?.itemId
      ? { ...item, verdict: result.verdict, detectedLabel: result.detectedLabel }
      : item,
  );
  const session = { ...current.session, items, status: result.status };

  return {
    session,
    selectedItem: result.status === 'RETURNING' ? null : selectNextPendingItem(items),
  };
}

export function startReturningMission(current: ChildMissionState): ChildMissionState {
  if (!current.session) {
    return current;
  }

  return {
    session: { ...current.session, status: 'RETURNING' },
    selectedItem: null,
  };
}

function selectNextPendingItem(items: MissionItemDto[]): MissionItemDto | null {
  return items.find((item) => item.verdict !== 'MATCH') ?? null;
}
