import type {
  CreateMissionResult,
  ItemVerificationResult,
  JoinMissionResult,
  MissionDraft,
} from '@/features/mission/types';

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
      items: [{ itemId: 'mock-server-item-uuid', name: draft.item.name, brand: draft.item.brand, size: null, verdict: 'UNKNOWN', detectedLabel: null }],
    };
  }
}

// 실제 API 준비 후 이 바인딩만 HTTP adapter로 교체한다.
export const missionAdapter: MissionAdapter = new MockMissionAdapter();

const apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.replace(/\/$/, '');

function apiUrl(path: string) {
  if (!apiBaseUrl) throw new Error('EXPO_PUBLIC_API_BASE_URL 설정이 필요합니다.');
  return `${apiBaseUrl}${path}`;
}

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) throw new Error(payload?.error?.message ?? '서버 요청에 실패했어요.');
  return payload as T;
}

/** Child-only API boundary: opaque child token is sent only as a bearer credential. */
export const childMissionApi = {
  async join(joinCode: string): Promise<JoinMissionResult> {
    const response = await fetch(apiUrl('/missions/join'), {
      body: JSON.stringify({ joinCode }),
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
    });
    return readJson<JoinMissionResult>(response);
  },

  async verifyItem(
    missionId: string,
    itemId: string,
    childToken: string,
    imageUri: string,
  ): Promise<ItemVerificationResult> {
    const form = new FormData();
    form.append('image', { uri: imageUri, name: 'item.jpg', type: 'image/jpeg' } as never);
    const response = await fetch(apiUrl(`/missions/${missionId}/items/${itemId}/verify`), {
      body: form,
      headers: { Authorization: `Bearer ${childToken}` },
      method: 'POST',
    });
    return readJson<ItemVerificationResult>(response);
  },
};
