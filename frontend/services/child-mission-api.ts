import { Platform } from 'react-native';

import { isRoadVisionResult, type RoadVisionResult } from '@/features/road-vision/safety';

const apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.replace(/\/$/, '');

export interface ChildMissionSession { missionId: string; childToken: string; status: 'GOING'; message: string; }
export interface CapturedRoadFrame { uri: string; base64: string; capturedAt: string; }

export class ChildApiError extends Error {
  constructor(readonly status: number | undefined, message: string) { super(message); this.name = 'ChildApiError'; }
}

function endpoint(path: string): string {
  if (!apiBaseUrl) throw new ChildApiError(undefined, 'API 주소가 설정되지 않았습니다.');
  return `${apiBaseUrl}${path}`;
}

async function errorFromResponse(response: Response): Promise<ChildApiError> {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    return new ChildApiError(response.status, body.error?.message ?? '요청을 처리하지 못했습니다.');
  } catch { return new ChildApiError(response.status, '요청을 처리하지 못했습니다.'); }
}

function webJpegBlob(base64: string): Blob {
  const binary = atob(base64.includes(',') ? base64.slice(base64.indexOf(',') + 1) : base64);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new Blob([bytes], { type: 'image/jpeg' });
}

export async function joinMission(joinCode: string): Promise<ChildMissionSession> {
  const response = await fetch(endpoint('/missions/join'), { body: JSON.stringify({ joinCode }), headers: { 'Content-Type': 'application/json' }, method: 'POST' });
  if (!response.ok) throw await errorFromResponse(response);
  return (await response.json()) as ChildMissionSession;
}

export async function uploadRoadFrame(session: Pick<ChildMissionSession, 'missionId' | 'childToken'>, frame: CapturedRoadFrame): Promise<RoadVisionResult> {
  const form = new FormData();
  form.append('capturedAt', frame.capturedAt);
  const image = Platform.OS === 'web'
    ? webJpegBlob(frame.base64)
    : ({ name: 'road-frame.jpg', type: 'image/jpeg', uri: frame.uri } as unknown as Blob);
  form.append('image', image, 'road-frame.jpg');
  const response = await fetch(endpoint(`/missions/${session.missionId}/vision/road`), { body: form, headers: { Authorization: `Bearer ${session.childToken}` }, method: 'POST' });
  if (!response.ok) throw await errorFromResponse(response);
  const body = (await response.json()) as { result?: unknown };
  if (!isRoadVisionResult(body.result)) throw new ChildApiError(response.status, '안전 판단 형식이 올바르지 않습니다.');
  return body.result;
}
