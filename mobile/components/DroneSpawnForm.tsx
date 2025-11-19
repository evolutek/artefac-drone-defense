import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Switch,
} from 'react-native';
import api from '../services/api';

export default function DroneSpawnForm({ onSpawnSuccess }: { onSpawnSuccess?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [useCustomPosition, setUseCustomPosition] = useState(false);
  const [x, setX] = useState('');
  const [y, setY] = useState('');
  const [z, setZ] = useState('0.5');

  const handleSpawn = async () => {
    try {
      setLoading(true);

      let position;
      if (useCustomPosition) {
        // Validate coordinates
        const xNum = parseFloat(x);
        const yNum = parseFloat(y);
        const zNum = parseFloat(z);

        if (isNaN(xNum) || isNaN(yNum) || isNaN(zNum)) {
          Alert.alert('Invalid Input', 'Please enter valid numbers for coordinates');
          return;
        }

        position = { x: xNum, y: yNum, z: zNum };
      }

      const result = await api.spawnDrone(position);

      if (result.success) {
        Alert.alert('Success', result.message);
        // Reset form
        setX('');
        setY('');
        setZ('0.5');
        setUseCustomPosition(false);
        onSpawnSuccess?.();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to spawn drone');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Spawn New Drone</Text>

      {/* Custom Position Toggle */}
      <View style={styles.switchRow}>
        <Text style={styles.switchLabel}>Custom Position</Text>
        <Switch
          value={useCustomPosition}
          onValueChange={setUseCustomPosition}
          trackColor={{ false: '#d1d5db', true: '#3b82f6' }}
          thumbColor={useCustomPosition ? '#1e40af' : '#f4f3f4'}
        />
      </View>

      {useCustomPosition && (
        <View style={styles.positionInputs}>
          <View style={styles.inputRow}>
            <Text style={styles.label}>X:</Text>
            <TextInput
              style={styles.input}
              value={x}
              onChangeText={setX}
              placeholder="e.g., 3"
              keyboardType="numeric"
              editable={!loading}
            />
          </View>

          <View style={styles.inputRow}>
            <Text style={styles.label}>Y:</Text>
            <TextInput
              style={styles.input}
              value={y}
              onChangeText={setY}
              placeholder="e.g., 5"
              keyboardType="numeric"
              editable={!loading}
            />
          </View>

          <View style={styles.inputRow}>
            <Text style={styles.label}>Z:</Text>
            <TextInput
              style={styles.input}
              value={z}
              onChangeText={setZ}
              placeholder="e.g., 0.5"
              keyboardType="numeric"
              editable={!loading}
            />
          </View>
        </View>
      )}

      {!useCustomPosition && (
        <Text style={styles.helperText}>
          Auto-grid positioning will be used (drone will spawn at next available grid slot)
        </Text>
      )}

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleSpawn}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Spawn Drone</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 16,
    color: '#1f2937',
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  switchLabel: {
    fontSize: 16,
    color: '#4b5563',
    fontWeight: '500',
  },
  positionInputs: {
    marginBottom: 16,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  label: {
    width: 40,
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
  input: {
    flex: 1,
    height: 44,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 6,
    paddingHorizontal: 12,
    fontSize: 16,
    backgroundColor: '#f9fafb',
  },
  helperText: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 16,
    fontStyle: 'italic',
  },
  button: {
    backgroundColor: '#3b82f6',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  buttonDisabled: {
    backgroundColor: '#9ca3af',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
});
