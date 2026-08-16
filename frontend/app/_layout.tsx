import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';

import { ChildJourneyProvider } from '@/features/child/child-journey-context';
import { ChildMissionProvider } from '@/features/child/child-mission-context';
import { MissionDraftProvider } from '@/features/mission/mission-draft-context';

export default function RootLayout() {
  return (
    <MissionDraftProvider>
      <ChildJourneyProvider>
        <ChildMissionProvider>
          <StatusBar style="dark" />
          <Stack screenOptions={{ headerShown: false, animation: 'slide_from_right' }} />
        </ChildMissionProvider>
      </ChildJourneyProvider>
    </MissionDraftProvider>
  );
}
