import { PropsWithChildren } from 'react';
import { SafeAreaView, ScrollView, StyleSheet, View, ViewStyle } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';

type ScreenProps = PropsWithChildren<{ scroll?: boolean; contentStyle?: ViewStyle; bottomInset?: boolean }>;

export function Screen({ children, scroll = false, contentStyle, bottomInset = true }: ScreenProps) {
  const content = scroll ? (
    <ScrollView
      contentContainerStyle={[styles.scrollContent, bottomInset && styles.bottomInset, contentStyle]}
      showsVerticalScrollIndicator={false}>
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.content, bottomInset && styles.bottomInset, contentStyle]}>{children}</View>
  );
  return <SafeAreaView style={styles.safeArea}>{content}</SafeAreaView>;
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: ICanColors.paper },
  content: { flex: 1 },
  scrollContent: { flexGrow: 1, width: '100%' },
  bottomInset: { paddingBottom: 88 },
});
