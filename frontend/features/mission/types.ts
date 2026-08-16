export type MissionStatus = 'WAITING' | 'GOING' | 'SHOPPING' | 'RETURNING' | 'COMPLETED';

export type MissionCoordinate = {
  latitude: number;
  longitude: number;
};

export type MissionItem = {
  id: string;
  name: string;
  brand: string | null;
  quantity: number;
  unit: string;
  size: string;
  verified: boolean;
};

export type ItemVerdict = 'MATCH' | 'SIMILAR' | 'MISMATCH' | 'UNKNOWN';
export type MissionItemDto = { itemId: string; name: string; brand: string | null; size: string | null; verdict: ItemVerdict; detectedLabel: string | null };

export type MissionDraft = {
  home: MissionCoordinate;
  store: MissionCoordinate;
  destination: { name: string; distance: string; duration: string };
  item: MissionItem;
  shareLocation: boolean;
  notifyOffRoute: boolean;
};

/** UI snapshot retained for child-flow consumers that do not call the API directly. */
export type MissionSnapshot = Omit<MissionDraft, 'home' | 'store'> & {
  id: string;
  status: MissionStatus;
  updatedAt: string;
};

export type CreateMissionResult = {
  missionId: string;
  joinCode: string;
  joinCodeExpiresAt: string;
  parentToken: string;
  items: MissionItemDto[];
};

export interface JoinMissionResult extends Record<string, unknown> {
  missionId: string;
  childToken: string;
  status: MissionStatus;
  instructionCode: string;
  message: string;
  items: MissionItemDto[];
}

export type ItemVerificationResult = { verdict: ItemVerdict; message: string; detectedLabel: string | null; status: 'SHOPPING' | 'RETURNING' };
