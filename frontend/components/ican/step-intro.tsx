import { Image, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';

export function StepIntro({ title, description }: { title: string; description: string }) {
  return (
    <View style={styles.container}>
      <Image resizeMode="contain" source={require('../../assets/ican/mascot-question.png')} style={styles.mascot} />
      <View style={styles.copy}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', flexDirection: 'row', gap: 10 },
  mascot: { height: 66, width: 62 },
  copy: { flex: 1 },
  title: { color: ICanColors.ink, fontSize: 20, fontWeight: '600', lineHeight: 28 },
  description: { color: ICanColors.muted, fontSize: 14, lineHeight: 19, marginTop: 2 },
});
