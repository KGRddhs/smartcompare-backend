/**
 * SmartCompare - Camera Screen
 * Capture 2-4 product images for comparison
 */

import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  SafeAreaView,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, CapturedImage } from '../types';
import { compareProducts } from '../services/api';

type CameraScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Camera'>;
};

export default function CameraScreen({ navigation }: CameraScreenProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const [capturedImages, setCapturedImages] = useState<CapturedImage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [facing, setFacing] = useState<CameraType>('back');
  const cameraRef = useRef<CameraView>(null);

  const MIN_IMAGES = 2;
  const MAX_IMAGES = 4;

  // Request camera permission
  if (!permission) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.permissionContainer}>
          <Text style={styles.permissionTitle}>Camera Permission Needed</Text>
          <Text style={styles.permissionText}>
            SmartCompare needs camera access to photograph products for comparison.
          </Text>
          <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
            <Text style={styles.permissionButtonText}>Grant Permission</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.galleryButton}
            onPress={pickFromGallery}
          >
            <Text style={styles.galleryButtonText}>Or pick from gallery</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const takePicture = async () => {
    if (cameraRef.current && capturedImages.length < MAX_IMAGES) {
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          base64: false,
          exif: false,
          imageType: 'jpg',
        });
        
        if (photo) {
          setCapturedImages([
            ...capturedImages,
            {
              uri: photo.uri,
              width: photo.width,
              height: photo.height,
            },
          ]);
        }
      } catch (error) {
        console.error('Error taking picture:', error);
        Alert.alert('Error', 'Failed to take picture. Please try again.');
      }
    }
  };

  const pickFromGallery = async () => {
    const remainingSlots = MAX_IMAGES - capturedImages.length;
    if (remainingSlots <= 0) {
      Alert.alert('Maximum Reached', `You can only compare up to ${MAX_IMAGES} products.`);
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      selectionLimit: remainingSlots,
      quality: 0.8,
      exif: false,
    });

    if (!result.canceled && result.assets) {
      const newImages: CapturedImage[] = result.assets.map((asset) => ({
        uri: asset.uri,
        width: asset.width,
        height: asset.height,
      }));
      setCapturedImages([...capturedImages, ...newImages]);
    }
  };

  const removeImage = (index: number) => {
    setCapturedImages(capturedImages.filter((_, i) => i !== index));
  };

  const handleCompare = async () => {
    if (capturedImages.length < MIN_IMAGES) {
      Alert.alert(
        'Need More Products',
        `Please capture at least ${MIN_IMAGES} products to compare.`
      );
      return;
    }

    setIsProcessing(true);

    try {
      const imageUris = capturedImages.map((img) => img.uri);
      const result = await compareProducts(imageUris, 'Bahrain');

      if (result.success) {
        navigation.replace('Results', { result });
      } else {
        Alert.alert('Comparison Failed', result.errors?.[0] || 'Please try again.');
      }
    } catch (error: any) {
      console.error('Comparison error:', error);
      
      if (error.response?.status === 429) {
        Alert.alert(
          'Daily Limit Reached',
          'You\'ve used all your free comparisons today. Upgrade to Premium for unlimited access!'
        );
      } else if (error.message?.includes('Network')) {
        Alert.alert(
          'Connection Error',
          'Could not connect to server. Make sure the backend is running.'
        );
      } else {
        Alert.alert('Error', error.message || 'Comparison failed. Please try again.');
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const toggleCameraFacing = () => {
    setFacing(current => (current === 'back' ? 'front' : 'back'));
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Camera View */}
      <View style={styles.cameraContainer}>
        <CameraView 
          ref={cameraRef} 
          style={styles.camera} 
          facing={facing}
        >
          {/* Overlay with instructions */}
          <View style={styles.overlay}>
            <Text style={styles.overlayText}>
              {capturedImages.length === 0
                ? 'Point at first product'
                : `Product ${capturedImages.length + 1} of ${MAX_IMAGES}`}
            </Text>
          </View>
        </CameraView>
      </View>

      {/* Captured Images Preview */}
      {capturedImages.length > 0 && (
        <View style={styles.previewContainer}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {capturedImages.map((image, index) => (
              <View key={index} style={styles.previewItem}>
                <Image source={{ uri: image.uri }} style={styles.previewImage} />
                <TouchableOpacity
                  style={styles.removeButton}
                  onPress={() => removeImage(index)}
                >
                  <Text style={styles.removeButtonText}>✕</Text>
                </TouchableOpacity>
                <Text style={styles.previewLabel}>Product {index + 1}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Progress Indicator */}
      <View style={styles.progressContainer}>
        <Text style={styles.progressText}>
          {capturedImages.length} / {MAX_IMAGES} products captured
          {capturedImages.length < MIN_IMAGES && ` (min ${MIN_IMAGES})`}
        </Text>
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              { width: `${(capturedImages.length / MAX_IMAGES) * 100}%` },
            ]}
          />
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.controls}>
        {isProcessing ? (
          <View style={styles.processingContainer}>
            <ActivityIndicator size="large" color="#007AFF" />
            <Text style={styles.processingText}>Analyzing products...</Text>
            <Text style={styles.processingHint}>This may take 30-60 seconds</Text>
          </View>
        ) : (
          <>
            <View style={styles.buttonRow}>
              {/* Gallery Button */}
              <TouchableOpacity style={styles.sideButton} onPress={pickFromGallery}>
                <Text style={styles.sideButtonText}>🖼️</Text>
              </TouchableOpacity>

              {/* Capture Button */}
              <TouchableOpacity
                style={[
                  styles.captureButton,
                  capturedImages.length >= MAX_IMAGES && styles.captureButtonDisabled,
                ]}
                onPress={takePicture}
                disabled={capturedImages.length >= MAX_IMAGES}
              >
                <View style={styles.captureButtonInner} />
              </TouchableOpacity>

              {/* Flip Camera Button */}
              <TouchableOpacity style={styles.sideButton} onPress={toggleCameraFacing}>
                <Text style={styles.sideButtonText}>🔄</Text>
              </TouchableOpacity>
            </View>

            {/* Compare Button */}
            {capturedImages.length >= MIN_IMAGES && (
              <TouchableOpacity style={styles.compareButton} onPress={handleCompare}>
                <Text style={styles.compareButtonText}>
                  Compare {capturedImages.length} Products →
                </Text>
              </TouchableOpacity>
            )}
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  cameraContainer: {
    flex: 1,
  },
  camera: {
    flex: 1,
  },
  overlay: {
    position: 'absolute',
    top: 20,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  overlayText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  previewContainer: {
    height: 100,
    backgroundColor: 'rgba(0,0,0,0.8)',
    paddingVertical: 10,
    paddingHorizontal: 5,
  },
  previewItem: {
    marginHorizontal: 5,
    alignItems: 'center',
  },
  previewImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#FFF',
  },
  removeButton: {
    position: 'absolute',
    top: -5,
    right: -5,
    backgroundColor: '#FF3B30',
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  removeButtonText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold',
  },
  previewLabel: {
    color: '#FFF',
    fontSize: 10,
    marginTop: 4,
  },
  progressContainer: {
    backgroundColor: 'rgba(0,0,0,0.8)',
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  progressText: {
    color: '#FFF',
    fontSize: 12,
    marginBottom: 8,
    textAlign: 'center',
  },
  progressBar: {
    height: 4,
    backgroundColor: '#333',
    borderRadius: 2,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#007AFF',
    borderRadius: 2,
  },
  controls: {
    backgroundColor: '#000',
    paddingVertical: 20,
    paddingHorizontal: 20,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  captureButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#FFF',
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 30,
  },
  captureButtonDisabled: {
    opacity: 0.3,
  },
  captureButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#FFF',
    borderWidth: 4,
    borderColor: '#000',
  },
  sideButton: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sideButtonText: {
    fontSize: 24,
  },
  compareButton: {
    backgroundColor: '#34C759',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  compareButtonText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  processingContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  processingText: {
    color: '#FFF',
    fontSize: 16,
    marginTop: 12,
  },
  processingHint: {
    color: '#999',
    fontSize: 12,
    marginTop: 4,
  },
  permissionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    backgroundColor: '#F5F5F5',
  },
  permissionTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#1A1A1A',
  },
  permissionText: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    marginBottom: 24,
  },
  permissionButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 12,
  },
  permissionButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  galleryButton: {
    marginTop: 16,
    padding: 12,
  },
  galleryButtonText: {
    color: '#007AFF',
    fontSize: 14,
  },
});