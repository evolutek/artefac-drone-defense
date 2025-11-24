import drones.manager as drone
import entrepots.manager as entrepots
import livraisons.manager as livraison
import zones.manager as zones

def map_config():
    entrepots.spawn_entrepot(1, start, 0, 0, 0)
    #livraison.
    zones.spawn_zone(1, start, 50, 50, 50, 30, "jamming")
    return 