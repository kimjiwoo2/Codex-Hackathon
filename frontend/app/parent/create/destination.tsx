import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { BottomNav } from '@/components/ican/bottom-nav';
import { PrimaryButton } from '@/components/ican/primary-button';
import { Screen } from '@/components/ican/screen';
import { StepIntro } from '@/components/ican/step-intro';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';

export default function DestinationScreen() {
  return (
    <Screen scroll contentStyle={styles.screen}>
      <TopBar title="심부름 작성" />
      <View style={styles.content}>
        <StepIntro description="2026.08.16 (일)" title="어디로 갈까요?" />
        <View style={styles.searchBox}>
          <Ionicons color={ICanColors.green} name="search" size={22} />
          <Text style={styles.placeholder}>마트 이름을 검색해 주세요.</Text>
        </View>
        <Image resizeMode="cover" source={require('../../../assets/ican/destination-map.png')} style={styles.map} />
        <Pressable style={styles.storeCard}>
          <Image resizeMode="contain" source={require('../../../assets/ican/store.png')} style={styles.storeImage} />
          <View>
            <Text style={styles.storeName}>행복 슈퍼</Text>
            <Text style={styles.storeMeta}>집에서 420m, 도보 약 6분</Text>
          </View>
        </Pressable>
        <PrimaryButton label="장소 선택 완료" onPress={() => router.push('/parent/create/items')} />
      </View>
      <BottomNav active="create" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 110 },
  content: { gap: 20, paddingHorizontal: 24, paddingTop: 22 },
  searchBox: { alignItems: 'center', backgroundColor: ICanColors.canvas, borderRadius: 10, flexDirection: 'row', gap: 10, height: 43, paddingHorizontal: 14 },
  placeholder: { color: 'rgba(20,21,23,0.38)', fontSize: 15 },
  map: { borderRadius: 6, height: 276, width: '100%' },
  storeCard: {
    alignItems: 'center',
    backgroundColor: ICanColors.paper,
    borderRadius: 10,
    elevation: 3,
    flexDirection: 'row',
    height: 91,
    paddingHorizontal: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
  },
  storeImage: { height: 56, marginRight: 14, width: 60 },
  storeName: { color: ICanColors.ink, fontSize: 18, fontWeight: '600' },
  storeMeta: { color: ICanColors.muted, fontSize: 12, marginTop: 4 },
});
