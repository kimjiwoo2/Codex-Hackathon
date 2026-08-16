import { router } from 'expo-router';
import { Image, ImageBackground, Pressable, StyleSheet, Text } from 'react-native';

import { ChildBottomNav } from '@/components/ican/child-bottom-nav';
import { ChildLocationStatus } from '@/components/ican/child-location-status';
import { ChildMissionCard } from '@/components/ican/child-mission-card';
import { Screen } from '@/components/ican/screen';
import { useChildAutoNavigation } from '@/features/child/use-child-auto-navigation';
import { useChildJourney } from '@/features/child/child-journey-context';
import { useChildLocation } from '@/features/child/use-child-location';

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
  useChildAutoNavigation({ location, setStage, stage });

  return (
    <Screen bottomInset={false} contentStyle={styles.screen}>
      <ImageBackground resizeMode="cover" source={require('../../assets/ican/child-background.png')} style={styles.background}>
        <Image resizeMode="contain" source={require('../../assets/ican/logo.png')} style={styles.logo} />
        <ChildLocationStatus onRetry={retryLocation} status={locationStatus} />
        <JourneyHeadline stage={stage} />
        <ChildMissionCard
          onAdvance={advance}
          onOpenCamera={() => {
            setStage('ARRIVED');
            router.push('/child/camera');
          }}
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
