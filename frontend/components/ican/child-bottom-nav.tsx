import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';

export function ChildBottomNav({ onHome }: { onHome?: () => void }) {
  return (
    <View style={styles.container}>
      <Pressable accessibilityRole="button" onPress={onHome ?? (() => router.replace('/child'))} style={styles.item}>
        <View style={styles.activeIcon}>
          <Ionicons color={ICanColors.green} name="home" size={22} />
        </View>
        <Text style={[styles.label, styles.activeLabel]}>{'심부름\n확인하기'}</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        onPress={() => Alert.alert('보호자 전화', '보호자 전화번호가 연결되면 바로 전화할 수 있어요.')}
        style={styles.item}>
        <Ionicons color="#616161" name="call" size={24} />
        <Text style={styles.label}>{'엄마한테\n전화걸기'}</Text>
      </Pressable>
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
    flexDirection: 'row',
    height: 92,
    justifyContent: 'center',
    left: 0,
    paddingTop: 12,
    position: 'absolute',
    right: 0,
    shadowColor: '#828282',
    shadowOffset: { width: 0, height: -5 },
    shadowOpacity: 0.15,
    shadowRadius: 24,
  },
  item: { alignItems: 'center', marginHorizontal: 34, minWidth: 70 },
  activeIcon: { alignItems: 'center', backgroundColor: ICanColors.paleGreen, borderRadius: 15, height: 29, justifyContent: 'center', width: 29 },
  label: { color: '#616161', fontSize: 11, lineHeight: 15, marginTop: 3, textAlign: 'center' },
  activeLabel: { color: '#374957', fontWeight: '600' },
});
