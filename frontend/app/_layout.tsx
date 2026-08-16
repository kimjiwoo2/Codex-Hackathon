import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';

import { ChildJourneyProvider } from '@/features/child/child-journey-context';
import { MissionDraftProvider } from '@/features/mission/mission-draft-context';
import { ChildMissionProvider } from '@/features/mission/child-mission-context';

export default function RootLayout() {
  return (
    <MissionDraftProvider>
      <ChildMissionProvider>
        <ChildJourneyProvider>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false, animation: 'slide_from_right' }} />
        </ChildJourneyProvider>
      </ChildMissionProvider>
    </MissionDraftProvider>
  );
}
