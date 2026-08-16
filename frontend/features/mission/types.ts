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
};

export interface JoinMissionResult extends Record<string, unknown> {
  missionId: string;
  childToken: string;
  status: MissionStatus;
  instructionCode: string;
  message: string;
}
