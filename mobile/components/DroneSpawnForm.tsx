import React, { useState, useEffect } from 'react';
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
import { Picker } from '@react-native-picker/picker';
import api, { DroneModel } from '../services/api';

export default function DroneSpawnForm({ onSpawnSuccess }: { onSpawnSuccess?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [useCustomPosition, setUseCustomPosition] = useState(false);
  const [x, setX] = useState('');
  const [y, setY] = useState('');
  const [z, setZ] = useState('0.5');
  const [availableModels, setAvailableModels] = useState<DroneModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gz_x500');
  const [loadingModels, setLoadingModels] = useState(true);

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const modelsResponse = await api.getAvailableModels();
        setAvailableModels(modelsResponse.models);
        setSelectedModel(modelsResponse.default_model);
      } catch (error) {
        console.error('Failed to fetch models:', error);
        Alert.alert('Warning', 'Failed to load drone models. Using default (x500).');
      } finally {
        setLoadingModels(false);
      }
    };

    fetchModels();
  }, []);

  const handleSpawn = async () => {
    try {
      setLoading(true);

      let request: any = { model: selectedModel };

      if (useCustomPosition) {
        // Validate coordinates
        const xNum = parseFloat(x);
        const yNum = parseFloat(y);
        const zNum = parseFloat(z);

        if (isNaN(xNum) || isNaN(yNum) || isNaN(zNum)) {
          Alert.alert('Invalid Input', 'Please enter valid numbers for coordinates');
          return;
        }

        request.x = xNum;
        request.y = yNum;
        request.z = zNum;
      }

      const result = await api.spawnDrone(request);

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

      {/* Model Selector */}
      <View style={styles.modelSection}>
        <Text style={styles.modelLabel}>Drone Model</Text>
        {loadingModels ? (
          <ActivityIndicator size="small" color="#3b82f6" />
        ) : (
          <>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={selectedModel}
                onValueChange={(itemValue) => setSelectedModel(itemValue)}
                style={styles.picker}
                enabled={!loading}
              >
                {availableModels.map((model) => (
                  <Picker.Item
                    key={model.id}
                    label={model.description}
                    value={model.id}
                  />
                ))}
              </Picker>
            </View>
            {selectedModel && (
              <Text style={styles.modelDetails}>
                {availableModels.find((m) => m.id === selectedModel)?.details}
              </Text>
            )}
          </>
        )}
      </View>

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
  modelSection: {
    marginBottom: 16,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 6,
    backgroundColor: '#f9fafb',
    marginTop: 8,
    overflow: 'hidden',
  },
  picker: {
    height: 50,
  },
  modelDetails: {
    fontSize: 13,
    color: '#6b7280',
    marginTop: 8,
    fontStyle: 'italic',
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
  modelLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
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
