import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';
import { useChildJourney } from '@/features/child/child-journey-context';

export default function ChildCameraScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const { setStage } = useChildJourney();

  const finishVerification = () => {
    setStage('RETURNING');
    router.replace('/child/completed');
  };

  if (!permission) return <View style={styles.permissionScreen} />;

  if (!permission.granted) {
    return (
      <View style={styles.permissionScreen}>
        <View style={styles.permissionCard}>
          <Ionicons color={ICanColors.greenDark} name="camera" size={54} />
          <Text style={styles.permissionTitle}>우유를 카메라로 확인해요</Text>
          <Text style={styles.permissionCopy}>심부름 물건을 비추려면 카메라 권한이 필요해요.</Text>
          <Pressable accessibilityRole="button" onPress={requestPermission} style={styles.permissionButton}>
            <Text style={styles.permissionButtonText}>카메라 허용하기</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={finishVerification} style={styles.demoButton}>
            <Text style={styles.demoButtonText}>웹 데모에서는 바로 확인</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.cameraScreen}>
      <CameraView facing="back" style={StyleSheet.absoluteFillObject} />
      <View style={styles.cameraHeader}>
        <Pressable accessibilityLabel="뒤로 가기" hitSlop={10} onPress={() => router.back()}>
          <Ionicons color={ICanColors.paper} name="chevron-back" size={30} />
        </Pressable>
        <Text style={styles.cameraTitle}>우유를 화면 안에 맞춰주세요</Text>
        <View style={styles.headerSpacer} />
      </View>
      <View style={styles.guideFrame} />
      <View style={styles.cameraFooter}>
        <Text style={styles.cameraHint}>서울 우유 1L가 맞는지 확인할게요.</Text>
        <Pressable accessibilityLabel="물건 촬영하기" onPress={finishVerification} style={styles.shutter}>
          <View style={styles.shutterInner} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  cameraScreen: { backgroundColor: '#111', flex: 1 },
  cameraHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 54 },
  cameraTitle: { color: ICanColors.paper, fontSize: 17, fontWeight: '700' },
  headerSpacer: { width: 30 },
  guideFrame: { borderColor: ICanColors.yellow, borderRadius: 20, borderWidth: 4, height: 330, left: 42, position: 'absolute', right: 42, top: 190 },
  cameraFooter: { alignItems: 'center', bottom: 52, left: 0, position: 'absolute', right: 0 },
  cameraHint: { color: ICanColors.paper, fontSize: 15, marginBottom: 22 },
  shutter: { alignItems: 'center', borderColor: ICanColors.paper, borderRadius: 38, borderWidth: 4, height: 76, justifyContent: 'center', width: 76 },
  shutterInner: { backgroundColor: ICanColors.yellow, borderRadius: 29, height: 58, width: 58 },
  permissionScreen: { alignItems: 'center', backgroundColor: '#FFF9E9', flex: 1, justifyContent: 'center', padding: 28 },
  permissionCard: { alignItems: 'center', backgroundColor: ICanColors.paper, borderColor: '#FDE6AD', borderRadius: 20, borderWidth: 3, padding: 28, width: '100%' },
  permissionTitle: { color: ICanColors.ink, fontSize: 22, fontWeight: '800', marginTop: 18 },
  permissionCopy: { color: ICanColors.muted, fontSize: 14, lineHeight: 21, marginTop: 8, textAlign: 'center' },
  permissionButton: { alignItems: 'center', backgroundColor: ICanColors.yellow, borderRadius: 8, height: 52, justifyContent: 'center', marginTop: 24, width: '100%' },
  permissionButtonText: { color: ICanColors.paper, fontSize: 17, fontWeight: '700' },
  demoButton: { marginTop: 16, padding: 8 },
  demoButtonText: { color: ICanColors.greenDark, fontSize: 14, fontWeight: '600' },
});
