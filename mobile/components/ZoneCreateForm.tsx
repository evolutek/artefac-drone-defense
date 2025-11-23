import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import api from '../services/api';

type ZoneType = 'jamming' | 'no-fly' | 'restricted';

export default function ZoneCreateForm({ onCreateSuccess }: { onCreateSuccess?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState('');
  const [nameError, setNameError] = useState('');
  const [selectedType, setSelectedType] = useState<ZoneType>('jamming');
  const [centerX, setCenterX] = useState('10');
  const [centerY, setCenterY] = useState('10');
  const [centerZ, setCenterZ] = useState('0');
  const [radius, setRadius] = useState('15');

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

  // Auto-generate zone name and position on component mount
  useEffect(() => {
    const generateDefaults = async () => {
      try {
        const zones = await api.getActiveZones();
        const nextNumber = zones.length + 1;
        setName(`Zone ${nextNumber}`);

        // Grid positioning: 20m spacing to avoid overlap (radius = 15m default)
        const gridX = zones.length * 20;
        setCenterX(gridX.toString());
      } catch (error) {
        console.error('Failed to fetch zones for defaults generation:', error);
        setName('Zone 1'); // Fallback default
        setCenterX('0'); // Fallback position
      }
    };

    generateDefaults();
  }, []);

  const handleCreate = async () => {
    // Validation
    if (!name.trim()) {
      setNameError('Zone name is required');
      Alert.alert('Validation Error', 'Please enter a zone name');
      return;
    }

    setNameError(''); // Clear error if name is valid

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

        // Generate next zone name and position
        try {
          const zones = await api.getActiveZones();
          const nextNumber = zones.length + 1;
          setName(`Zone ${nextNumber}`);

          // Grid positioning: 20m spacing to avoid overlap
          const gridX = zones.length * 20;
          setCenterX(gridX.toString());
        } catch (error) {
          console.error('Failed to fetch zones for name generation:', error);
          // Extract current number from name (e.g., "Zone 3" -> 3)
          const currentNumber = parseInt(name.match(/\d+/)?.[0] || '1');
          setName(`Zone ${currentNumber + 1}`); // Increment from current name

          // Increment position as well
          const currentX = parseFloat(centerX) || 0;
          setCenterX((currentX + 20).toString());
        }

        // Reset form (keep name and position auto-generated above)
        setNameError('');
        setCenterY('10');
        setCenterZ('0');
        setRadius('15');
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
    <View style={styles.container}>
      <Text style={styles.title}>Create Exclusion Zone</Text>

      {/* Zone Name */}
      <View style={styles.formGroup}>
        <Text style={styles.label}>Zone Name</Text>
        <TextInput
          style={[styles.input, nameError ? styles.inputError : null]}
          value={name}
          onChangeText={(text) => {
            setName(text);
            if (nameError) setNameError(''); // Clear error when user types
          }}
          placeholder="e.g., Jamming Zone Alpha"
          editable={!loading}
        />
        {nameError ? <Text style={styles.errorText}>{nameError}</Text> : null}
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
  inputError: {
    borderColor: '#ef4444',
    borderWidth: 2,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 13,
    marginTop: 4,
    marginLeft: 4,
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
