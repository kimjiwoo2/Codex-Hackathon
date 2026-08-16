import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { BottomNav } from '@/components/ican/bottom-nav';
import { PrimaryButton } from '@/components/ican/primary-button';
import { Screen } from '@/components/ican/screen';
import { StepIntro } from '@/components/ican/step-intro';
import { TopBar } from '@/components/ican/top-bar';
import { ICanColors } from '@/constants/ican-theme';
import { useMissionDraft } from '@/features/mission/mission-draft-context';

export default function ItemsScreen() {
  const { draft, setQuantity } = useMissionDraft();

  return (
    <Screen scroll contentStyle={styles.screen}>
      <TopBar title="심부름 작성" />
      <View style={styles.content}>
        <StepIntro description={'아이가 쉽게 사올 수 있도록\n사올 물건을 알려주세요.'} title="무엇을 사올까요?" />
        <View style={styles.searchBox}>
          <Ionicons color={ICanColors.green} name="search" size={22} />
          <Text style={styles.placeholder}>사올 물건 검색하기</Text>
        </View>
        <Text style={styles.sectionTitle}>사올 물건</Text>
        <View style={styles.itemCard}>
          <Image resizeMode="contain" source={require('../../../assets/ican/milk.png')} style={styles.milk} />
          <View style={styles.itemCopy}>
            <Text style={styles.itemName}>우유</Text>
            <Text style={styles.itemMeta}>서울 우유 1L</Text>
            <Text style={styles.itemMeta}>{draft.item.quantity}개</Text>
          </View>
          <View style={styles.stepper}>
            <Pressable hitSlop={8} onPress={() => setQuantity(draft.item.quantity - 1)}>
              <Ionicons color={ICanColors.green} name="remove" size={17} />
            </Pressable>
            <Text style={styles.quantity}>{draft.item.quantity}</Text>
            <Pressable hitSlop={8} onPress={() => setQuantity(draft.item.quantity + 1)}>
              <Ionicons color={ICanColors.green} name="add" size={17} />
            </Pressable>
          </View>
        </View>
        <Pressable style={styles.addCard}>
          <Ionicons color={ICanColors.yellowStrong} name="add" size={28} />
          <Text style={styles.addText}>물건 추가하기</Text>
        </Pressable>
        <View style={styles.tipCard}>
          <Text style={styles.tipEyebrow}>심부름 Tip!</Text>
          <Text style={styles.tipText}>처음에는 아이가 평소 자주 봤던 물건부터{`\n`}부탁해 보세요.</Text>
        </View>
        <PrimaryButton label="물건 선택 완료" onPress={() => router.push('/parent/create/confirm')} />
      </View>
      <BottomNav active="create" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 110 },
  content: { gap: 19, paddingHorizontal: 24, paddingTop: 22 },
  searchBox: { alignItems: 'center', backgroundColor: ICanColors.canvas, borderRadius: 10, flexDirection: 'row', gap: 10, height: 43, paddingHorizontal: 14 },
  placeholder: { color: 'rgba(20,21,23,0.38)', fontSize: 15 },
  sectionTitle: { color: ICanColors.ink, fontSize: 18, fontWeight: '700', marginTop: 2 },
  itemCard: { alignItems: 'center', backgroundColor: ICanColors.canvas, borderRadius: 10, flexDirection: 'row', minHeight: 110, paddingHorizontal: 14 },
  milk: { height: 86, width: 75 },
  itemCopy: { flex: 1, marginLeft: 10 },
  itemName: { color: ICanColors.ink, fontSize: 18, fontWeight: '700' },
  itemMeta: { color: 'rgba(20,21,23,0.45)', fontSize: 13, marginTop: 3 },
  stepper: { alignItems: 'center', borderColor: 'rgba(163,183,85,0.35)', borderRadius: 6, borderWidth: 1, flexDirection: 'row', gap: 12, height: 28, paddingHorizontal: 8 },
  quantity: { color: ICanColors.green, fontSize: 13 },
  addCard: { alignItems: 'center', borderColor: '#F5EAD4', borderRadius: 10, borderStyle: 'dashed', borderWidth: 2, flexDirection: 'row', gap: 8, height: 91, justifyContent: 'center' },
  addText: { color: ICanColors.yellowStrong, fontSize: 18, fontWeight: '600' },
  tipCard: { backgroundColor: ICanColors.canvas, borderRadius: 10, minHeight: 99, paddingHorizontal: 84, paddingVertical: 16 },
  tipEyebrow: { color: '#848E5D', fontSize: 13 },
  tipText: { color: ICanColors.ink, fontSize: 13, fontWeight: '600', lineHeight: 18, marginTop: 8 },
});
