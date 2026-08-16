import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { useRef, useState } from 'react';
import { ActivityIndicator, Image, Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import { ICanColors } from '@/constants/ican-theme';
import { useChildJourney } from '@/features/child/child-journey-context';

export default function ChildCameraScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [error, setError] = useState('');
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const { setStage } = useChildJourney();

  const finishVerification = () => {
    setStage('RETURNING');
    router.replace('/child/completed');
  };

  const takePicture = async () => {
    if (!cameraReady || capturing) return;

    setCapturing(true);
    setError('');
    try {
      const picture = await cameraRef.current?.takePictureAsync({ quality: 0.7 });
      if (!picture?.uri) throw new Error('PHOTO_URI_MISSING');
      setPhotoUri(picture.uri);
    } catch {
      setError('사진을 찍지 못했어요. 카메라를 확인하고 다시 시도해 주세요.');
    } finally {
      setCapturing(false);
    }
  };

  if (!permission) return <View style={styles.permissionScreen} />;

  if (!permission.granted) {
    return (
      <View style={styles.permissionScreen}>
        <View style={styles.permissionCard}>
          <Ionicons color={ICanColors.greenDark} name="camera" size={54} />
          <Text style={styles.permissionTitle}>우유를 카메라로 확인해요</Text>
          <Text style={styles.permissionCopy}>심부름 물건을 비추려면 카메라 권한이 필요해요.</Text>
          <Pressable
            accessibilityRole="button"
            onPress={permission.canAskAgain ? requestPermission : Linking.openSettings}
            style={styles.permissionButton}>
            <Text style={styles.permissionButtonText}>
              {permission.canAskAgain ? '카메라 허용하기' : '기기 설정 열기'}
            </Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={finishVerification} style={styles.demoButton}>
            <Text style={styles.demoButtonText}>카메라 없이 데모 계속하기</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  if (photoUri) {
    return (
      <View style={styles.cameraScreen}>
        <Image resizeMode="cover" source={{ uri: photoUri }} style={StyleSheet.absoluteFillObject} />
        <View style={styles.previewShade} />
        <View style={styles.cameraHeader}>
          <Pressable accessibilityLabel="사진 다시 찍기" hitSlop={10} onPress={() => setPhotoUri(null)}>
            <Ionicons color={ICanColors.paper} name="chevron-back" size={30} />
          </Pressable>
          <Text style={styles.cameraTitle}>찍은 사진을 확인해 주세요</Text>
          <View style={styles.headerSpacer} />
        </View>
        <View style={styles.previewCard}>
          <View style={styles.previewTitleRow}>
            <View style={styles.previewIcon}>
              <Ionicons color={ICanColors.greenDark} name="checkmark" size={22} />
            </View>
            <View style={styles.previewCopy}>
              <Text style={styles.previewTitle}>우유가 잘 보이나요?</Text>
              <Text style={styles.previewDescription}>사진은 서버로 전송되지 않고 이 화면에서만 확인해요.</Text>
            </View>
          </View>
          <View style={styles.previewActions}>
            <Pressable accessibilityRole="button" onPress={() => setPhotoUri(null)} style={styles.retakeButton}>
              <Text style={styles.retakeButtonText}>다시 찍기</Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={finishVerification} style={styles.confirmButton}>
              <Text style={styles.confirmButtonText}>우유 확인 완료</Text>
            </Pressable>
          </View>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.cameraScreen}>
      <CameraView
        facing="back"
        onCameraReady={() => setCameraReady(true)}
        ref={cameraRef}
        style={StyleSheet.absoluteFillObject}
      />
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
        {error ? <Text accessibilityLiveRegion="polite" style={styles.cameraError}>{error}</Text> : null}
        <Pressable
          accessibilityLabel="물건 촬영하기"
          disabled={!cameraReady || capturing}
          onPress={takePicture}
          style={[styles.shutter, (!cameraReady || capturing) && styles.shutterDisabled]}>
          {capturing ? <ActivityIndicator color={ICanColors.yellowStrong} /> : <View style={styles.shutterInner} />}
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
  cameraError: { color: '#FFD6D6', fontSize: 13, marginBottom: 12, paddingHorizontal: 28, textAlign: 'center' },
  shutter: { alignItems: 'center', borderColor: ICanColors.paper, borderRadius: 38, borderWidth: 4, height: 76, justifyContent: 'center', width: 76 },
  shutterInner: { backgroundColor: ICanColors.yellow, borderRadius: 29, height: 58, width: 58 },
  shutterDisabled: { opacity: 0.55 },
  previewShade: { backgroundColor: 'rgba(0,0,0,0.24)', bottom: 0, left: 0, position: 'absolute', right: 0, top: 0 },
  previewCard: {
    backgroundColor: ICanColors.paper,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    bottom: 0,
    left: 0,
    paddingBottom: 34,
    paddingHorizontal: 24,
    paddingTop: 24,
    position: 'absolute',
    right: 0,
  },
  previewTitleRow: { alignItems: 'center', flexDirection: 'row' },
  previewIcon: { alignItems: 'center', backgroundColor: ICanColors.paleGreen, borderRadius: 24, height: 48, justifyContent: 'center', width: 48 },
  previewCopy: { flex: 1, marginLeft: 13 },
  previewTitle: { color: ICanColors.ink, fontSize: 19, fontWeight: '800' },
  previewDescription: { color: ICanColors.muted, fontSize: 13, lineHeight: 18, marginTop: 5 },
  previewActions: { flexDirection: 'row', gap: 10, marginTop: 22 },
  retakeButton: { alignItems: 'center', borderColor: ICanColors.border, borderRadius: 9, borderWidth: 1, flex: 1, height: 52, justifyContent: 'center' },
  retakeButtonText: { color: ICanColors.muted, fontSize: 16, fontWeight: '700' },
  confirmButton: { alignItems: 'center', backgroundColor: ICanColors.yellow, borderRadius: 9, flex: 1.4, height: 52, justifyContent: 'center' },
  confirmButtonText: { color: ICanColors.paper, fontSize: 16, fontWeight: '700' },
  permissionScreen: { alignItems: 'center', backgroundColor: '#FFF9E9', flex: 1, justifyContent: 'center', padding: 28 },
  permissionCard: { alignItems: 'center', backgroundColor: ICanColors.paper, borderColor: '#FDE6AD', borderRadius: 20, borderWidth: 3, padding: 28, width: '100%' },
  permissionTitle: { color: ICanColors.ink, fontSize: 22, fontWeight: '800', marginTop: 18 },
  permissionCopy: { color: ICanColors.muted, fontSize: 14, lineHeight: 21, marginTop: 8, textAlign: 'center' },
  permissionButton: { alignItems: 'center', backgroundColor: ICanColors.yellow, borderRadius: 8, height: 52, justifyContent: 'center', marginTop: 24, width: '100%' },
  permissionButtonText: { color: ICanColors.paper, fontSize: 17, fontWeight: '700' },
  demoButton: { marginTop: 16, padding: 8 },
  demoButtonText: { color: ICanColors.greenDark, fontSize: 14, fontWeight: '600' },
});
