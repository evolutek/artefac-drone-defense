/**
 * Platform-aware confirmation alert utility
 *
 * On React Native: uses Alert.alert with proper async callback support
 * On Web: uses window.confirm and executes callback synchronously
 *
 * This fixes the issue where Alert.alert on Expo Web doesn't properly
 * execute async callbacks in the onPress handler.
 */

import { Alert, Platform } from 'react-native';

interface ConfirmationOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  confirmStyle?: 'default' | 'cancel' | 'destructive';
  onConfirm: () => Promise<void> | void;
  onCancel?: () => void;
}

/**
 * Show a confirmation dialog that properly handles async callbacks on all platforms
 */
export async function showConfirmationAlert(options: ConfirmationOptions): Promise<void> {
  const {
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    confirmStyle = 'destructive',
    onConfirm,
    onCancel,
  } = options;

  if (Platform.OS === 'web') {
    // Web: Use window.confirm and execute callback immediately
    // Note: window.confirm is synchronous, so we need to handle async differently
    const confirmed = window.confirm(`${title}\n\n${message}`);

    if (confirmed) {
      console.log('[ConfirmationAlert] Web - User confirmed');
      // Execute the callback (await if it's a Promise)
      await Promise.resolve(onConfirm());
    } else {
      console.log('[ConfirmationAlert] Web - User cancelled');
      onCancel?.();
    }
  } else {
    // Native: Use Alert.alert with proper async support
    return new Promise((resolve) => {
      Alert.alert(
        title,
        message,
        [
          {
            text: cancelText,
            style: 'cancel',
            onPress: () => {
              console.log('[ConfirmationAlert] Native - User cancelled');
              onCancel?.();
              resolve();
            },
          },
          {
            text: confirmText,
            style: confirmStyle,
            onPress: async () => {
              console.log('[ConfirmationAlert] Native - User confirmed');
              await Promise.resolve(onConfirm());
              resolve();
            },
          },
        ]
      );
    });
  }
}

/**
 * Show a simple alert message
 */
export function showAlert(title: string, message: string): void {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
}
