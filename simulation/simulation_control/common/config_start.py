from simulation_control.drones.manager import spawn_drone
from simulation_control.entrepots.manager import spawn_entrepot
from simulation_control.livraisons.manager import spawn_livraison
from simulation_control.zones.manager import spawn_zone

def map_config():
    print("===================")
    print("start map_config")
    print("===================")

    spawn_entrepot(1, "start", 0, 30, 0, "food")
    spawn_livraison(1, "start", 150, 0, 150, "food")
    spawn_zone(1, "start", 50, 50, 50, 30, "jamming")

