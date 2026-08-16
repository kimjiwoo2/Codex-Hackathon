import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';

type NavKey = 'home' | 'create' | 'monitor' | 'report';
const navItems: { key: NavKey; label: string; icon: keyof typeof Ionicons.glyphMap; route?: string }[] = [
  { key: 'home', label: '홈', icon: 'home', route: '/parent' },
  { key: 'create', label: '심부름 작성', icon: 'pencil', route: '/parent/create/destination' },
  { key: 'monitor', label: '위치 확인', icon: 'map', route: '/parent/monitor' },
  { key: 'report', label: '리포트 확인', icon: 'documents' },
];

export function BottomNav({ active }: { active: NavKey }) {
  return (
    <View style={styles.container}>
      {navItems.map((item) => {
        const isActive = item.key === active;
        return (
          <Pressable
            accessibilityRole="button"
            key={item.key}
            onPress={() => item.route && router.replace(item.route as never)}
            style={styles.item}>
            <View style={[styles.iconWrap, isActive && styles.activeIconWrap]}>
              <Ionicons color={isActive ? ICanColors.green : '#616161'} name={item.icon} size={21} />
            </View>
            <Text style={[styles.label, isActive && styles.activeLabel]}>{item.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'flex-start',
    backgroundColor: ICanColors.paper,
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    bottom: 0,
    elevation: 12,
    flexDirection: 'row',
    height: 86,
    justifyContent: 'space-around',
    left: 0,
    paddingTop: 13,
    position: 'absolute',
    right: 0,
    shadowColor: '#828282',
    shadowOffset: { width: 0, height: -5 },
    shadowOpacity: 0.12,
    shadowRadius: 24,
  },
  item: { alignItems: 'center', minWidth: 70 },
  iconWrap: { alignItems: 'center', height: 28, justifyContent: 'center', width: 30 },
  activeIconWrap: { backgroundColor: ICanColors.paleGreen, borderRadius: 15 },
  label: { color: '#616161', fontSize: 11, marginTop: 4 },
  activeLabel: { color: ICanColors.ink, fontWeight: '600' },
});
