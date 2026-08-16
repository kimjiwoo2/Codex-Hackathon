export const ROAD_VISION_RESULTS = ['STOP', 'CAUTION', 'UNKNOWN'] as const;

export type RoadVisionResult = (typeof ROAD_VISION_RESULTS)[number];
export type RoadVisionFailure = 'busy' | 'invalid-frame' | 'network' | 'unknown';

export interface RoadSafetyGuidance {
  result: RoadVisionResult;
  title: string;
  message: string;
}

// This is deliberately independent from server/model-authored messages. Road vision can
// warn, but it must never authorize crossing or imply that a road is safe to cross.
const guidanceByResult: Record<RoadVisionResult, RoadSafetyGuidance> = {
  STOP: { result: 'STOP', title: '멈춰서 확인해요', message: '멈춰서 주변을 살피고 보호자와 함께 확인하세요.' },
  CAUTION: { result: 'CAUTION', title: '주변을 살펴요', message: '주변을 살피고 보호자와 함께 확인하세요.' },
  UNKNOWN: { result: 'UNKNOWN', title: '직접 확인이 필요해요', message: '길을 멈추고 보호자와 함께 직접 확인하세요.' },
};

const guidanceByFailure: Record<RoadVisionFailure, RoadSafetyGuidance> = {
  busy: { result: 'UNKNOWN', title: '판단을 다시 확인하고 있어요', message: '잠시 멈추고 주변을 살피세요. 보호자와 함께 직접 확인하세요.' },
  'invalid-frame': { result: 'UNKNOWN', title: '카메라 화면을 다시 비춰주세요', message: '그동안 멈춰서 주변을 살피고 보호자와 함께 직접 확인하세요.' },
  network: { result: 'UNKNOWN', title: '연결을 확인할 수 없어요', message: '멈춰서 주변을 살피고 보호자와 함께 직접 확인하세요.' },
  unknown: guidanceByResult.UNKNOWN,
};

export function isRoadVisionResult(value: unknown): value is RoadVisionResult {
  return typeof value === 'string' && (ROAD_VISION_RESULTS as readonly string[]).includes(value);
}

export function roadSafetyGuidance(result: RoadVisionResult): RoadSafetyGuidance {
  return guidanceByResult[result];
}

export function roadSafetyFailureGuidance(failure: RoadVisionFailure): RoadSafetyGuidance {
  return guidanceByFailure[failure];
}

export function roadFailureFromStatus(status: number | undefined): RoadVisionFailure {
  if (status === 409) return 'busy';
  if (status === 422) return 'invalid-frame';
  if (status === undefined) return 'network';
  return 'unknown';
}

export function jpegByteLength(base64: string): number {
  const payload = base64.includes(',') ? base64.slice(base64.indexOf(',') + 1) : base64;
  const padding = payload.endsWith('==') ? 2 : payload.endsWith('=') ? 1 : 0;
  return Math.floor((payload.length * 3) / 4) - padding;
}
