import { router } from 'expo-router';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { BottomNav } from '@/components/ican/bottom-nav';
import { Screen } from '@/components/ican/screen';
import { ICanColors } from '@/constants/ican-theme';

const recentMissions = [
  { label: '우유 사오기', source: require('../../assets/ican/recent-milk.png') },
  { label: '식빵 사오기', source: require('../../assets/ican/recent-bread.png') },
  { label: '당근 사오기', source: require('../../assets/ican/recent-carrot.png') },
];

export default function ParentHomeScreen() {
  return (
    <Screen contentStyle={styles.screen}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Image resizeMode="contain" source={require('../../assets/ican/logo.png')} style={styles.logo} />
        <View style={styles.greetingRow}>
          <View style={styles.greetingCopy}>
            <Text style={styles.date}>2026년 8월 16일</Text>
            <Text style={styles.greeting}>
              <Text style={styles.bold}>이준이의 심부름</Text>을{`\n`}확인해 볼까요?  →
            </Text>
          </View>
          <Image resizeMode="contain" source={require('../../assets/ican/home-child.png')} style={styles.heroChild} />
        </View>
        <Text style={styles.sectionTitle}>최근 다녀온 심부름</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.recentScroll}>
          {recentMissions.map((mission) => (
            <View key={mission.label} style={styles.recentItem}>
              <Image resizeMode="cover" source={mission.source} style={styles.recentImage} />
              <Text style={styles.recentLabel}>{mission.label}</Text>
            </View>
          ))}
        </ScrollView>
        <View style={styles.tipBox}>
          <Text style={styles.tipText}>Tip! 작은 심부름 하나가 아이의 큰 자신감이 돼요!</Text>
        </View>
        <Text style={[styles.sectionTitle, styles.todayTitle]}>오늘의 심부름 시키기</Text>
        <Pressable onPress={() => router.push('/parent/create/destination')} style={styles.startCard}>
          <View style={styles.startCopy}>
            <Text style={styles.startEyebrow}>오늘은 어떤 심부름을 해볼까요?</Text>
            <Text style={styles.startTitle}>아이가 다녀올 곳과 사올 물건을 정해주세요.</Text>
            <View style={styles.startButton}>
              <Text style={styles.startButtonText}>바로 작성하기</Text>
            </View>
          </View>
          <Image resizeMode="contain" source={require('../../assets/ican/prompt-chick.png')} style={styles.chick} />
        </Pressable>
      </ScrollView>
      <BottomNav active="home" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: ICanColors.paper },
  content: { paddingBottom: 36, paddingTop: 14 },
  logo: { height: 52, marginLeft: 24, width: 112 },
  greetingRow: { flexDirection: 'row', minHeight: 112, paddingHorizontal: 28 },
  greetingCopy: { flex: 1, paddingTop: 16 },
  date: { color: ICanColors.green, fontSize: 15, marginBottom: 5 },
  greeting: { color: ICanColors.ink, fontSize: 22, lineHeight: 28 },
  bold: { fontWeight: '700' },
  heroChild: { height: 108, width: 110 },
  sectionTitle: { color: ICanColors.ink, fontSize: 18, fontWeight: '700', marginLeft: 27, marginTop: 8 },
  recentScroll: { marginTop: 14, paddingLeft: 24 },
  recentItem: { marginRight: 12, width: 136 },
  recentImage: { borderRadius: 6, height: 164, width: 136 },
  recentLabel: { color: ICanColors.muted, fontSize: 12, fontWeight: '600', marginTop: 7 },
  tipBox: { backgroundColor: 'rgba(163,183,85,0.15)', borderRadius: 10, marginHorizontal: 24, marginTop: 20, padding: 14 },
  tipText: { color: '#848E5D', fontSize: 14 },
  todayTitle: { marginTop: 24 },
  startCard: {
    alignItems: 'center',
    backgroundColor: ICanColors.lime,
    borderRadius: 8,
    flexDirection: 'row',
    height: 130,
    marginHorizontal: 24,
    marginTop: 14,
    overflow: 'hidden',
    padding: 17,
  },
  startCopy: { flex: 1 },
  startEyebrow: { color: '#848E5D', fontSize: 13 },
  startTitle: { color: ICanColors.ink, fontSize: 15, fontWeight: '600', lineHeight: 22, marginTop: 3 },
  startButton: { backgroundColor: ICanColors.paper, borderRadius: 5, marginTop: 13, paddingHorizontal: 10, paddingVertical: 7, width: 92 },
  startButtonText: { color: '#869A37', fontSize: 12, textAlign: 'center' },
  chick: { height: 76, width: 64 },
});
