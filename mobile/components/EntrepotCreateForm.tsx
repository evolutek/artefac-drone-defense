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
import api from '../services/api';

type EntrepotType = 'medecines' | 'ammunition' | 'food' | 'equipment' | 'blood' | 'custom';

export default function EntrepotCreateForm({ onCreateSuccess }: { onCreateSuccess?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState('');
  const [nameError, setNameError] = useState('');
  const [selectedType, setSelectedType] = useState<EntrepotType>('medecines');
  const [customType, setCustomType] = useState('');
  const [customTypeError, setCustomTypeError] = useState('');
  const [useCustomPosition, setUseCustomPosition] = useState(false);
  const [x, setX] = useState('');
  const [y, setY] = useState('');
  const [z, setZ] = useState('0');

  const entrepotTypes: Array<{ type: EntrepotType; label: string; color: string; description: string }> = [
    {
      type: 'medecines',
      label: 'Medecines',
      color: '#10b981',
      description: 'Medical supplies warehouse',
    },
    {
      type: 'ammunition',
      label: 'Ammunition',
      color: '#ef4444',
      description: 'Ammunition storage',
    },
    {
      type: 'food',
      label: 'Food',
      color: '#f97316',
      description: 'Food storage',
    },
    {
      type: 'equipment',
      label: 'Equipment',
      color: '#3b82f6',
      description: 'Equipment depot',
    },
    {
      type: 'blood',
      label: 'Blood',
      color: '#dc2626',
      description: 'Blood bank storage',
    },
    {
      type: 'custom',
      label: 'Custom',
      color: '#6b7280',
      description: 'Custom warehouse type',
    },
  ];

  // Auto-generate entrepot name and position on component mount
  useEffect(() => {
    const generateDefaults = async () => {
      try {
        const entrepots = await api.getEntrepots();
        const nextNumber = entrepots.length + 1;
        setName(`Warehouse ${nextNumber}`);

        // Grid positioning: 20m spacing to avoid overlap
        const gridX = entrepots.length * 20;
        setX(gridX.toString());
      } catch (error) {
        console.error('Failed to fetch entrepots for defaults generation:', error);
        setName('Warehouse 1'); // Fallback default
        setX('0'); // Fallback position
      }
    };

    generateDefaults();
  }, []);

  const handleCreate = async () => {
    // Validation
    if (!name.trim()) {
      setNameError('Warehouse name is required');
      Alert.alert('Validation Error', 'Please enter a warehouse name');
      return;
    }
    setNameError('');

    // Validate custom type if selected
    if (selectedType === 'custom') {
      if (!customType.trim()) {
        setCustomTypeError('Custom type is required');
        Alert.alert('Validation Error', 'Please enter a custom warehouse type');
        return;
      }
      setCustomTypeError('');
    }

    // Determine final type
    const finalType = selectedType === 'custom' ? customType.trim() : selectedType;

    // Position validation and calculation
    let finalX: number, finalY: number, finalZ: number;

    if (useCustomPosition) {
      // Validate custom coordinates
      finalX = parseFloat(x);
      finalY = parseFloat(y);
      finalZ = parseFloat(z);

      if (isNaN(finalX) || isNaN(finalY) || isNaN(finalZ)) {
        Alert.alert('Validation Error', 'Please enter valid numbers for coordinates');
        return;
      }
    } else {
      // Auto-grid positioning
      try {
        const entrepots = await api.getEntrepots();
        const gridX = entrepots.length * 20; // 20m spacing
        finalX = gridX;
        finalY = 0;
        finalZ = 0;
      } catch (error) {
        console.error('Failed to fetch entrepots for grid positioning:', error);
        // Fallback to 0,0,0
        finalX = 0;
        finalY = 0;
        finalZ = 0;
      }
    }

    try {
      setLoading(true);

      const result = await api.createEntrepot({
        name: name.trim(),
        type: finalType,
        position: { x: finalX, y: finalY, z: finalZ },
      });

      if (result.success) {
        Alert.alert('Success', result.message);

        // Generate next warehouse name and position
        try {
          const entrepots = await api.getEntrepots();
          const nextNumber = entrepots.length + 1;
          setName(`Warehouse ${nextNumber}`);

          // Grid positioning: 20m spacing
          const gridX = entrepots.length * 20;
          setX(gridX.toString());
        } catch (error) {
          console.error('Failed to fetch entrepots for name generation:', error);
          // Extract current number from name
          const currentNumber = parseInt(name.match(/\d+/)?.[0] || '1');
          setName(`Warehouse ${currentNumber + 1}`);

          // Increment position
          const currentX = parseFloat(x) || 0;
          setX((currentX + 20).toString());
        }

        // Reset form
        setNameError('');
        setCustomType('');
        setCustomTypeError('');
        setY('0');
        setZ('0');
        setSelectedType('medecines');
        setUseCustomPosition(false);
        onCreateSuccess?.();
      } else {
        Alert.alert('Error', result.message);
      }
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create warehouse');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Create Warehouse</Text>

      {/* Warehouse Name */}
      <View style={styles.formGroup}>
        <Text style={styles.label}>Warehouse Name</Text>
        <TextInput
          style={[styles.input, nameError ? styles.inputError : null]}
          value={name}
          onChangeText={(text) => {
            setName(text);
            if (nameError) setNameError('');
          }}
          placeholder="e.g., Main Warehouse"
          editable={!loading}
        />
        {nameError ? <Text style={styles.errorText}>{nameError}</Text> : null}
      </View>

      {/* Warehouse Type */}
      <View style={styles.formGroup}>
        <Text style={styles.label}>Warehouse Type</Text>
        <View style={styles.typeButtons}>
          {entrepotTypes.map(({ type, label, color, description }) => (
            <TouchableOpacity
              key={type}
              style={[
                styles.typeButton,
                selectedType === type && { ...styles.typeButtonActive, borderColor: color },
              ]}
              onPress={() => {
                setSelectedType(type);
                if (type !== 'custom' && customTypeError) {
                  setCustomTypeError('');
                }
              }}
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

      {/* Custom Type Input (conditional) */}
      {selectedType === 'custom' && (
        <View style={styles.formGroup}>
          <Text style={styles.label}>Custom Type Name</Text>
          <TextInput
            style={[styles.input, customTypeError ? styles.inputError : null]}
            value={customType}
            onChangeText={(text) => {
              setCustomType(text);
              if (customTypeError) setCustomTypeError('');
            }}
            placeholder="e.g., Construction Materials"
            editable={!loading}
          />
          {customTypeError ? <Text style={styles.errorText}>{customTypeError}</Text> : null}
        </View>
      )}

      {/* Position Toggle */}
      <View style={styles.formGroup}>
        <View style={styles.switchRow}>
          <Text style={styles.label}>Use Custom Position</Text>
          <Switch
            value={useCustomPosition}
            onValueChange={setUseCustomPosition}
            disabled={loading}
          />
        </View>
        {!useCustomPosition && (
          <Text style={styles.helperText}>Auto-grid: Warehouses spaced 20m apart</Text>
        )}
      </View>

      {/* Position Coordinates (conditional) */}
      {useCustomPosition && (
        <View style={styles.formGroup}>
          <Text style={styles.label}>Position</Text>
          <View style={styles.coordinateRow}>
            <View style={styles.coordinateInput}>
              <Text style={styles.coordinateLabel}>X</Text>
              <TextInput
                style={styles.input}
                value={x}
                onChangeText={setX}
                placeholder="0"
                keyboardType="numeric"
                editable={!loading}
              />
            </View>
            <View style={styles.coordinateInput}>
              <Text style={styles.coordinateLabel}>Y</Text>
              <TextInput
                style={styles.input}
                value={y}
                onChangeText={setY}
                placeholder="0"
                keyboardType="numeric"
                editable={!loading}
              />
            </View>
            <View style={styles.coordinateInput}>
              <Text style={styles.coordinateLabel}>Z</Text>
              <TextInput
                style={styles.input}
                value={z}
                onChangeText={setZ}
                placeholder="0"
                keyboardType="numeric"
                editable={!loading}
              />
            </View>
          </View>
        </View>
      )}

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleCreate}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Create Warehouse</Text>
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
  helperText: {
    fontSize: 13,
    color: '#6b7280',
    marginTop: 4,
    fontStyle: 'italic',
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
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
