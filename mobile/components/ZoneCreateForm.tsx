import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import api from '../services/api';

type ZoneType = 'jamming' | 'no-fly' | 'restricted';

export default function ZoneCreateForm({ onCreateSuccess }: { onCreateSuccess?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState('');
  const [selectedType, setSelectedType] = useState<ZoneType>('jamming');
  const [centerX, setCenterX] = useState('');
  const [centerY, setCenterY] = useState('');
  const [centerZ, setCenterZ] = useState('0');
  const [radius, setRadius] = useState('');

  const zoneTypes: Array<{ type: ZoneType; label: string; color: string; description: string }> = [
    {
      type: 'jamming',
      label: 'Jamming',
      color: '#ef4444',
      description: 'GPS/Communication jamming area',
    },
    { type: 'no-fly', label: 'No-Fly', color: '#f97316', description: 'No-fly zone' },
    { type: 'restricted', label: 'Restricted', color: '#eab308', description: 'Restricted area' },
  ];

  const handleCreate = async () => {
    // Validation
    if (!name.trim()) {
      Alert.alert('Validation Error', 'Please enter a zone name');
      return;
    }

    const x = parseFloat(centerX);
    const y = parseFloat(centerY);
    const z = parseFloat(centerZ);
    const r = parseFloat(radius);

    if (isNaN(x) || isNaN(y) || isNaN(z)) {
      Alert.alert('Validation Error', 'Please enter valid numbers for center coordinates');
      return;
    }

    if (isNaN(r) || r <= 0) {
      Alert.alert('Validation Error', 'Please enter a valid radius (> 0)');
      return;
    }

    try {
      setLoading(true);

      const result = await api.createZone({
        name: name.trim(),
        type: selectedType,
        center: { x, y, z },
        radius: r,
      });

      if (result.success) {
        Alert.alert('Success', result.message);
        // Reset form
        setName('');
        setCenterX('');
        setCenterY('');
        setCenterZ('0');
        setRadius('');
        setSelectedType('jamming');
        onCreateSuccess?.();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create zone');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Create Exclusion Zone</Text>

      {/* Zone Name */}
      <View style={styles.formGroup}>
        <Text style={styles.label}>Zone Name</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
          placeholder="e.g., Jamming Zone Alpha"
          editable={!loading}
        />
      </View>

      {/* Zone Type */}
      <View style={styles.formGroup}>
        <Text style={styles.label}>Zone Type</Text>
        <View style={styles.typeButtons}>
          {zoneTypes.map(({ type, label, color, description }) => (
            <TouchableOpacity
              key={type}
              style={[
                styles.typeButton,
                selectedType === type && { ...styles.typeButtonActive, borderColor: color },
              ]}
              onPress={() => setSelectedType(type)}
              disabled={loading}
            >
              <View style={[styles.typeColorIndicator, { backgroundColor: color }]} />
              <View style={styles.typeButtonContent}>
                <Text
                  style={[
                    styles.typeButtonLabel,
                    selectedType === type && styles.typeButtonLabelActive,
                  ]}
                >
                  {label}
                </Text>
                <Text style={styles.typeButtonDescription}>{description}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Center Coordinates */}
      <View style={styles.formGroup}>
        <Text style={styles.label}>Center Position</Text>
        <View style={styles.coordinateRow}>
          <View style={styles.coordinateInput}>
            <Text style={styles.coordinateLabel}>X</Text>
            <TextInput
              style={styles.input}
              value={centerX}
              onChangeText={setCenterX}
              placeholder="10"
              keyboardType="numeric"
              editable={!loading}
            />
          </View>
          <View style={styles.coordinateInput}>
            <Text style={styles.coordinateLabel}>Y</Text>
            <TextInput
              style={styles.input}
              value={centerY}
              onChangeText={setCenterY}
              placeholder="10"
              keyboardType="numeric"
              editable={!loading}
            />
          </View>
          <View style={styles.coordinateInput}>
            <Text style={styles.coordinateLabel}>Z</Text>
            <TextInput
              style={styles.input}
              value={centerZ}
              onChangeText={setCenterZ}
              placeholder="0"
              keyboardType="numeric"
              editable={!loading}
            />
          </View>
        </View>
      </View>

      {/* Radius */}
      <View style={styles.formGroup}>
        <Text style={styles.label}>Radius (meters)</Text>
        <TextInput
          style={styles.input}
          value={radius}
          onChangeText={setRadius}
          placeholder="e.g., 15"
          keyboardType="numeric"
          editable={!loading}
        />
      </View>

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleCreate}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Create Zone</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
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
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  input: {
    height: 44,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 6,
    paddingHorizontal: 12,
    fontSize: 16,
    backgroundColor: '#f9fafb',
  },
  typeButtons: {
    gap: 8,
  },
  typeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderWidth: 2,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    backgroundColor: '#f9fafb',
  },
  typeButtonActive: {
    backgroundColor: '#eff6ff',
    borderWidth: 2,
  },
  typeColorIndicator: {
    width: 24,
    height: 24,
    borderRadius: 12,
    marginRight: 12,
  },
  typeButtonContent: {
    flex: 1,
  },
  typeButtonLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#6b7280',
  },
  typeButtonLabelActive: {
    color: '#1f2937',
  },
  typeButtonDescription: {
    fontSize: 13,
    color: '#9ca3af',
    marginTop: 2,
  },
  coordinateRow: {
    flexDirection: 'row',
    gap: 8,
  },
  coordinateInput: {
    flex: 1,
  },
  coordinateLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: 4,
  },
  button: {
    backgroundColor: '#3b82f6',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    marginTop: 8,
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
