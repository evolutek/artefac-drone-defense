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
import api, { Zone } from '../services/api';
import { showConfirmationAlert, showAlert } from '../utils/confirmationAlert';

export default function ActiveZonesList({ refreshTrigger }: { refreshTrigger?: number }) {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [deletingZone, setDeletingZone] = useState<string | null>(null);
  const [selectedZones, setSelectedZones] = useState<Set<string>>(new Set());
  const [deletingBatch, setDeletingBatch] = useState(false);

  const loadZones = async () => {
    try {
      setLoading(true);
      const activeZones = await api.getZones();
      setZones(activeZones);
      // Clear selection when reloading (in case selected zones were deleted)
      setSelectedZones(new Set());
    } catch (error: any) {
      console.error('Failed to load zones:', error);
      showAlert('Error', 'Failed to load active zones');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleDelete = async (zone: Zone) => {
    console.log('[ActiveZonesList] handleDelete called for:', zone.zone_id, zone.name);

    await showConfirmationAlert({
      title: 'Confirm Deletion',
      message: `Are you sure you want to delete zone "${zone.name}"?`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        console.log('[ActiveZonesList] Delete confirmed - starting deletion...');
        try {
          setDeletingZone(zone.zone_id);
          console.log('[ActiveZonesList] Calling api.deleteZone for zone_id:', zone.zone_id);
          const result = await api.deleteZone(zone.zone_id);
          console.log('[ActiveZonesList] API response:', result);

          if (result.success) {
            console.log('[ActiveZonesList] Deletion successful');
            showAlert('Success', result.message);
            await loadZones(); // Refresh list
          } else {
            console.error('[ActiveZonesList] Deletion failed:', result.message);
            showAlert('Error', result.message);
          }
        } catch (error: any) {
          console.error('[ActiveZonesList] Exception during deletion:', error);
          showAlert('Error', error.message || 'Failed to delete zone');
        } finally {
          setDeletingZone(null);
        }
      },
      onCancel: () => console.log('[ActiveZonesList] Deletion cancelled'),
    });
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadZones();
  };

  const toggleZoneSelection = (zoneId: string) => {
    setSelectedZones((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(zoneId)) {
        newSet.delete(zoneId);
      } else {
        newSet.add(zoneId);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedZones(new Set(zones.map((z) => z.zone_id)));
  };

  const deselectAll = () => {
    setSelectedZones(new Set());
  };

  const handleBatchDelete = async () => {
    if (selectedZones.size === 0) return;

    await showConfirmationAlert({
      title: 'Confirm Batch Deletion',
      message: `Are you sure you want to delete ${selectedZones.size} zone(s)?`,
      confirmText: 'Delete All',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        try {
          setDeletingBatch(true);
          const zoneIds = Array.from(selectedZones);
          const result = await api.batchDeleteZones(zoneIds);

          if (result.success) {
            showAlert('Success', result.message);
          } else {
            // Show detailed results if some failed
            const failedZones = result.results
              .filter((r) => !r.success)
              .map((r) => `Zone ${r.zone_id}: ${r.message}`)
              .join('\n');
            showAlert(
              'Partial Success',
              `${result.message}\n\nFailed:\n${failedZones}`
            );
          }

          await loadZones(); // Refresh list
        } catch (error: any) {
          showAlert('Error', error.message || 'Failed to delete zones');
        } finally {
          setDeletingBatch(false);
        }
      },
    });
  };

  useEffect(() => {
    loadZones();
  }, [refreshTrigger]);

  const getZoneColor = (type: string): string => {
    switch (type) {
      case 'jamming':
        return '#ef4444';
      case 'no-fly':
        return '#f97316';
      case 'restricted':
        return '#eab308';
      default:
        return '#6b7280';
    }
  };

  const getZoneTypeLabel = (type: string): string => {
    switch (type) {
      case 'jamming':
        return 'Jamming';
      case 'no-fly':
        return 'No-Fly';
      case 'restricted':
        return 'Restricted';
      default:
        return type;
    }
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.loadingText}>Loading zones...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Active Zones</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{zones.length}</Text>
        </View>
      </View>

      {zones.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No active zones</Text>
          <Text style={styles.emptySubtext}>Create an exclusion zone to get started</Text>
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
                (selectedZones.size === 0 || deletingBatch) && styles.deleteSelectedButtonDisabled,
              ]}
              onPress={handleBatchDelete}
              disabled={selectedZones.size === 0 || deletingBatch}
            >
              {deletingBatch ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.deleteSelectedButtonText}>
                  Delete ({selectedZones.size})
                </Text>
              )}
            </TouchableOpacity>
          </View>

          <FlatList
            data={zones}
            keyExtractor={(item) => item.zone_id}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            renderItem={({ item }) => {
              const isSelected = selectedZones.has(item.zone_id);
              return (
                <View
                  style={[styles.zoneCard, isSelected && styles.zoneCardSelected]}
                >
                  {/* Checkbox */}
                  <Pressable
                    onPress={() => toggleZoneSelection(item.zone_id)}
                    style={styles.checkboxContainer}
                    disabled={deletingBatch || deletingZone === item.zone_id}
                  >
                    <View style={[styles.checkbox, isSelected && styles.checkboxChecked]}>
                      {isSelected && <Text style={styles.checkmark}>✓</Text>}
                    </View>
                  </Pressable>

                  {/* Zone Indicator */}
                  <View style={styles.zoneIndicator}>
                    <View
                      style={[styles.zoneColorDot, { backgroundColor: getZoneColor(item.type) }]}
                    />
                  </View>

                  <View style={styles.zoneInfo}>
                    <Text style={styles.zoneName}>{item.name}</Text>
                    <View style={[styles.typeTag, { backgroundColor: `${getZoneColor(item.type)}20` }]}>
                      <Text style={[styles.typeTagText, { color: getZoneColor(item.type) }]}>
                        {getZoneTypeLabel(item.type)}
                      </Text>
                    </View>
                    <Text style={styles.zoneDetails}>
                      Center: ({item.center.x.toFixed(1)}, {item.center.y.toFixed(1)},{' '}
                      {item.center.z.toFixed(1)})
                    </Text>
                    <Text style={styles.zoneDetails}>Radius: {item.radius.toFixed(1)}m</Text>
                    {item.created_at && (
                      <Text style={styles.zoneTime}>
                        Created: {new Date(item.created_at).toLocaleTimeString()}
                      </Text>
                    )}
                  </View>

                  {/* Individual Delete Button */}
                  <TouchableOpacity
                    style={[
                      styles.deleteButton,
                      (deletingZone === item.zone_id || deletingBatch) &&
                        styles.deleteButtonDisabled,
                    ]}
                    onPress={() => handleDelete(item)}
                    disabled={deletingZone === item.zone_id || deletingBatch}
                  >
                    {deletingZone === item.zone_id ? (
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
  zoneCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  zoneCardSelected: {
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
  zoneIndicator: {
    marginRight: 12,
  },
  zoneColorDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
  },
  zoneInfo: {
    flex: 1,
  },
  zoneName: {
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
  zoneDetails: {
    fontSize: 13,
    color: '#6b7280',
    fontFamily: 'monospace',
    marginBottom: 2,
  },
  zoneTime: {
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
