import * as Speech from 'expo-speech';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef } from 'react';
import { Image, ImageBackground, Pressable, StyleSheet, Text } from 'react-native';

import { ChildBottomNav } from '@/components/ican/child-bottom-nav';
import { ChildLocationStatus } from '@/components/ican/child-location-status';
import { ChildMissionCard } from '@/components/ican/child-mission-card';
import { Screen } from '@/components/ican/screen';
import { useChildJourney } from '@/features/child/child-journey-context';
import { useChildMission } from '@/features/child/child-mission-context';
import { stageFromGuidance } from '@/features/child/location-guidance';
import { useChildLocation } from '@/features/child/use-child-location';
import { useMissionDraft } from '@/features/mission/mission-draft-context';
import {
  childMissionApi,
  type ChildLocationUpdateResult,
  MissionAdapterError,
} from '@/services/mission-adapter';

function JourneyHeadline({ stage }: { stage: ReturnType<typeof useChildJourney>['stage'] }) {
  if (stage === 'STOP') {
    return <Text style={styles.headline}><Text style={styles.orange}>이준아, </Text>신호등 조심해!</Text>;
  }
  if (stage === 'ARRIVED') {
    return <Text style={styles.headline}><Text style={styles.green}>행복 슈퍼</Text>에 도착했어!</Text>;
  }
  return <Text style={styles.headline}>안녕, <Text style={styles.orange}>이준아!</Text></Text>;
}

export default function ChildHomeScreen() {
  const { advance, setStage, stage } = useChildJourney();
  const { location, retry: retryLocation, status: locationStatus } = useChildLocation();
  const { selectedItem, session, updateStatus } = useChildMission();
  const { createResult, draft } = useMissionDraft();
  const initialMissionRef = useRef<string>('');
  const lastGuidanceKeyRef = useRef<string>('');
  const lastLocationKeyRef = useRef<string>('');
  const inFlightRef = useRef(false);
  const demoFallbackEnabled = __DEV__ && createResult?.missionId === session?.missionId;

  const applyGuidance = useCallback((response: ChildLocationUpdateResult) => {
    updateStatus(response.status);
    setStage(stageFromGuidance(response.instructionCode, response.status));
    const guidanceKey = `${response.status}:${response.instructionCode}:${response.message}`;
    if (guidanceKey !== lastGuidanceKeyRef.current) {
      lastGuidanceKeyRef.current = guidanceKey;
      Speech.stop();
      Speech.speak(response.message, { language: 'ko-KR', rate: 0.92 });
    }
    if (response.status === 'COMPLETED') {
      router.replace('/child/completed');
    }
  }, [setStage, updateStatus]);

  useEffect(() => {
    if (!session || session.missionId === initialMissionRef.current) return;
    initialMissionRef.current = session.missionId;
    lastLocationKeyRef.current = '';
    const guidanceKey = `join:${session.message}`;
    lastGuidanceKeyRef.current = guidanceKey;
    Speech.stop();
    Speech.speak(session.message, { language: 'ko-KR', rate: 0.92 });
  }, [session]);

  useEffect(() => {
    if (!session || !location || session.status === 'COMPLETED' || inFlightRef.current) {
      return;
    }

    const locationKey = `${location.timestamp}:${location.coords.latitude}:${location.coords.longitude}`;
    if (locationKey === lastLocationKeyRef.current) return;
    lastLocationKeyRef.current = locationKey;
    inFlightRef.current = true;
    void childMissionApi.updateLocation(session.missionId, session.childToken, {
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
      accuracyM: location.coords.accuracy ?? 0,
      headingDeg: location.coords.heading != null && location.coords.heading >= 0 ? location.coords.heading : undefined,
      speedMps: location.coords.speed != null && location.coords.speed >= 0 ? location.coords.speed : undefined,
      observedAt: location.timestamp ? new Date(location.timestamp).toISOString() : new Date().toISOString(),
    }).then(applyGuidance).catch((error: unknown) => {
      if (!(error instanceof MissionAdapterError)) {
        return;
      }
      const guidanceKey = `error:${error.message}`;
      if (guidanceKey !== lastGuidanceKeyRef.current) {
        lastGuidanceKeyRef.current = guidanceKey;
        Speech.stop();
        Speech.speak(error.message, { language: 'ko-KR', rate: 0.92 });
      }
    }).finally(() => {
      inFlightRef.current = false;
    });
  }, [applyGuidance, location, session]);

  const advanceWithDemoLocation = async () => {
    if (!session || inFlightRef.current) return;
    if (stage !== 'STOP' && stage !== 'RETURNING') {
      advance();
      return;
    }
    if (!demoFallbackEnabled) return;

    inFlightRef.current = true;
    try {
      const coordinate = stage === 'RETURNING' ? draft.home : draft.store;
      let response: ChildLocationUpdateResult | null = null;
      for (let index = 0; index < 2; index += 1) {
        response = await childMissionApi.updateLocation(session.missionId, session.childToken, {
          ...coordinate,
          accuracyM: 5,
          observedAt: new Date().toISOString(),
        });
      }
      if (response) applyGuidance(response);
    } catch (error) {
      if (error instanceof MissionAdapterError) {
        Speech.stop();
        Speech.speak(error.message, { language: 'ko-KR', rate: 0.92 });
      }
    } finally {
      inFlightRef.current = false;
    }
  };

  if (!session) {
    router.replace('/child/join');
    return null;
  }

  if (!selectedItem && session.status !== 'RETURNING' && session.status !== 'COMPLETED') {
    router.replace('/child/completed');
    return null;
  }

  return (
    <Screen bottomInset={false} contentStyle={styles.screen}>
      <ImageBackground resizeMode="cover" source={require('../../assets/ican/child-background.png')} style={styles.background}>
        <Image resizeMode="contain" source={require('../../assets/ican/logo.png')} style={styles.logo} />
        <ChildLocationStatus onRetry={retryLocation} status={locationStatus} />
        <JourneyHeadline stage={stage} />
        <ChildMissionCard
          demoFallbackEnabled={demoFallbackEnabled}
          onAdvance={() => void advanceWithDemoLocation()}
          onOpenCamera={() => {
            setStage('ARRIVED');
            router.push('/child/camera');
          }}
          itemDetails={selectedItem ? [selectedItem.brand, selectedItem.size].filter(Boolean).join(' · ') : undefined}
          itemName={selectedItem?.name}
          stage={stage}
        />
        {stage === 'STOP' ? (
          <Pressable accessibilityRole="button" onPress={() => router.push('/child/road')} style={styles.roadSafetyButton}>
            <Text style={styles.roadSafetyButtonText}>카메라로 주변 안전 확인하기</Text>
          </Pressable>
        ) : null}
        <ChildBottomNav />
      </ImageBackground>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: '#FFF9E9' },
  background: { flex: 1, paddingTop: 16 },
  logo: { height: 52, marginLeft: 17, width: 111 },
  headline: { color: '#141517', fontSize: 27, fontWeight: '800', lineHeight: 32, marginBottom: 25, marginTop: 28, textAlign: 'center' },
  orange: { color: '#F9A20A' },
  green: { color: '#50B748' },
  roadSafetyButton: { alignItems: 'center', backgroundColor: '#E85B4A', borderRadius: 12, marginHorizontal: 24, marginTop: -112, padding: 14, zIndex: 1 },
  roadSafetyButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '800' },
});
