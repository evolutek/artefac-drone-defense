import React, { useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Platform,
} from 'react-native';
import DroneSpawnForm from './components/DroneSpawnForm';
import ActiveDronesList from './components/ActiveDronesList';
import ZoneCreateForm from './components/ZoneCreateForm';
import ActiveZonesList from './components/ActiveZonesList';
import EntrepotCreateForm from './components/EntrepotCreateForm';
import ActiveEntrepotsList from './components/ActiveEntrepotsList';
import LivraisonCreateForm from './components/LivraisonCreateForm';
import ActiveLivraisonsList from './components/ActiveLivraisonsList';

type Tab = 'drones' | 'zones' | 'warehouses' | 'deliveries';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('drones');
  const [droneRefreshTrigger, setDroneRefreshTrigger] = useState(0);
  const [zoneRefreshTrigger, setZoneRefreshTrigger] = useState(0);
  const [warehouseRefreshTrigger, setWarehouseRefreshTrigger] = useState(0);
  const [deliveryRefreshTrigger, setDeliveryRefreshTrigger] = useState(0);

  const handleDroneSpawnSuccess = () => {
    setDroneRefreshTrigger((prev) => prev + 1);
  };

  const handleZoneCreateSuccess = () => {
    setZoneRefreshTrigger((prev) => prev + 1);
  };

  const handleWarehouseCreateSuccess = () => {
    setWarehouseRefreshTrigger((prev) => prev + 1);
  };

  const handleDeliveryCreateSuccess = () => {
    setDeliveryRefreshTrigger((prev) => prev + 1);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <StatusBar style="auto" />

        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Simulation Control</Text>
          <Text style={styles.headerSubtitle}>Artefac Drone Defense</Text>
        </View>

        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'drones' && styles.tabActive]}
            onPress={() => setActiveTab('drones')}
          >
            <Text style={[styles.tabText, activeTab === 'drones' && styles.tabTextActive]}>
              Drones
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'zones' && styles.tabActive]}
            onPress={() => setActiveTab('zones')}
          >
            <Text style={[styles.tabText, activeTab === 'zones' && styles.tabTextActive]}>
              Zones
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'warehouses' && styles.tabActive]}
            onPress={() => setActiveTab('warehouses')}
          >
            <Text style={[styles.tabText, activeTab === 'warehouses' && styles.tabTextActive]}>
              Warehouses
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'deliveries' && styles.tabActive]}
            onPress={() => setActiveTab('deliveries')}
          >
            <Text style={[styles.tabText, activeTab === 'deliveries' && styles.tabTextActive]}>
              Deliveries
            </Text>
          </TouchableOpacity>
        </View>

        {/* Content */}
        <ScrollView
          style={styles.content}
          contentContainerStyle={styles.contentContainer}
          showsVerticalScrollIndicator={false}
        >
          {activeTab === 'drones' ? (
            <>
              <DroneSpawnForm onSpawnSuccess={handleDroneSpawnSuccess} />
              <ActiveDronesList refreshTrigger={droneRefreshTrigger} />
            </>
          ) : activeTab === 'zones' ? (
            <>
              <ZoneCreateForm onCreateSuccess={handleZoneCreateSuccess} />
              <ActiveZonesList refreshTrigger={zoneRefreshTrigger} />
            </>
          ) : activeTab === 'warehouses' ? (
            <>
              <EntrepotCreateForm onCreateSuccess={handleWarehouseCreateSuccess} />
              <ActiveEntrepotsList refreshTrigger={warehouseRefreshTrigger} />
            </>
          ) : (
            <>
              <LivraisonCreateForm onCreateSuccess={handleDeliveryCreateSuccess} />
              <ActiveLivraisonsList refreshTrigger={deliveryRefreshTrigger} />
            </>
          )}
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  container: {
    flex: 1,
  },
  header: {
    backgroundColor: '#1e40af',
    paddingVertical: 20,
    paddingHorizontal: 16,
    ...Platform.select({
      web: {
        paddingTop: 20,
      },
      default: {},
    }),
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#bfdbfe',
    fontWeight: '500',
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: '#3b82f6',
  },
  tabText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#6b7280',
  },
  tabTextActive: {
    color: '#1e40af',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 32,
  },
});
