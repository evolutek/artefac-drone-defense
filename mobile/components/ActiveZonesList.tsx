import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import api, { Zone } from '../services/api';
import { showConfirmationAlert, showAlert } from '../utils/confirmationAlert';

export default function ActiveZonesList({ refreshTrigger }: { refreshTrigger?: number }) {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [deletingZone, setDeletingZone] = useState<string | null>(null);

  const loadZones = async () => {
    try {
      setLoading(true);
      const activeZones = await api.getZones();
      setZones(activeZones);
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
        <FlatList
          data={zones}
          keyExtractor={(item) => item.zone_id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={({ item }) => (
            <View style={styles.zoneCard}>
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

              <TouchableOpacity
                style={[
                  styles.deleteButton,
                  deletingZone === item.zone_id && styles.deleteButtonDisabled,
                ]}
                onPress={() => handleDelete(item)}
                disabled={deletingZone === item.zone_id}
              >
                {deletingZone === item.zone_id ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.deleteButtonText}>Delete</Text>
                )}
              </TouchableOpacity>
            </View>
          )}
        />
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
