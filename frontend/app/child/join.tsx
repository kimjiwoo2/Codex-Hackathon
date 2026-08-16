import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from 'react-native';

import { PrimaryButton } from '@/components/ican/primary-button';
import { Screen } from '@/components/ican/screen';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';
import { useChildJourney } from '@/features/child/child-journey-context';
import { useChildMission } from '@/features/mission/child-mission-context';
import { getJoinCodeErrorMessage } from '@/features/mission/presentation';
import { useMissionDraft } from '@/features/mission/mission-draft-context';
import { MissionAdapterError, missionAdapter } from '@/services/mission-adapter';

export default function ChildJoinScreen() {
  const [joinCode, setJoinCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { reset } = useChildJourney();
  const { setJoinResult } = useMissionDraft();
  const { setSession } = useChildMission();

  const submit = async () => {
    if (joinCode.length !== 6) {
      setError('숫자 6자리를 모두 입력해 주세요.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const session = await missionAdapter.joinMission(joinCode);
      setJoinResult(session);
      setSession(session);
      reset();
      router.replace('/child');
    } catch (caught) {
      setError(
        caught instanceof MissionAdapterError
          ? getJoinCodeErrorMessage(caught.code)
          : '심부름에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen bottomInset={false}>
      <TopBar title="심부름 참여" />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.keyboardView}>
        <View style={styles.content}>
          <View style={styles.iconWrap}>
            <Ionicons color={ICanColors.yellowStrong} name="keypad" size={46} />
          </View>
          <Text style={styles.title}>부모님이 알려준 코드를 입력해요</Text>
          <Text style={styles.description}>6자리 코드를 입력하면{`\n`}심부름 길안내가 시작돼요.</Text>

          <TextInput
            accessibilityLabel="6자리 참여 코드"
            autoFocus
            keyboardType="number-pad"
            maxLength={6}
            onChangeText={(value) => {
              setJoinCode(value.replace(/\D/g, ''));
              if (error) setError('');
            }}
            onSubmitEditing={submit}
            placeholder="000000"
            placeholderTextColor="#C6C6C6"
            returnKeyType="done"
            style={[styles.input, error ? styles.inputError : undefined]}
            value={joinCode}
          />
          <Text style={styles.counter}>{joinCode.length} / 6</Text>
          {error ? <Text accessibilityLiveRegion="polite" style={styles.error}>{error}</Text> : null}

          <View style={styles.demoNotice}>
            <Ionicons color={ICanColors.greenDark} name="information-circle" size={18} />
            <Text style={styles.demoNoticeText}>보호자에게 받은 참여 코드를 입력해요.</Text>
          </View>
        </View>
        <View style={styles.buttonWrap}>
          <PrimaryButton label="심부름 시작하기" loading={loading} onPress={submit} />
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  keyboardView: { flex: 1 },
  content: { alignItems: 'center', flex: 1, paddingHorizontal: 24, paddingTop: 58 },
  iconWrap: {
    alignItems: 'center',
    backgroundColor: '#FFF6DE',
    borderRadius: 44,
    height: 88,
    justifyContent: 'center',
    width: 88,
  },
  title: { color: ICanColors.ink, fontSize: 23, fontWeight: '800', marginTop: 24, textAlign: 'center' },
  description: { color: ICanColors.muted, fontSize: 15, lineHeight: 22, marginTop: 10, textAlign: 'center' },
  input: {
    backgroundColor: ICanColors.canvas,
    borderColor: ICanColors.yellowStrong,
    borderRadius: 14,
    borderWidth: 2,
    color: ICanColors.ink,
    fontSize: 34,
    fontWeight: '800',
    height: 76,
    letterSpacing: 14,
    marginTop: 38,
    paddingLeft: 25,
    textAlign: 'center',
    width: '100%',
  },
  inputError: { borderColor: '#EB5757' },
  counter: { alignSelf: 'flex-end', color: ICanColors.subtle, fontSize: 12, marginTop: 7 },
  error: { color: '#D74646', fontSize: 13, marginTop: 10, textAlign: 'center' },
  demoNotice: {
    alignItems: 'center',
    backgroundColor: ICanColors.paleGreen,
    borderRadius: 10,
    flexDirection: 'row',
    marginTop: 24,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  demoNoticeText: { color: ICanColors.greenDark, fontSize: 13, fontWeight: '600', marginLeft: 6 },
  buttonWrap: { paddingBottom: 28, paddingHorizontal: 24 },
});
