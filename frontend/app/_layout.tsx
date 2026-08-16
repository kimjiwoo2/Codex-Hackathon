import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';

import { MissionDraftProvider } from '@/features/mission/mission-draft-context';

export default function RootLayout() {
  return (
    <MissionDraftProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, animation: 'slide_from_right' }} />
    </MissionDraftProvider>
  );
}
