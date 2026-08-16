import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { PrimaryButton } from '@/components/ican/primary-button';
import { Screen } from '@/components/ican/screen';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';
import { formatJoinCodeExpiry } from '@/features/mission/presentation';
import { useMissionDraft } from '@/features/mission/mission-draft-context';

export default function JoinCodeScreen() {
  const { createResult } = useMissionDraft();

  if (!createResult) {
    return (
      <Screen bottomInset={false}>
        <TopBar title="참여 코드" />
        <View style={styles.emptyContent}>
          <Text style={styles.title}>아직 만든 심부름이 없어요</Text>
          <Text style={styles.description}>심부름을 만든 뒤에 아이에게 전달할 참여 코드를 볼 수 있어요.</Text>
          <View style={styles.buttonWrap}>
            <PrimaryButton label="심부름 만들기" onPress={() => router.replace('/parent/create/destination')} />
          </View>
        </View>
      </Screen>
    );
  }

  return (
    <Screen bottomInset={false}>
      <TopBar title="참여 코드" />
      <View style={styles.content}>
        <View style={styles.iconWrap}>
          <Ionicons color={ICanColors.greenDark} name="people" size={44} />
        </View>
        <Text style={styles.title}>아이에게 코드를 알려주세요</Text>
        <Text style={styles.description}>아이 앱에서 아래 6자리 코드를 입력하면{`\n`}같은 심부름에 연결돼요.</Text>
        <View style={styles.codeCard}>
          {createResult.joinCode.split('').map((digit, index) => (
            <View key={`${digit}-${index}`} style={styles.codeCell}>
              <Text style={styles.codeDigit}>{digit}</Text>
            </View>
          ))}
        </View>
        <Text style={styles.expiry}>{formatJoinCodeExpiry(createResult.joinCodeExpiresAt)}</Text>
        <View style={styles.buttonWrap}>
          <PrimaryButton label="아이 위치 확인하기" onPress={() => router.replace('/parent/monitor')} />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { alignItems: 'center', flex: 1, paddingHorizontal: 24, paddingTop: 70 },
  emptyContent: { alignItems: 'center', flex: 1, paddingHorizontal: 24, paddingTop: 110 },
  iconWrap: { alignItems: 'center', backgroundColor: ICanColors.paleGreen, borderRadius: 42, height: 84, justifyContent: 'center', width: 84 },
  title: { color: ICanColors.ink, fontSize: 24, fontWeight: '700', marginTop: 24 },
  description: { color: ICanColors.muted, fontSize: 15, lineHeight: 22, marginTop: 10, textAlign: 'center' },
  codeCard: { flexDirection: 'row', gap: 7, marginTop: 42 },
  codeCell: { alignItems: 'center', backgroundColor: ICanColors.canvas, borderColor: ICanColors.border, borderRadius: 10, borderWidth: 1, height: 62, justifyContent: 'center', width: 49 },
  codeDigit: { color: ICanColors.ink, fontSize: 28, fontWeight: '700' },
  expiry: { color: ICanColors.green, fontSize: 13, lineHeight: 19, marginTop: 16, textAlign: 'center' },
  buttonWrap: { bottom: 32, left: 24, position: 'absolute', right: 24 },
});
