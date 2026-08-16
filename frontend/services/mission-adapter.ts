import type { CreateMissionResult, JoinMissionResult, MissionDraft } from '@/features/mission/types';
import type { ChildInstructionCode } from '@/features/child/location-guidance';
import { isRoadVisionResult, type RoadVisionResult } from '@/features/road-vision/safety';
import { Platform } from 'react-native';

type ErrorEnvelope = {
  error?: {
    code?: unknown;
    message?: unknown;
  };
};

export type MissionAdapterErrorCode =
  | 'JOIN_CODE_INVALID'
  | 'JOIN_CODE_EXPIRED'
  | 'JOIN_CODE_ALREADY_USED'
  | 'INVALID_ITEM_IMAGE'
  | 'MISSION_API_CONFIG_MISSING'
  | 'MISSION_API_RESPONSE_INVALID'
  | 'MISSION_API_REQUEST_FAILED';

export class MissionAdapterError extends Error {
  constructor(
    readonly code: MissionAdapterErrorCode,
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'MissionAdapterError';
  }
}

export interface MissionAdapter {
  createMission(draft: MissionDraft): Promise<CreateMissionResult>;
  joinMission(joinCode: string): Promise<JoinMissionResult>;
}

export interface ChildLocationUpdate {
  latitude: number;
  longitude: number;
  accuracyM: number;
  headingDeg?: number;
  speedMps?: number;
  observedAt: string;
}

export interface ChildLocationUpdateResult {
  status: JoinMissionResult['status'];
  instructionCode: ChildInstructionCode;
  message: string;
  vibrationHint: string;
  remainingDistanceM: number;
  offRoute: boolean;
  wrongWay: boolean;
}

export interface CapturedRoadFrame {
  uri: string;
  base64: string;
  capturedAt: string;
}

const apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000';

class HttpMissionAdapter implements MissionAdapter {
  async createMission(draft: MissionDraft): Promise<CreateMissionResult> {
    const payload = await requestJson('/missions', {
      method: 'POST',
      body: JSON.stringify({
        home: draft.home,
        store: draft.store,
        items: [
          {
            name: draft.item.name,
            brand: draft.item.brand,
            size: draft.item.size,
          },
        ],
      }),
    });

    return {
      missionId: readString(payload, ['missionId', 'mission_id']),
      joinCode: readJoinCode(payload, ['joinCode', 'join_code']),
      joinCodeExpiresAt: readIsoTimestamp(payload, ['joinCodeExpiresAt', 'join_code_expires_at']),
      parentToken: readString(payload, ['parentToken', 'parent_token']),
      items: readItems(payload),
    };
  }

  async joinMission(joinCode: string): Promise<JoinMissionResult> {
    const payload = await requestJson('/missions/join', {
      method: 'POST',
      body: JSON.stringify({
        joinCode,
      }),
    });

    return {
      ...payload,
      missionId: readString(payload, ['missionId', 'mission_id']),
      childToken: readString(payload, ['childToken', 'child_token']),
      status: readString(payload, ['status']) as JoinMissionResult['status'],
      instructionCode: readString(payload, ['instructionCode', 'instruction_code']) as ChildInstructionCode,
      message: readString(payload, ['message']),
      items: readItems(payload),
    };
  }
}

async function requestJson(path: string, init: RequestInit): Promise<Record<string, unknown>> {
  if (!apiBaseUrl) {
    throw new MissionAdapterError(
      'MISSION_API_CONFIG_MISSING',
      '백엔드 주소가 설정되지 않았습니다. EXPO_PUBLIC_API_BASE_URL을 확인해 주세요.',
    );
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new MissionAdapterError(
      'MISSION_API_REQUEST_FAILED',
      '서버에 연결하지 못했어요. 네트워크와 백엔드 주소를 확인해 주세요.',
    );
  }

  const body = await readResponseBody(response);
  const payload = isRecord(body) ? body : {};
  if (!response.ok) {
    const error = readErrorEnvelope(payload);
    if (error) {
      throw new MissionAdapterError(error.code, error.message, response.status);
    }
    throw new MissionAdapterError(
      'MISSION_API_REQUEST_FAILED',
      '요청 처리 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.',
      response.status,
    );
  }

  if (!isRecord(body)) {
    throw new MissionAdapterError(
      'MISSION_API_RESPONSE_INVALID',
      '서버 응답 형식을 해석하지 못했어요. 앱을 다시 열고 시도해 주세요.',
      response.status,
    );
  }

  return payload;
}

async function readResponseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return {};
  }
}

function readErrorEnvelope(
  payload: Record<string, unknown>,
): { code: MissionAdapterErrorCode; message: string } | null {
  const envelope = payload as ErrorEnvelope;
  if (!envelope.error || typeof envelope.error.code !== 'string' || typeof envelope.error.message !== 'string') {
    return null;
  }

  const knownCodes: MissionAdapterErrorCode[] = [
    'JOIN_CODE_INVALID',
    'JOIN_CODE_EXPIRED',
    'JOIN_CODE_ALREADY_USED',
    'INVALID_ITEM_IMAGE',
    'MISSION_API_CONFIG_MISSING',
    'MISSION_API_RESPONSE_INVALID',
    'MISSION_API_REQUEST_FAILED',
  ];

  const code = knownCodes.includes(envelope.error.code as MissionAdapterErrorCode)
    ? (envelope.error.code as MissionAdapterErrorCode)
    : 'MISSION_API_REQUEST_FAILED';

  return { code, message: envelope.error.message };
}

function readString(payload: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === 'string' && value.length > 0) {
      return value;
    }
  }

  throw new MissionAdapterError(
    'MISSION_API_RESPONSE_INVALID',
    `서버 응답에 ${keys[0]} 값이 없습니다.`,
  );
}

function readJoinCode(payload: Record<string, unknown>, keys: string[]): string {
  const value = readString(payload, keys);
  if (/^\d{6}$/.test(value)) {
    return value;
  }

  throw new MissionAdapterError(
    'MISSION_API_RESPONSE_INVALID',
    '서버 응답의 참여 코드 형식이 올바르지 않습니다.',
  );
}

function readIsoTimestamp(payload: Record<string, unknown>, keys: string[]): string {
  const value = readString(payload, keys);
  if (!Number.isNaN(Date.parse(value))) {
    return value;
  }

  throw new MissionAdapterError(
    'MISSION_API_RESPONSE_INVALID',
    '서버 응답의 만료 시각 형식이 올바르지 않습니다.',
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export const missionAdapter: MissionAdapter = new HttpMissionAdapter();

function readItems(payload: Record<string, unknown>) {
  if (!Array.isArray(payload.items)) throw new MissionAdapterError('MISSION_API_RESPONSE_INVALID', '서버 응답에 상품 목록이 없습니다.');
  return payload.items as CreateMissionResult['items'];
}

export const childMissionApi = {
  join: (joinCode: string) => missionAdapter.joinMission(joinCode),
  async updateLocation(missionId: string, childToken: string, location: ChildLocationUpdate) {
    const payload = await requestJson(`/missions/${missionId}/locations`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${childToken}` },
      body: JSON.stringify(location),
    });
    return {
      status: readString(payload, ['status']) as ChildLocationUpdateResult['status'],
      instructionCode: readString(payload, ['instructionCode', 'instruction_code']) as ChildInstructionCode,
      message: readString(payload, ['message']),
      vibrationHint: readString(payload, ['vibrationHint', 'vibration_hint']),
      remainingDistanceM: readNumber(payload, ['remainingDistanceM', 'remaining_distance_m']),
      offRoute: readBoolean(payload, ['offRoute', 'off_route']),
      wrongWay: readBoolean(payload, ['wrongWay', 'wrong_way']),
    } satisfies ChildLocationUpdateResult;
  },
  async uploadRoadFrame(
    missionId: string,
    childToken: string,
    frame: CapturedRoadFrame,
  ) {
    const form = new FormData();
    form.append('capturedAt', frame.capturedAt);
    appendJpegImage(form, 'image', await buildRoadImageFormPart(frame), 'road-frame.jpg');
    let response: Response;
    try {
      response = await fetch(`${apiBaseUrl}/missions/${missionId}/vision/road`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${childToken}` },
        body: form,
      });
    } catch {
      throw new MissionAdapterError('MISSION_API_REQUEST_FAILED', '서버에 연결하지 못했어요. 네트워크를 확인해 주세요.');
    }
    const body = await readResponseBody(response);
    const payload = isRecord(body) ? body : {};
    if (!response.ok) {
      throw new MissionAdapterError(
        'MISSION_API_REQUEST_FAILED',
        (payload as ErrorEnvelope).error?.message as string || '도로 안전 확인에 실패했어요.',
        response.status,
      );
    }
    const result = payload.result;
    if (!isRoadVisionResult(result)) {
      throw new MissionAdapterError('MISSION_API_RESPONSE_INVALID', '안전 판단 형식이 올바르지 않습니다.', response.status);
    }
    return result as RoadVisionResult;
  },
  async verifyItem(missionId: string, itemId: string, childToken: string, imageUri: string) {
    await assertLocalImageSize(imageUri);
    const form = new FormData();
    appendJpegImage(form, 'image', await buildItemImageFormPart(imageUri), 'item.jpg');
    let response: Response;
    try { response = await fetch(`${apiBaseUrl}/missions/${missionId}/items/${itemId}/verify`, { method: 'POST', headers: { Authorization: `Bearer ${childToken}` }, body: form }); }
    catch { throw new MissionAdapterError('MISSION_API_REQUEST_FAILED', '서버에 연결하지 못했어요. 네트워크를 확인해 주세요.'); }
    const body = await readResponseBody(response);
    const payload = isRecord(body) ? body : {};
    if (!response.ok) {
      const errorMessage = (payload as ErrorEnvelope).error?.message as string | undefined;
      const code = response.status === 422 ? 'INVALID_ITEM_IMAGE' : 'MISSION_API_REQUEST_FAILED';
      throw new MissionAdapterError(code, errorMessage || '상품 확인에 실패했어요.', response.status);
    }
    return payload as import('@/features/mission/types').ItemVerificationResult;
  },
};

function readNumber(payload: Record<string, unknown>, keys: string[]): number {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
  }
  throw new MissionAdapterError('MISSION_API_RESPONSE_INVALID', `서버 응답에 ${keys[0]} 값이 없습니다.`);
}

function readBoolean(payload: Record<string, unknown>, keys: string[]): boolean {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === 'boolean') {
      return value;
    }
  }
  throw new MissionAdapterError('MISSION_API_RESPONSE_INVALID', `서버 응답에 ${keys[0]} 값이 없습니다.`);
}

async function buildRoadImageFormPart(frame: CapturedRoadFrame) {
  if (Platform.OS === 'web') {
    return jpegBlobFromBase64(frame.base64);
  }
  return { uri: frame.uri, name: 'road-frame.jpg', type: 'image/jpeg' } as never;
}

async function buildItemImageFormPart(uri: string) {
  if (Platform.OS === 'web') {
    return await readBlobFromUri(uri);
  }
  return { uri, name: 'item.jpg', type: 'image/jpeg' } as never;
}

async function assertLocalImageSize(uri: string) {
  const blob = await readBlobFromUri(uri);
  if (blob.size > 1_000_000) {
    throw new MissionAdapterError('INVALID_ITEM_IMAGE', '사진은 1MB 이하로 다시 찍어 주세요.');
  }
}

function appendJpegImage(form: FormData, field: string, value: Blob | never, name: string) {
  if (Platform.OS === 'web') {
    form.append(field, value, name);
    return;
  }
  form.append(field, value);
}

async function readBlobFromUri(uri: string) {
  const response = await fetch(uri);
  return response.blob();
}

function jpegBlobFromBase64(base64: string): Blob {
  const binary = atob(base64.includes(',') ? base64.slice(base64.indexOf(',') + 1) : base64);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new Blob([bytes], { type: 'image/jpeg' });
}
