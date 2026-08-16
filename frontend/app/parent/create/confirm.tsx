import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { BottomNav } from '@/components/ican/bottom-nav';
import { PrimaryButton } from '@/components/ican/primary-button';
import { Screen } from '@/components/ican/screen';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';
import { useMissionDraft } from '@/features/mission/mission-draft-context';
import { missionAdapter } from '@/services/mission-adapter';

function Toggle({ enabled, onPress }: { enabled: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: enabled }}
      onPress={onPress}
      style={[styles.toggle, enabled && styles.toggleEnabled]}>
      <Text style={[styles.toggleText, enabled && styles.toggleTextEnabled]}>{enabled ? 'ON' : 'OFF'}</Text>
      <View style={[styles.knob, enabled && styles.knobEnabled]} />
    </Pressable>
  );
}

export default function ConfirmScreen() {
  const { draft, setResult, toggleNotifyOffRoute, toggleShareLocation } = useMissionDraft();
  const [loading, setLoading] = useState(false);

  const createMission = async () => {
    setLoading(true);
    try {
      setResult(await missionAdapter.createMission(draft));
      router.replace('/parent/code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen scroll contentStyle={styles.screen}>
      <TopBar title="심부름 작성" />
      <View style={styles.content}>
        <Image resizeMode="cover" source={require('../../../assets/ican/route-summary.png')} style={styles.map} />
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>사올 것</Text>
          <Text style={styles.summaryValue}>우유 {draft.item.quantity}개</Text>
        </View>
        <View style={[styles.summaryRow, styles.timeRow]}>
          <Text style={[styles.summaryLabel, styles.timeLabel]}>예상 시간</Text>
          <Text style={styles.summaryValue}>왕복 약 15분</Text>
          <Image resizeMode="contain" source={require('../../../assets/ican/time-mascot.png')} style={styles.timeMascot} />
        </View>
        <View style={styles.settingsCard}>
          <View style={styles.settingRow}>
            <Ionicons color={ICanColors.green} name="location" size={21} />
            <Text style={styles.settingLabel}>위치 공유</Text>
            <Toggle enabled={draft.shareLocation} onPress={toggleShareLocation} />
          </View>
          <View style={styles.divider} />
          <View style={styles.settingRow}>
            <Ionicons color={ICanColors.green} name="notifications" size={21} />
            <Text style={styles.settingLabel}>경로 이탈 알림</Text>
            <Toggle enabled={draft.notifyOffRoute} onPress={toggleNotifyOffRoute} />
          </View>
        </View>
        <PrimaryButton label="심부름 시작" loading={loading} onPress={createMission} />
      </View>
      <BottomNav active="create" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 110 },
  content: { gap: 11, paddingHorizontal: 24, paddingTop: 28 },
  map: { borderRadius: 10, height: 289, width: '100%' },
  summaryRow: { alignItems: 'center', backgroundColor: ICanColors.canvas, borderRadius: 10, flexDirection: 'row', height: 47, paddingHorizontal: 16 },
  summaryLabel: { color: ICanColors.green, fontSize: 15, fontWeight: '600', width: 80 },
  summaryValue: { color: 'rgba(20,21,23,0.6)', fontSize: 15, fontWeight: '500' },
  timeRow: { backgroundColor: '#FEF9EC', height: 50 },
  timeLabel: { color: ICanColors.warning },
  timeMascot: { height: 43, marginLeft: 'auto', width: 55 },
  settingsCard: { backgroundColor: ICanColors.canvas, borderRadius: 10, marginVertical: 7, paddingHorizontal: 15 },
  settingRow: { alignItems: 'center', flexDirection: 'row', height: 42 },
  settingLabel: { color: ICanColors.green, flex: 1, fontSize: 15, fontWeight: '600', marginLeft: 10 },
  divider: { backgroundColor: ICanColors.border, height: 1, marginLeft: 30 },
  toggle: { alignItems: 'center', borderColor: ICanColors.border, borderRadius: 12, borderWidth: 1, flexDirection: 'row', height: 23, justifyContent: 'space-between', paddingHorizontal: 5, width: 58 },
  toggleEnabled: { borderColor: 'rgba(163,183,85,0.45)' },
  toggleText: { color: ICanColors.subtle, fontSize: 11 },
  toggleTextEnabled: { color: ICanColors.green },
  knob: { backgroundColor: ICanColors.subtle, borderRadius: 8, height: 15, width: 15 },
  knobEnabled: { backgroundColor: ICanColors.green },
});
