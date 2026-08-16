export type ParentMonitorStatus = 'WAITING' | 'GOING' | 'SHOPPING' | 'RETURNING' | 'COMPLETED' | 'CANCELED';

type StatusPresentation = {
  label: string;
  message: string;
  progress: number;
};

const statusPresentation: Record<ParentMonitorStatus, StatusPresentation> = {
  WAITING: {
    label: '출발 대기 중',
    message: '이준이가 참여 코드를 입력하면 출발해요.',
    progress: 6,
  },
  GOING: {
    label: '마트로 이동 중',
    message: '이준이가 마트로 출발했어요.',
    progress: 32,
  },
  SHOPPING: {
    label: '물건을 찾는 중',
    message: '행복 슈퍼에 도착해 물건을 찾고 있어요.',
    progress: 58,
  },
  RETURNING: {
    label: '집으로 돌아오는 중',
    message: '물건을 확인하고 집으로 돌아오고 있어요.',
    progress: 80,
  },
  COMPLETED: {
    label: '심부름 완료',
    message: '이준이가 집에 도착해 심부름을 마쳤어요.',
    progress: 100,
  },
  CANCELED: {
    label: '심부름 취소',
    message: '이번 심부름이 취소되었어요.',
    progress: 0,
  },
};

const eventLabels: Record<string, string> = {
  STATUS_CHANGED: '심부름 단계가 바뀌었어요',
  OFF_ROUTE: '예정된 길에서 벗어났어요',
  WRONG_WAY: '반대 방향으로 이동하고 있어요',
  ARRIVED_STORE: '행복 슈퍼에 도착했어요',
  ROAD_HAZARD: '주변 위험을 확인하고 있어요',
  VISION_UNAVAILABLE: '카메라 안내를 잠시 사용할 수 없어요',
  ITEM_VERIFIED: '심부름 물건을 확인했어요',
  RETURNING: '집으로 출발했어요',
  COMPLETED: '심부름을 완료했어요',
  LOCATION_STALE: '아이 위치가 잠시 멈춰 있어요',
};

export function getMissionStatusPresentation(status: ParentMonitorStatus): StatusPresentation {
  return statusPresentation[status];
}

export function getEventLabel(eventType: string): string {
  return eventLabels[eventType] ?? '새로운 진행 알림';
}
