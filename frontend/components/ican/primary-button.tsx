import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';

type Props = { label: string; onPress: () => void; loading?: boolean };

export function PrimaryButton({ label, onPress, loading = false }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={loading}
      onPress={onPress}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
      {loading ? <ActivityIndicator color={ICanColors.paper} /> : <Text style={styles.label}>{label}</Text>}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    backgroundColor: ICanColors.yellow,
    borderRadius: 8,
    height: 55,
    justifyContent: 'center',
    width: '100%',
  },
  label: { color: ICanColors.paper, fontSize: 20, fontWeight: '600' },
  pressed: { opacity: 0.82 },
});
