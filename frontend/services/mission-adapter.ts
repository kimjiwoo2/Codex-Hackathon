import type { CreateMissionResult, JoinMissionResult, MissionDraft } from '@/features/mission/types';

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
      instructionCode: readString(payload, ['instructionCode', 'instruction_code']),
      message: readString(payload, ['message']),
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
