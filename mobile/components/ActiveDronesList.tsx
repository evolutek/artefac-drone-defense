import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Pressable,
} from 'react-native';
import api, { Drone } from '../services/api';
import { showConfirmationAlert, showAlert } from '../utils/confirmationAlert';

export default function ActiveDronesList({ refreshTrigger }: { refreshTrigger?: number }) {
  const [drones, setDrones] = useState<Drone[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [removingDrone, setRemovingDrone] = useState<number | null>(null);
  const [selectedDrones, setSelectedDrones] = useState<Set<number>>(new Set());
  const [deletingBatch, setDeletingBatch] = useState(false);

  const loadDrones = async () => {
    try {
      setLoading(true);
      const activeDrones = await api.getActiveDrones();
      setDrones(activeDrones);
      // Clear selection when reloading (in case selected drones were deleted)
      setSelectedDrones(new Set());
    } catch (error: any) {
      console.error('Failed to load drones:', error);
      showAlert('Error', 'Failed to load active drones');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRemove = async (drone: Drone) => {
    console.log('[ActiveDronesList] handleRemove called for:', drone.drone_id);

    await showConfirmationAlert({
      title: 'Confirm Removal',
      message: `Are you sure you want to remove ${drone.drone_id}?`,
      confirmText: 'Remove',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        console.log('[ActiveDronesList] Remove confirmed - starting despawn...');
        try {
          setRemovingDrone(drone.drone_num);
          console.log('[ActiveDronesList] Calling api.despawnDrone for drone_num:', drone.drone_num);
          const result = await api.despawnDrone(drone.drone_num);
          console.log('[ActiveDronesList] API response:', result);

          if (result.success) {
            console.log('[ActiveDronesList] Despawn successful');
            showAlert('Success', result.message);
            await loadDrones(); // Refresh list
          } else {
            console.error('[ActiveDronesList] Despawn failed:', result.message);
            showAlert('Error', result.message);
          }
        } catch (error: any) {
          console.error('[ActiveDronesList] Exception during despawn:', error);
          showAlert('Error', error.message || 'Failed to remove drone');
        } finally {
          setRemovingDrone(null);
        }
      },
      onCancel: () => console.log('[ActiveDronesList] Removal cancelled'),
    });
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadDrones();
  };

  const toggleDroneSelection = (droneNum: number) => {
    setSelectedDrones((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(droneNum)) {
        newSet.delete(droneNum);
      } else {
        newSet.add(droneNum);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedDrones(new Set(drones.map((d) => d.drone_num)));
  };

  const deselectAll = () => {
    setSelectedDrones(new Set());
  };

  const handleBatchDelete = async () => {
    if (selectedDrones.size === 0) return;

    await showConfirmationAlert({
      title: 'Confirm Batch Removal',
      message: `Are you sure you want to remove ${selectedDrones.size} drone(s)?`,
      confirmText: 'Remove All',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        try {
          setDeletingBatch(true);
          const droneNums = Array.from(selectedDrones);
          const result = await api.batchDespawnDrones(droneNums);

          if (result.success) {
            showAlert('Success', result.message);
          } else {
            // Show detailed results if some failed
            const failedDrones = result.results
              .filter((r) => !r.success)
              .map((r) => `Drone ${r.drone_num}: ${r.message}`)
              .join('\n');
            showAlert(
              'Partial Success',
              `${result.message}\n\nFailed:\n${failedDrones}`
            );
          }

          await loadDrones(); // Refresh list
        } catch (error: any) {
          showAlert('Error', error.message || 'Failed to remove drones');
        } finally {
          setDeletingBatch(false);
        }
      },
    });
  };

  useEffect(() => {
    loadDrones();
  }, [refreshTrigger]);

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.loadingText}>Loading drones...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Active Drones</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{drones.length}</Text>
        </View>
      </View>

      {drones.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No active drones</Text>
          <Text style={styles.emptySubtext}>Spawn a drone to get started</Text>
        </View>
      ) : (
        <>
          {/* Selection Toolbar */}
          <View style={styles.toolbar}>
            <View style={styles.toolbarLeft}>
              <TouchableOpacity
                style={styles.toolbarButton}
                onPress={selectAll}
                disabled={deletingBatch}
              >
                <Text style={styles.toolbarButtonText}>Select All</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.toolbarButton}
                onPress={deselectAll}
                disabled={deletingBatch}
              >
                <Text style={styles.toolbarButtonText}>Deselect All</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              style={[
                styles.deleteSelectedButton,
                (selectedDrones.size === 0 || deletingBatch) && styles.deleteSelectedButtonDisabled,
              ]}
              onPress={handleBatchDelete}
              disabled={selectedDrones.size === 0 || deletingBatch}
            >
              {deletingBatch ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.deleteSelectedButtonText}>
                  Delete ({selectedDrones.size})
                </Text>
              )}
            </TouchableOpacity>
          </View>

          <FlatList
            data={drones}
            keyExtractor={(item) => item.drone_id}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            renderItem={({ item }) => {
              const isSelected = selectedDrones.has(item.drone_num);
              return (
                <View
                  style={[styles.droneCard, isSelected && styles.droneCardSelected]}
                >
                  {/* Checkbox */}
                  <Pressable
                    onPress={() => toggleDroneSelection(item.drone_num)}
                    style={styles.checkboxContainer}
                    disabled={deletingBatch || removingDrone === item.drone_num}
                  >
                    <View style={[styles.checkbox, isSelected && styles.checkboxChecked]}>
                      {isSelected && <Text style={styles.checkmark}>✓</Text>}
                    </View>
                  </Pressable>

                  {/* Drone Info */}
                  <View style={styles.droneInfo}>
                    <Text style={styles.droneId}>{item.drone_id}</Text>
                    <Text style={styles.droneModel}>{item.model_name}</Text>
                    {item.position && (
                      <Text style={styles.dronePosition}>
                        Position: ({item.position.x.toFixed(1)}, {item.position.y.toFixed(1)},{' '}
                        {item.position.z.toFixed(1)})
                      </Text>
                    )}
                    {item.spawned_at && (
                      <Text style={styles.droneTime}>
                        Spawned: {new Date(item.spawned_at).toLocaleTimeString()}
                      </Text>
                    )}
                  </View>

                  {/* Individual Remove Button */}
                  <TouchableOpacity
                    style={[
                      styles.removeButton,
                      (removingDrone === item.drone_num || deletingBatch) &&
                        styles.removeButtonDisabled,
                    ]}
                    onPress={() => handleRemove(item)}
                    disabled={removingDrone === item.drone_num || deletingBatch}
                  >
                    {removingDrone === item.drone_num ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <Text style={styles.removeButtonText}>Remove</Text>
                    )}
                  </TouchableOpacity>
                </View>
              );
            }}
          />
        </>
      )}
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
  loadingContainer: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#6b7280',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
  },
  badge: {
    backgroundColor: '#3b82f6',
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    minWidth: 28,
    alignItems: 'center',
  },
  badgeText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: 4,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#9ca3af',
  },
  toolbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  toolbarLeft: {
    flexDirection: 'row',
    gap: 8,
  },
  toolbarButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#f3f4f6',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#d1d5db',
  },
  toolbarButtonText: {
    fontSize: 13,
    color: '#374151',
    fontWeight: '600',
  },
  deleteSelectedButton: {
    backgroundColor: '#ef4444',
    borderRadius: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    minWidth: 100,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 32,
  },
  deleteSelectedButtonDisabled: {
    backgroundColor: '#f87171',
    opacity: 0.5,
  },
  deleteSelectedButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  droneCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  droneCardSelected: {
    backgroundColor: '#dbeafe',
    borderColor: '#3b82f6',
    borderWidth: 2,
  },
  checkboxContainer: {
    marginRight: 12,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: '#9ca3af',
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxChecked: {
    backgroundColor: '#3b82f6',
    borderColor: '#3b82f6',
  },
  checkmark: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  droneInfo: {
    flex: 1,
  },
  droneId: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 4,
  },
  droneModel: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 2,
  },
  dronePosition: {
    fontSize: 13,
    color: '#9ca3af',
    fontFamily: 'monospace',
  },
  droneTime: {
    fontSize: 12,
    color: '#9ca3af',
    marginTop: 4,
  },
  removeButton: {
    backgroundColor: '#ef4444',
    borderRadius: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    minWidth: 80,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 36,
  },
  removeButtonDisabled: {
    backgroundColor: '#f87171',
  },
  removeButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
});
