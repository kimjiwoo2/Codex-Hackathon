import { Ionicons } from '@expo/vector-icons';
import { Image, StyleSheet, Text, View } from 'react-native';

import { BottomNav } from '@/components/ican/bottom-nav';
import { Screen } from '@/components/ican/screen';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';

const timeline = [
  { time: '09:40', label: '출발', done: true },
  { time: '09:42', label: '횡단보도 도착', done: true },
  { time: '09:47', label: '마트 도착 예정', done: false },
];

export default function MonitorScreen() {
  return (
    <Screen scroll contentStyle={styles.screen}>
      <TopBar title="이준이의 심부름" />
      <View style={styles.content}>
        <Image resizeMode="cover" source={require('../../assets/ican/route-monitor.png')} style={styles.map} />
        <View style={styles.locationCard}>
          <Ionicons color={ICanColors.greenDark} name="location" size={48} />
          <View style={styles.locationCopy}>
            <Text style={styles.locationTitle}>석현 초등학교 앞</Text>
            <Text style={styles.locationMeta}>
              마트까지 <Text style={styles.distance}>180m</Text>
            </Text>
          </View>
        </View>
        <View style={styles.progressCard}>
          <Text style={styles.cardTitle}>현재 단계</Text>
          <View style={styles.progressTrack}>
            <View style={styles.progressFill} />
            <View style={styles.progressKnob} />
          </View>
          <Text style={styles.progressLabel}>이동 중</Text>
          <View style={styles.divider} />
          {timeline.map((entry, index) => (
            <View key={entry.label} style={styles.timelineRow}>
              <View style={[styles.timelineDot, entry.done && styles.timelineDotDone]}>
                {entry.done && <Ionicons color={ICanColors.paper} name="checkmark" size={13} />}
              </View>
              {index < timeline.length - 1 && <View style={styles.timelineLine} />}
              <Text style={[styles.time, !entry.done && styles.timePending]}>{entry.time}</Text>
              <Text style={styles.timelineLabel}>{entry.label}</Text>
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
  progressFill: { backgroundColor: '#76A052', borderRadius: 4, height: 7, width: '54%' },
  progressKnob: { backgroundColor: '#76A052', borderRadius: 9, height: 18, left: '51%', position: 'absolute', top: -6, width: 18 },
  progressLabel: { color: '#76A052', fontSize: 14, marginTop: 8 },
  divider: { backgroundColor: ICanColors.border, height: 1, marginVertical: 11 },
  timelineRow: { alignItems: 'center', flexDirection: 'row', height: 33, position: 'relative' },
  timelineDot: { alignItems: 'center', borderColor: '#76A052', borderRadius: 10, borderWidth: 2, height: 20, justifyContent: 'center', width: 20 },
  timelineDotDone: { backgroundColor: '#76A052' },
  timelineLine: { backgroundColor: '#76A052', height: 20, left: 9, position: 'absolute', top: 23, width: 2 },
  time: { color: '#76A052', fontSize: 14, marginLeft: 12, width: 66 },
  timePending: { color: '#838383' },
  timelineLabel: { color: '#030303', fontSize: 14 },
});
