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
import api, { Livraison } from '../services/api';
import { showConfirmationAlert, showAlert } from '../utils/confirmationAlert';

export default function ActiveLivraisonsList({ refreshTrigger }: { refreshTrigger?: number }) {
  const [livraisons, setLivraisons] = useState<Livraison[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [deletingLivraison, setDeletingLivraison] = useState<string | null>(null);
  const [selectedLivraisons, setSelectedLivraisons] = useState<Set<string>>(new Set());
  const [deletingBatch, setDeletingBatch] = useState(false);

  const loadLivraisons = async () => {
    try {
      setLoading(true);
      const activeLivraisons = await api.getLivraisons();
      setLivraisons(activeLivraisons);
      // Clear selection when reloading (in case selected livraisons were deleted)
      setSelectedLivraisons(new Set());
    } catch (error: any) {
      console.error('Failed to load livraisons:', error);
      showAlert('Error', 'Failed to load active deliveries');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleDelete = async (livraison: Livraison) => {
    console.log('[ActiveLivraisonsList] handleDelete called for:', livraison.livraison_id, livraison.name);

    await showConfirmationAlert({
      title: 'Confirm Deletion',
      message: `Are you sure you want to delete delivery "${livraison.name}"?`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        console.log('[ActiveLivraisonsList] Delete confirmed - starting deletion...');
        try {
          setDeletingLivraison(livraison.livraison_id);
          console.log('[ActiveLivraisonsList] Calling api.deleteLivraison for livraison_id:', livraison.livraison_id);
          const result = await api.deleteLivraison(livraison.livraison_id);
          console.log('[ActiveLivraisonsList] API response:', result);

          if (result.success) {
            console.log('[ActiveLivraisonsList] Deletion successful');
            showAlert('Success', result.message);
            await loadLivraisons(); // Refresh list
          } else {
            console.error('[ActiveLivraisonsList] Deletion failed:', result.message);
            showAlert('Error', result.message);
          }
        } catch (error: any) {
          console.error('[ActiveLivraisonsList] Exception during deletion:', error);
          showAlert('Error', error.message || 'Failed to delete delivery');
        } finally {
          setDeletingLivraison(null);
        }
      },
      onCancel: () => console.log('[ActiveLivraisonsList] Deletion cancelled'),
    });
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadLivraisons();
  };

  const toggleLivraisonSelection = (livraisonId: string) => {
    setSelectedLivraisons((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(livraisonId)) {
        newSet.delete(livraisonId);
      } else {
        newSet.add(livraisonId);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedLivraisons(new Set(livraisons.map((l) => l.livraison_id)));
  };

  const deselectAll = () => {
    setSelectedLivraisons(new Set());
  };

  const handleBatchDelete = async () => {
    if (selectedLivraisons.size === 0) return;

    await showConfirmationAlert({
      title: 'Confirm Batch Deletion',
      message: `Are you sure you want to delete ${selectedLivraisons.size} delivery(ies)?`,
      confirmText: 'Delete All',
      cancelText: 'Cancel',
      confirmStyle: 'destructive',
      onConfirm: async () => {
        try {
          setDeletingBatch(true);
          const livraisonIds = Array.from(selectedLivraisons);
          const result = await api.batchDeleteLivraisons(livraisonIds);

          if (result.success) {
            showAlert('Success', result.message);
          } else {
            // Show detailed results if some failed
            const failedLivraisons = result.results
              .filter((r) => !r.success)
              .map((r) => `Livraison ${r.livraison_id}: ${r.message}`)
              .join('\n');
            showAlert(
              'Partial Success',
              `${result.message}\n\nFailed:\n${failedLivraisons}`
            );
          }

          await loadLivraisons(); // Refresh list
        } catch (error: any) {
          showAlert('Error', error.message || 'Failed to delete deliveries');
        } finally {
          setDeletingBatch(false);
        }
      },
    });
  };

  useEffect(() => {
    loadLivraisons();
  }, [refreshTrigger]);

  const getLivraisonColor = (type: string): string => {
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

  const getLivraisonTypeLabel = (type: string): string => {
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
        <Text style={styles.loadingText}>Loading deliveries...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Active Deliveries</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{livraisons.length}</Text>
        </View>
      </View>

      {livraisons.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No active deliveries</Text>
          <Text style={styles.emptySubtext}>Create a delivery to get started</Text>
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
                (selectedLivraisons.size === 0 || deletingBatch) && styles.deleteSelectedButtonDisabled,
              ]}
              onPress={handleBatchDelete}
              disabled={selectedLivraisons.size === 0 || deletingBatch}
            >
              {deletingBatch ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.deleteSelectedButtonText}>
                  Delete ({selectedLivraisons.size})
                </Text>
              )}
            </TouchableOpacity>
          </View>

          <FlatList
            data={livraisons}
            keyExtractor={(item) => item.livraison_id}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            renderItem={({ item }) => {
              const isSelected = selectedLivraisons.has(item.livraison_id);
              return (
                <View
                  style={[styles.livraisonCard, isSelected && styles.livraisonCardSelected]}
                >
                  {/* Checkbox */}
                  <Pressable
                    onPress={() => toggleLivraisonSelection(item.livraison_id)}
                    style={styles.checkboxContainer}
                    disabled={deletingBatch || deletingLivraison === item.livraison_id}
                  >
                    <View style={[styles.checkbox, isSelected && styles.checkboxChecked]}>
                      {isSelected && <Text style={styles.checkmark}>✓</Text>}
                    </View>
                  </Pressable>

                  {/* Livraison Indicator */}
                  <View style={styles.livraisonIndicator}>
                    <View
                      style={[styles.livraisonColorDot, { backgroundColor: getLivraisonColor(item.type) }]}
                    />
                  </View>

                  <View style={styles.livraisonInfo}>
                    <Text style={styles.livraisonName}>{item.name}</Text>
                    <View style={[styles.typeTag, { backgroundColor: `${getLivraisonColor(item.type)}20` }]}>
                      <Text style={[styles.typeTagText, { color: getLivraisonColor(item.type) }]}>
                        {getLivraisonTypeLabel(item.type)}
                      </Text>
                    </View>
                    {item.position ? (
                      <Text style={styles.livraisonDetails}>
                        Position: ({item.position.x.toFixed(1)}, {item.position.y.toFixed(1)},{' '}
                        {item.position.z.toFixed(1)})
                      </Text>
                    ) : (
                      <Text style={[styles.livraisonDetails, styles.unknownText]}>
                        Position: Unknown
                      </Text>
                    )}
                    {item.created_at && (
                      <Text style={styles.livraisonTime}>
                        Created: {new Date(item.created_at).toLocaleTimeString()}
                      </Text>
                    )}
                  </View>

                  {/* Individual Delete Button */}
                  <TouchableOpacity
                    style={[
                      styles.deleteButton,
                      (deletingLivraison === item.livraison_id || deletingBatch) &&
                        styles.deleteButtonDisabled,
                    ]}
                    onPress={() => handleDelete(item)}
                    disabled={deletingLivraison === item.livraison_id || deletingBatch}
                  >
                    {deletingLivraison === item.livraison_id ? (
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
  livraisonCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  livraisonCardSelected: {
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
  livraisonIndicator: {
    marginRight: 12,
  },
  livraisonColorDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
  },
  livraisonInfo: {
    flex: 1,
  },
  livraisonName: {
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
  livraisonDetails: {
    fontSize: 13,
    color: '#6b7280',
    fontFamily: 'monospace',
    marginBottom: 2,
  },
  unknownText: {
    fontStyle: 'italic',
    color: '#9ca3af',
  },
  livraisonTime: {
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
