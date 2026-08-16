export type MissionStatus = 'WAITING' | 'GOING' | 'SHOPPING' | 'RETURNING' | 'COMPLETED';

export type MissionItem = {
  id: string;
  name: string;
  brand: string | null;
  quantity: number;
  unit: string;
  verified: boolean;
};

export type ItemVerdict = 'MATCH' | 'SIMILAR' | 'MISMATCH' | 'UNKNOWN';

/** Server-issued item identity. Never substitute a local draft id in verify URLs. */
export type MissionItemDto = {
  itemId: string;
  name: string;
  brand: string | null;
  size: string | null;
  verdict: ItemVerdict;
  detectedLabel: string | null;
};

export type MissionDraft = {
  destination: { name: string; distance: string; duration: string };
  item: MissionItem;
  shareLocation: boolean;
  notifyOffRoute: boolean;
};

export type MissionSnapshot = MissionDraft & {
  id: string;
  status: MissionStatus;
  updatedAt: string;
};

export type CreateMissionResult = {
  mission: MissionSnapshot;
  joinCode: string;
  joinCodeExpiresAt: string;
  parentToken: string;
  items: MissionItemDto[];
};

export type JoinMissionResult = {
  missionId: string;
  childToken: string;
  status: 'GOING' | 'SHOPPING' | 'RETURNING';
  instructionCode: string;
  message: string;
  items: MissionItemDto[];
};

export type ItemVerificationResult = {
  verdict: ItemVerdict;
  message: string;
  detectedLabel: string | null;
  status: 'SHOPPING' | 'RETURNING';
};
