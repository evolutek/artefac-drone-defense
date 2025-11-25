from simulation_control.drones.manager import spawn_drone
from simulation_control.entrepots.manager import spawn_entrepot
from simulation_control.livraisons.manager import spawn_livraison
from simulation_control.zones.manager import spawn_zone

def map_config():
    print("===================")
    print("start map_config")
    print("===================")

    spawn_entrepot(1, "start", 150, 150, 0, "food")
    spawn_livraison(1, "start", 70, 70, 0, "food")
    spawn_zone(1, "start", -300, -300, 0, 30, "jamming")

