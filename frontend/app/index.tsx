import { Ionicons } from '@expo/vector-icons';
import { Link } from 'expo-router';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { Screen } from '@/components/ican/screen';
import { ICanColors } from '@/constants/ican-theme';

export default function RoleScreen() {
  return (
    <Screen bottomInset={false} contentStyle={styles.screen}>
      <Image resizeMode="contain" source={require('../assets/ican/logo.png')} style={styles.logo} />
      <View style={styles.hero}>
        <Image resizeMode="contain" source={require('../assets/ican/home-child.png')} style={styles.child} />
        <Text style={styles.eyebrow}>아이의 첫 심부름을 함께해요</Text>
        <Text style={styles.title}>어떤 역할로 시작할까요?</Text>
      </View>
      <View style={styles.roles}>
        <Link asChild href="/parent" replace>
          <Pressable accessibilityRole="button" style={styles.roleCard}>
            <View style={styles.roleIcon}>
              <Ionicons color={ICanColors.greenDark} name="heart" size={28} />
            </View>
            <View style={styles.roleCopy}>
              <Text style={styles.roleTitle}>부모로 시작</Text>
              <Text style={styles.roleDescription}>심부름을 만들고 아이의 진행을 확인해요.</Text>
            </View>
            <Ionicons color={ICanColors.green} name="chevron-forward" size={22} />
          </Pressable>
        </Link>
        <Link asChild href="/child/join" replace>
          <Pressable accessibilityRole="button" style={styles.roleCard}>
            <View style={[styles.roleIcon, styles.childRoleIcon]}>
              <Ionicons color={ICanColors.yellowStrong} name="happy" size={28} />
            </View>
            <View style={styles.roleCopy}>
              <Text style={styles.roleTitle}>아이로 시작</Text>
              <Text style={styles.roleDescription}>오늘의 심부름과 안전한 길 안내를 확인해요.</Text>
            </View>
            <Ionicons color={ICanColors.yellowStrong} name="chevron-forward" size={22} />
          </Pressable>
        </Link>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingHorizontal: 24, paddingTop: 24 },
  logo: { height: 58, width: 122 },
  hero: { alignItems: 'center', marginTop: 32 },
  child: { height: 190, width: 210 },
  eyebrow: { color: ICanColors.green, fontSize: 15, fontWeight: '600', marginTop: 12 },
  title: { color: ICanColors.ink, fontSize: 25, fontWeight: '700', marginTop: 8 },
  roles: { gap: 12, marginTop: 34 },
  roleCard: {
    alignItems: 'center',
    backgroundColor: ICanColors.paper,
    borderColor: ICanColors.border,
    borderRadius: 14,
    borderWidth: 1,
    flexDirection: 'row',
    minHeight: 92,
    padding: 16,
  },
  roleIcon: {
    alignItems: 'center',
    backgroundColor: ICanColors.paleGreen,
    borderRadius: 24,
    height: 48,
    justifyContent: 'center',
    width: 48,
  },
  roleCopy: { flex: 1, marginLeft: 13 },
  roleTitle: { color: ICanColors.ink, fontSize: 18, fontWeight: '700' },
  roleDescription: { color: ICanColors.muted, fontSize: 13, lineHeight: 18, marginTop: 4 },
  childRoleIcon: { backgroundColor: '#FFF6DE' },
});
