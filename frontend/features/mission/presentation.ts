import type { MissionAdapterErrorCode } from '@/services/mission-adapter';

const expiryFormatter = new Intl.DateTimeFormat('ko-KR', {
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

export function formatJoinCodeExpiry(value: string): string {
  const expiry = new Date(value);
  if (Number.isNaN(expiry.getTime())) {
    return '만료 시각을 확인할 수 없어요.';
  }

  if (expiry.getTime() <= Date.now()) {
    return '이 코드는 이미 만료되었어요.';
  }

  return `${expiryFormatter.format(expiry)}까지 사용할 수 있어요.`;
}

export function getJoinCodeErrorMessage(code: MissionAdapterErrorCode): string {
  switch (code) {
    case 'JOIN_CODE_INVALID':
      return '참여 코드를 다시 확인해 주세요.';
    case 'JOIN_CODE_EXPIRED':
      return '이 코드는 만료되었어요. 부모가 새 코드를 만들어야 해요.';
    case 'JOIN_CODE_ALREADY_USED':
      return '이미 연결된 코드예요. 다른 코드를 입력해 주세요.';
    case 'MISSION_API_CONFIG_MISSING':
      return '앱에서 백엔드 주소를 찾지 못했어요.';
    case 'MISSION_API_RESPONSE_INVALID':
      return '서버 응답을 해석하지 못했어요. 잠시 후 다시 시도해 주세요.';
    case 'MISSION_API_REQUEST_FAILED':
    default:
      return '서버와 연결하지 못했어요. 잠시 후 다시 시도해 주세요.';
  }
}
