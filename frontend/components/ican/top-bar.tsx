import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';

export function TopBar({ title }: { title: string }) {
  return (
    <View style={styles.container}>
      <Pressable accessibilityLabel="뒤로 가기" hitSlop={12} onPress={() => router.back()}>
        <Ionicons color={ICanColors.ink} name="chevron-back" size={26} />
      </Pressable>
      <Text style={styles.title}>{title}</Text>
      <View style={styles.spacer} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    borderBottomColor: ICanColors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    height: 58,
    justifyContent: 'space-between',
    paddingHorizontal: 18,
  },
  title: { color: ICanColors.ink, fontSize: 19, fontWeight: '600' },
  spacer: { width: 26 },
});
