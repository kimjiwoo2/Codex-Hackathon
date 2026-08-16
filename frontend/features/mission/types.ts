export type MissionStatus = 'WAITING' | 'GOING' | 'SHOPPING' | 'RETURNING' | 'COMPLETED' | 'CANCELED';

export type MissionItem = {
  id: string;
  name: string;
  brand: string | null;
  quantity: number;
  unit: string;
  verified: boolean;
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
};
