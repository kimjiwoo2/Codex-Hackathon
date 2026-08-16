import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';
import type { ChildLocationStatus as LocationStatus } from '@/features/child/use-child-location';

const statusCopy: Record<LocationStatus, { icon: keyof typeof Ionicons.glyphMap; label: string }> = {
  CHECKING: { icon: 'locate', label: '위치 확인 중' },
  TRACKING: { icon: 'location', label: 'GPS 연결됨' },
  DENIED: { icon: 'location-outline', label: '위치 권한 필요' },
  UNAVAILABLE: { icon: 'navigate-outline', label: 'GPS를 켜 주세요' },
  ERROR: { icon: 'refresh', label: '다시 연결하기' },
};

export function ChildLocationStatus({ status, onRetry }: { status: LocationStatus; onRetry: () => void }) {
  const copy = statusCopy[status];
  const canRetry = status === 'DENIED' || status === 'UNAVAILABLE' || status === 'ERROR';

  return (
    <Pressable
      accessibilityHint={canRetry ? '위치 연결을 다시 시도합니다' : undefined}
      accessibilityRole={canRetry ? 'button' : undefined}
      disabled={!canRetry}
      onPress={onRetry}
      style={[styles.container, status === 'TRACKING' && styles.connected, canRetry && styles.retry]}>
      <Ionicons color={status === 'TRACKING' ? ICanColors.greenDark : '#8A6A18'} name={copy.icon} size={16} />
      <Text style={[styles.label, status === 'TRACKING' && styles.connectedLabel]}>{copy.label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    backgroundColor: '#FFF6DE',
    borderRadius: 16,
    flexDirection: 'row',
    paddingHorizontal: 11,
    paddingVertical: 7,
    position: 'absolute',
    right: 17,
    top: 11,
    zIndex: 1,
  },
  connected: { backgroundColor: ICanColors.paleGreen },
  retry: { borderColor: '#F0C65C', borderWidth: 1 },
  label: { color: '#8A6A18', fontSize: 12, fontWeight: '700', marginLeft: 5 },
  connectedLabel: { color: ICanColors.greenDark },
});
