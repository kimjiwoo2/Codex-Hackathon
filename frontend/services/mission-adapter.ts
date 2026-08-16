import type { CreateMissionResult, MissionDraft } from '@/features/mission/types';

export interface MissionAdapter {
  createMission(draft: MissionDraft): Promise<CreateMissionResult>;
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
}

// 실제 API 준비 후 이 바인딩만 HTTP adapter로 교체한다.
export const missionAdapter: MissionAdapter = new MockMissionAdapter();
