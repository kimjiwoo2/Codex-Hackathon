import { Ionicons } from '@expo/vector-icons';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { BottomNav } from '@/components/ican/bottom-nav';
import { Screen } from '@/components/ican/screen';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';
import { getEventLabel, getMissionStatusPresentation } from '@/features/mission/parent-monitor-presentation';
import { useMissionDraft } from '@/features/mission/mission-draft-context';
import { useParentSnapshot } from '@/hooks/use-parent-snapshot';

export default function MonitorScreen() {
  const { createResult } = useMissionDraft();
  const { error, events, loading, refresh, snapshot } = useParentSnapshot(
    createResult?.missionId,
    createResult?.parentToken,
  );
  const location = snapshot?.location;
  const distance = snapshot ? `${Math.round(snapshot.remainingDistanceM)}m` : '-';
  const status = getMissionStatusPresentation(snapshot?.status ?? 'WAITING');
  const displayedEvents = events.slice(-3);
  const progressWidth = `${status.progress}%` as `${number}%`;
  const knobLeft = `${Math.min(status.progress, 96)}%` as `${number}%`;

  return (
    <Screen scroll contentStyle={styles.screen}>
      <TopBar title="이준이의 심부름" />
      <View style={styles.content}>
        <Image resizeMode="cover" source={require('../../assets/ican/route-monitor.png')} style={styles.map} />
        <View style={styles.locationCard}>
          <Ionicons color={ICanColors.greenDark} name="location" size={48} />
          <View style={styles.locationCopy}>
            <Text style={styles.locationTitle}>
              {location ? `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}` : '아이 위치를 기다리는 중'}
            </Text>
            <Text style={styles.locationMeta}>
              남은 거리 <Text style={styles.distance}>{distance}</Text>
            </Text>
          </View>
        </View>
        {snapshot?.locationStale && <Text style={styles.warning}>마지막 위치가 오래되었습니다. 아이에게 직접 확인해 주세요.</Text>}
        {error && (
          <Pressable accessibilityRole="button" onPress={() => void refresh()} style={styles.errorCard}>
            <Text style={styles.errorText}>{error} 다시 시도</Text>
          </Pressable>
        )}
        <View style={styles.progressCard}>
          <Text style={styles.cardTitle}>현재 단계</Text>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: progressWidth }]} />
            <View style={[styles.progressKnob, { left: knobLeft }]} />
          </View>
          <Text style={styles.progressLabel}>{loading && !snapshot ? '미션 상태 불러오는 중' : status.label}</Text>
          <Text style={styles.statusMessage}>{status.message}</Text>
          <View style={styles.divider} />
          {displayedEvents.length === 0 && <Text style={styles.emptyEvents}>상태가 바뀌면 여기에 알림이 표시돼요.</Text>}
          {displayedEvents.map((entry, index) => (
            <View key={entry.eventId} style={styles.timelineRow}>
              <View style={[styles.timelineDot, styles.timelineDotDone]}>
                <Ionicons color={ICanColors.paper} name="checkmark" size={13} />
              </View>
              {index < displayedEvents.length - 1 && <View style={styles.timelineLine} />}
              <Text style={styles.time}>{new Date(entry.createdAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</Text>
              <Text style={styles.timelineLabel}>{getEventLabel(entry.eventType)}</Text>
            </View>
          ))}
        </View>
      </View>
      <BottomNav active="monitor" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 110 },
  content: { gap: 16, paddingHorizontal: 24, paddingTop: 28 },
  map: { borderRadius: 10, height: 289, width: '100%' },
  locationCard: {
    alignItems: 'center',
    backgroundColor: ICanColors.paper,
    borderRadius: 10,
    elevation: 3,
    flexDirection: 'row',
    height: 91,
    paddingHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
  },
  locationCopy: { marginLeft: 13 },
  locationTitle: { color: ICanColors.ink, fontSize: 18, fontWeight: '600' },
  locationMeta: { color: ICanColors.muted, fontSize: 16, marginTop: 5 },
  distance: { color: ICanColors.greenDark, fontWeight: '700' },
  warning: { color: '#A64A00', fontSize: 14, lineHeight: 20 },
  errorCard: { backgroundColor: '#FFF0E6', borderRadius: 10, padding: 14 },
  errorText: { color: '#A64A00', fontSize: 14, lineHeight: 20 },
  progressCard: {
    backgroundColor: ICanColors.paper,
    borderRadius: 10,
    elevation: 3,
    minHeight: 204,
    padding: 17,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
  },
  cardTitle: { color: ICanColors.ink, fontSize: 15, fontWeight: '600' },
  progressTrack: { backgroundColor: '#EFEFEE', borderRadius: 4, height: 7, marginTop: 10, overflow: 'visible' },
  progressFill: { backgroundColor: '#76A052', borderRadius: 4, height: 7 },
  progressKnob: { backgroundColor: '#76A052', borderRadius: 9, height: 18, position: 'absolute', top: -6, width: 18 },
  progressLabel: { color: '#76A052', fontSize: 14, marginTop: 8 },
  statusMessage: { color: ICanColors.ink, fontSize: 14, fontWeight: '600', lineHeight: 20, marginTop: 5 },
  emptyEvents: { color: ICanColors.muted, fontSize: 14, paddingVertical: 8 },
  divider: { backgroundColor: ICanColors.border, height: 1, marginVertical: 11 },
  timelineRow: { alignItems: 'center', flexDirection: 'row', height: 33, position: 'relative' },
  timelineDot: { alignItems: 'center', borderColor: '#76A052', borderRadius: 10, borderWidth: 2, height: 20, justifyContent: 'center', width: 20 },
  timelineDotDone: { backgroundColor: '#76A052' },
  timelineLine: { backgroundColor: '#76A052', height: 20, left: 9, position: 'absolute', top: 23, width: 2 },
  time: { color: '#76A052', fontSize: 14, marginLeft: 12, width: 66 },
  timelineLabel: { color: '#030303', fontSize: 14 },
});
