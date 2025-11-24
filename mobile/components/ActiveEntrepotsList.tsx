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
import api, { Entrepot } from '../services/api';
import { showConfirmationAlert, showAlert } from '../utils/confirmationAlert';

export default function ActiveEntrepotsList({ refreshTrigger }: { refreshTrigger?: number }) {
  const [entrepots, setEntrepots] = useState<Entrepot[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [deletingEntrepot, setDeletingEntrepot] = useState<string | null>(null);
  const [selectedEntrepots, setSelectedEntrepots] = useState<Set<string>>(new Set());
  const [deletingBatch, setDeletingBatch] = useState(false);

  const loadEntrepots = async () => {
    try {
      setLoading(true);
      const activeEntrepots = await api.getEntrepots();
      setEntrepots(activeEntrepots);
      // Clear selection when reloading (in case selected entrepots were deleted)
      setSelectedEntrepots(new Set());
    } catch (error: any) {
      console.error('Failed to load entrepots:', error);
      showAlert('Error', 'Failed to load active warehouses');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleDelete = async (entrepot: Entrepot) => {
    console.log('[ActiveEntrepotsList] handleDelete called for:', entrepot.entrepot_id, entrepot.name);

    await showConfirmationAlert({
      title: 'Confirm Deletion',
      message: `Are you sure you want to delete warehouse "${entrepot.name}"?`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        console.log('[ActiveEntrepotsList] Delete confirmed - starting deletion...');
        try {
          setDeletingEntrepot(entrepot.entrepot_id);
          console.log('[ActiveEntrepotsList] Calling api.deleteEntrepot for entrepot_id:', entrepot.entrepot_id);
          const result = await api.deleteEntrepot(entrepot.entrepot_id);
          console.log('[ActiveEntrepotsList] API response:', result);

          if (result.success) {
            console.log('[ActiveEntrepotsList] Deletion successful');
            showAlert('Success', result.message);
            await loadEntrepots(); // Refresh list
          } else {
            console.error('[ActiveEntrepotsList] Deletion failed:', result.message);
            showAlert('Error', result.message);
          }
        } catch (error: any) {
          console.error('[ActiveEntrepotsList] Exception during deletion:', error);
          showAlert('Error', error.message || 'Failed to delete warehouse');
        } finally {
          setDeletingEntrepot(null);
        }
      },
      onCancel: () => console.log('[ActiveEntrepotsList] Deletion cancelled'),
    });
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadEntrepots();
  };

  const toggleEntrepotSelection = (entrepotId: string) => {
    setSelectedEntrepots((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(entrepotId)) {
        newSet.delete(entrepotId);
      } else {
        newSet.add(entrepotId);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedEntrepots(new Set(entrepots.map((e) => e.entrepot_id)));
  };

  const deselectAll = () => {
    setSelectedEntrepots(new Set());
  };

  const handleBatchDelete = async () => {
    if (selectedEntrepots.size === 0) return;

    await showConfirmationAlert({
      title: 'Confirm Batch Deletion',
      message: `Are you sure you want to delete ${selectedEntrepots.size} warehouse(s)?`,
      confirmText: 'Delete All',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        try {
          setDeletingBatch(true);
          const entrepotIds = Array.from(selectedEntrepots);
          const result = await api.batchDeleteEntrepots(entrepotIds);

          if (result.success) {
            showAlert('Success', result.message);
          } else {
            // Show detailed results if some failed
            const failedEntrepots = result.results
              .filter((r) => !r.success)
              .map((r) => `Entrepot ${r.entrepot_id}: ${r.message}`)
              .join('\n');
            showAlert(
              'Partial Success',
              `${result.message}\n\nFailed:\n${failedEntrepots}`
            );
          }

          await loadEntrepots(); // Refresh list
        } catch (error: any) {
          showAlert('Error', error.message || 'Failed to delete warehouses');
        } finally {
          setDeletingBatch(false);
        }
      },
    });
  };

  useEffect(() => {
    loadEntrepots();
  }, [refreshTrigger]);

  const getEntrepotColor = (type: string): string => {
    switch (type) {
      case 'medecines':
        return '#10b981'; // green
      case 'ammunition':
        return '#ef4444'; // red
      case 'equipment':
        return '#3b82f6'; // blue
      case 'food':
        return '#f97316'; // orange
      case 'blood':
        return '#dc2626'; // dark red
      default:
        return '#6b7280'; // gray (custom/general)
    }
  };

  const getEntrepotTypeLabel = (type: string): string => {
    switch (type) {
      case 'medecines':
        return 'Medecines';
      case 'ammunition':
        return 'Ammunition';
      case 'equipment':
        return 'Equipment';
      case 'food':
        return 'Food';
      case 'blood':
        return 'Blood';
      default:
        return type.charAt(0).toUpperCase() + type.slice(1); // Capitalize first letter
    }
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.loadingText}>Loading warehouses...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Active Warehouses</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{entrepots.length}</Text>
        </View>
      </View>

      {entrepots.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No active warehouses</Text>
          <Text style={styles.emptySubtext}>Create a warehouse to get started</Text>
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
                (selectedEntrepots.size === 0 || deletingBatch) && styles.deleteSelectedButtonDisabled,
              ]}
              onPress={handleBatchDelete}
              disabled={selectedEntrepots.size === 0 || deletingBatch}
            >
              {deletingBatch ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.deleteSelectedButtonText}>
                  Delete ({selectedEntrepots.size})
                </Text>
              )}
            </TouchableOpacity>
          </View>

          <FlatList
            data={entrepots}
            keyExtractor={(item) => item.entrepot_id}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            renderItem={({ item }) => {
              const isSelected = selectedEntrepots.has(item.entrepot_id);
              return (
                <View
                  style={[styles.entrepotCard, isSelected && styles.entrepotCardSelected]}
                >
                  {/* Checkbox */}
                  <Pressable
                    onPress={() => toggleEntrepotSelection(item.entrepot_id)}
                    style={styles.checkboxContainer}
                    disabled={deletingBatch || deletingEntrepot === item.entrepot_id}
                  >
                    <View style={[styles.checkbox, isSelected && styles.checkboxChecked]}>
                      {isSelected && <Text style={styles.checkmark}>✓</Text>}
                    </View>
                  </Pressable>

                  {/* Entrepot Indicator */}
                  <View style={styles.entrepotIndicator}>
                    <View
                      style={[styles.entrepotColorDot, { backgroundColor: getEntrepotColor(item.type) }]}
                    />
                  </View>

                  <View style={styles.entrepotInfo}>
                    <Text style={styles.entrepotName}>{item.name}</Text>
                    <View style={[styles.typeTag, { backgroundColor: `${getEntrepotColor(item.type)}20` }]}>
                      <Text style={[styles.typeTagText, { color: getEntrepotColor(item.type) }]}>
                        {getEntrepotTypeLabel(item.type)}
                      </Text>
                    </View>
                    {item.position ? (
                      <Text style={styles.entrepotDetails}>
                        Position: ({item.position.x.toFixed(1)}, {item.position.y.toFixed(1)},{' '}
                        {item.position.z.toFixed(1)})
                      </Text>
                    ) : (
                      <Text style={[styles.entrepotDetails, styles.unknownText]}>
                        Position: Unknown
                      </Text>
                    )}
                    {item.created_at && (
                      <Text style={styles.entrepotTime}>
                        Created: {new Date(item.created_at).toLocaleTimeString()}
                      </Text>
                    )}
                  </View>

                  {/* Individual Delete Button */}
                  <TouchableOpacity
                    style={[
                      styles.deleteButton,
                      (deletingEntrepot === item.entrepot_id || deletingBatch) &&
                        styles.deleteButtonDisabled,
                    ]}
                    onPress={() => handleDelete(item)}
                    disabled={deletingEntrepot === item.entrepot_id || deletingBatch}
                  >
                    {deletingEntrepot === item.entrepot_id ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <Text style={styles.deleteButtonText}>Delete</Text>
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
  entrepotCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  entrepotCardSelected: {
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
  entrepotIndicator: {
    marginRight: 12,
  },
  entrepotColorDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
  },
  entrepotInfo: {
    flex: 1,
  },
  entrepotName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 4,
  },
  typeTag: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    marginBottom: 6,
  },
  typeTagText: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  entrepotDetails: {
    fontSize: 13,
    color: '#6b7280',
    fontFamily: 'monospace',
    marginBottom: 2,
  },
  unknownText: {
    fontStyle: 'italic',
    color: '#9ca3af',
  },
  entrepotTime: {
    fontSize: 12,
    color: '#9ca3af',
    marginTop: 4,
  },
  deleteButton: {
    backgroundColor: '#ef4444',
    borderRadius: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    minWidth: 70,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 36,
  },
  deleteButtonDisabled: {
    backgroundColor: '#f87171',
  },
  deleteButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
});
