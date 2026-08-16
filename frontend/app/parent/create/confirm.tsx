import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';

import { BottomNav } from '@/components/ican/bottom-nav';
import { PrimaryButton } from '@/components/ican/primary-button';
import { Screen } from '@/components/ican/screen';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';
import { getJoinCodeErrorMessage } from '@/features/mission/presentation';
import { useMissionDraft } from '@/features/mission/mission-draft-context';
import { MissionAdapterError, missionAdapter } from '@/services/mission-adapter';

export default function ConfirmScreen() {
  const { draft, setCreateResult } = useMissionDraft();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createMission = async () => {
    setLoading(true);
    try {
      setErrorMessage(null);
      setCreateResult(await missionAdapter.createMission(draft));
      router.replace('/parent/code');
    } catch (error) {
      const message = error instanceof MissionAdapterError ? getJoinCodeErrorMessage(error.code) : '심부름을 만들지 못했어요.';
      setErrorMessage(message);
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
          <Ionicons color={ICanColors.green} name="information-circle" size={21} />
          <Text style={styles.settingLabel}>위치 공유와 경로 이탈 알림은 현재 모든 미션에 적용됩니다.</Text>
        </View>
        {errorMessage ? <Text style={styles.errorMessage}>{errorMessage}</Text> : null}
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
  settingsCard: { alignItems: 'center', backgroundColor: ICanColors.canvas, borderRadius: 10, flexDirection: 'row', marginVertical: 7, minHeight: 54, paddingHorizontal: 15 },
  settingLabel: { color: ICanColors.green, flex: 1, fontSize: 14, fontWeight: '600', marginLeft: 10 },
  errorMessage: { color: '#C15C50', fontSize: 13, fontWeight: '600', lineHeight: 19, paddingHorizontal: 4 },
});
