import { router } from 'expo-router';
import { Image, ImageBackground, StyleSheet, Text } from 'react-native';

import { ChildBottomNav } from '@/components/ican/child-bottom-nav';
import { ChildMissionCard } from '@/components/ican/child-mission-card';
import { Screen } from '@/components/ican/screen';
import { useChildJourney } from '@/features/child/child-journey-context';

export default function ChildCompletedScreen() {
  const { setStage } = useChildJourney();

  return (
    <Screen bottomInset={false} contentStyle={styles.screen}>
      <ImageBackground resizeMode="cover" source={require('../../assets/ican/child-background.png')} style={styles.background}>
        <Image resizeMode="contain" source={require('../../assets/ican/logo.png')} style={styles.logo} />
        <Text style={styles.headline}>계산하고, <Text style={styles.green}>집</Text>으로 돌아가자</Text>
        <ChildMissionCard stage="RETURNING" />
        <ChildBottomNav
          onHome={() => {
            setStage('RETURNING');
            router.replace('/child/completed');
          }}
        />
      </ImageBackground>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: '#FFF9E9' },
  background: { flex: 1, paddingTop: 16 },
  logo: { height: 52, marginLeft: 17, width: 111 },
  headline: { color: '#141517', fontSize: 27, fontWeight: '800', lineHeight: 32, marginBottom: 25, marginTop: 28, textAlign: 'center' },
  green: { color: '#50B748' },
});
