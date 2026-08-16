import type { CreateMissionResult, JoinMissionResult, MissionDraft } from '@/features/mission/types';

export interface MissionAdapter {
  createMission(draft: MissionDraft): Promise<CreateMissionResult>;
  joinMission(joinCode: string): Promise<JoinMissionResult>;
}

class MockMissionAdapter implements MissionAdapter {
  async createMission(draft: MissionDraft): Promise<CreateMissionResult> {
    await new Promise((resolve) => setTimeout(resolve, 450));
    return {
      mission: { ...draft, id: 'demo-mission-ican', status: 'WAITING', updatedAt: new Date().toISOString() },
      joinCode: '482913',
      joinCodeExpiresAt: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
      parentToken: 'mock-parent-token',
    };
  }

  async joinMission(joinCode: string): Promise<JoinMissionResult> {
    await new Promise((resolve) => setTimeout(resolve, 450));
    if (joinCode !== '482913') throw new Error('INVALID_JOIN_CODE');

    return {
      mission: {
        destination: { name: '행복 슈퍼', distance: '300m', duration: '5분' },
        id: 'demo-mission-ican',
        item: { brand: '서울 우유', id: 'demo-milk', name: '우유', quantity: 1, unit: '개', verified: false },
        notifyOffRoute: true,
        shareLocation: true,
        status: 'WAITING',
        updatedAt: new Date().toISOString(),
      },
      childToken: 'mock-child-token',
    };
  }
}

// 실제 API 준비 후 이 바인딩만 HTTP adapter로 교체한다.
export const missionAdapter: MissionAdapter = new MockMissionAdapter();
