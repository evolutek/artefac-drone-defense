import posix_ipc
import time
from multiprocessing import shared_memory
import struct
import ctypes
from typing import List, Tuple
from dataclasses import dataclass

MAX_WAREHOUSE_ITEMS = 32
MAX_ITEM_NAME_SIZE = 128
MAX_ASSIGNMENTS = 32
MAX_DELIVERIES_PER_DRONE = 8

# ----------------------------------------------------------------------
# Packet structures
# ----------------------------------------------------------------------

class Position(ctypes.Structure): 
    _pack_ = 1
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
    ]


class EventType:
    EVENT_STOP = 0
    EVENT_DRONE_NEW = 1
    EVENT_DRONE_REMOVE = 2
    EVENT_DRONE_FINISHED = 3
    EVENT_DELIVERY_NEW = 4
    EVENT_DELIVERY_REMOVE = 5
    EVENT_WAREHOUSE_NEW = 6
    EVENT_WAREHOUSE_REMOVE = 7
    EVENT_ITEM_NEW = 8
    EVENT_ITEM_REMOVE = 9

class WaypointType:
    WAYPOINT_WAREHOUSE = 0,
    WAYPOINT_DELIVERY = 1,
    WAYPOINT_ROUTE = 2,


class NewDeliveryPkt(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint64),
        ("position", Position),
        ("priority", ctypes.c_uint8),
        ("precedence", ctypes.c_uint8),
        ("quantity", ctypes.c_uint16),
        ("item_id", ctypes.c_uint64),
    ]


class NewDronePkt(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint64),
        ("position", Position),
        ("max_capacity", ctypes.c_uint32),         # In grams
        ("energy", ctypes.c_float),                # In Wh
        ("max_flight_time", ctypes.c_uint16),      # In s
        ("max_flight_time_speed", ctypes.c_uint8), # In m/s
        ("max_speed", ctypes.c_uint8),             # In m/s
        ("acceleration", ctypes.c_uint8),          # In m/s²
    ]

class DroneFinishedPkt(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("drone_id", ctypes.c_uint64),
        ("position", Position),
        ("percent_bat", ctypes.c_float),
    ]

class NewWarehousePkt(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint64),
        ("position", Position),
        ("item_count", ctypes.c_uint32),
        ("items", ctypes.c_uint64 * MAX_WAREHOUSE_ITEMS),
    ]


class NewItemPkt(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint64),
        ("mass", ctypes.c_uint32),
        ("name_length", ctypes.c_uint32),
        ("name", ctypes.c_char * MAX_ITEM_NAME_SIZE),
    ]


class StructEventData(ctypes.Union):
    _pack_ = 1
    _fields_ = [
        ("new_delivery", NewDeliveryPkt),
        ("new_drone", NewDronePkt),
        ("drone_finished", DroneFinishedPkt),
        ("new_warehouse", NewWarehousePkt),
        ("new_item", NewItemPkt),
        ("id", ctypes.c_uint64),   # for remove/finished events
    ]


class StructEvent(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("type", ctypes.c_int),  # enum EventType is usually an int
        ("data", StructEventData),
    ]

class StructWaypoint(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("position", Position), 
        ("type", ctypes.c_int32),
    ]

class StructMission(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("mission_id", ctypes.c_uint64),
        ("drone_id", ctypes.c_uint64),
        ("waypoint_count", ctypes.c_uint32),
        ("waypoints", StructWaypoint * MAX_DELIVERIES_PER_DRONE),
    ]


class StructSharedMemory(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("backend_ready", ctypes.c_uint32),
        ("algo_ready", ctypes.c_uint32),

        ("active_buf1", ctypes.c_uint32),
        ("active_buf2", ctypes.c_uint32),

        ("buf2", StructEvent),
        ("buf1", StructMission),
    ]

# ==== Data classes ====
# Used to send new events to the algorithm.

@dataclass
class Drone:
    id: int
    position: Tuple[int, int]
    max_capacity: int
    energy: int
    max_flight_time: float
    max_speed: float
    acceleration: float

@dataclass
class Warehouse:
    id: int
    position: Tuple[int, int]
    item_ids: List[int]

@dataclass
class Item:
    id: int
    mass: float
    name: str

@dataclass
class Delivery:
    id: int
    position: Tuple[float, float]
    priority: int
    user_priority: int
    quantity: int
    item_id: int

@dataclass
class ExclusionZone:
    center: Tuple[float, float]
    radius: float
    type: int

@dataclass
class Waypoint:
    position: Tuple[float, float]
    type: int

@dataclass
class Mission:
    mission_id: int
    drone_id: int
    waypoints: List[Waypoint]
    

# ----------------------------------------------------------------------
# Shared memory algorithms & setup
# ----------------------------------------------------------------------

class AlgoInterface:

    def __init__(self):
        # Create semaphores (Python creates, C connects)
        self.sem_buf2 = posix_ipc.Semaphore("/sem_buf2", flags=posix_ipc.O_CREAT, initial_value=0)
        self.sem_buf1 = posix_ipc.Semaphore("/sem_buf1", flags=posix_ipc.O_CREAT, initial_value=0)

        # Create shared memory (Python creates, C connects)
        try:
            self.shm = shared_memory.SharedMemory(name="algo_shm", create=True, size=65536)
        except FileExistsError:
            # If it already exists, just open it
            self.shm = shared_memory.SharedMemory(name="algo_shm", create=False)

        ptr = ctypes.cast(
            ctypes.addressof(ctypes.c_char.from_buffer(self.shm.buf)),
            ctypes.POINTER(StructSharedMemory)
        )
        self.shm_struct = ptr.contents

    def wait_for_mission(self):
        self.sem_buf1.acquire()
        return self.shm_struct.buf1


interface: AlgoInterface = None

def get_assignment():
    res = interface.wait_for_mission()
    waypoints: List[Waypoint] = []
    for i in range(res.waypoint_count):
        wp = res.waypoints[i]
        waypoints.append(Waypoint((wp.position.x, wp.position.y), wp.type))
    return Mission(res.mission_id, res.drone_id, waypoints)

def new_event(event_type, data):
    """Send an event to the C algorithm via shared memory"""
    if interface is None:
        raise RuntimeError("AlgoInterface not initialized. Call algo_interface_init() first.")

    to_send: StructEvent = interface.shm_struct.buf2
    to_send.type = event_type
    edata = to_send.data

    match event_type:
        case EventType.EVENT_STOP:
            pass
        case EventType.EVENT_DRONE_NEW:
            edata.new_drone.id = data.id
            edata.new_drone.position.x = data.position[0]
            edata.new_drone.position.y = data.position[1]
            edata.new_drone.max_capacity = data.max_capacity
            edata.new_drone.energy = data.energy
            edata.new_drone.max_flight_time = data.max_flight_time
            edata.new_drone.max_speed = data.max_speed
            edata.new_drone.acceleration = data.acceleration
        case EventType.EVENT_DRONE_REMOVE:
            edata.id = data
        case EventType.EVENT_DRONE_FINISHED:
            pass
        case EventType.EVENT_DELIVERY_NEW:
            edata.new_delivery.id = data.id
            edata.new_delivery.position.x = data.position[0]
            edata.new_delivery.position.y = data.position[1]
            edata.new_delivery.priority = data.priority
            edata.new_delivery.precedence = data.user_priority
            edata.new_delivery.quantity = data.quantity
            edata.new_delivery.item_id = data.item_id
        case EventType.EVENT_DELIVERY_REMOVE:
            edata.id = data
        case EventType.EVENT_WAREHOUSE_NEW:
            edata.new_warehouse.id = data.id
            edata.new_warehouse.position.x = data.position[0]
            edata.new_warehouse.position.y = data.position[1]
            edata.new_warehouse.item_count = len(data.item_ids)
            for i, item_id in enumerate(data.item_ids[:MAX_WAREHOUSE_ITEMS]):
                edata.new_warehouse.items[i] = item_id
        case EventType.EVENT_WAREHOUSE_REMOVE:
            edata.id = data
        case EventType.EVENT_ITEM_NEW:
            edata.new_item.id = data.id
            edata.new_item.mass = data.mass
            name_bytes = data.name.encode('utf-8')[:MAX_ITEM_NAME_SIZE-1]
            edata.new_item.name_length = len(name_bytes)
            edata.new_item.name = name_bytes
        case EventType.EVENT_ITEM_REMOVE:
            edata.id = data

    interface.sem_buf2.release()

def algo_interface_init():
    """Initialize the algorithm interface (creates shared memory and semaphores)"""
    global interface
    interface = AlgoInterface()
    return interface

def algo_interface_cleanup():
    """Cleanup and stop the algorithm interface"""
    global interface
    if interface is None:
        return

    print("Python: Stopping algorithm interface...")
    try:
        # Send STOP event
        interface.shm_struct.buf2.type = EventType.EVENT_STOP
        interface.sem_buf2.release()

        # Close and unlink semaphores
        interface.sem_buf1.close()
        interface.sem_buf2.close()
        posix_ipc.unlink_semaphore("/sem_buf1")
        posix_ipc.unlink_semaphore("/sem_buf2")

        # Close and unlink shared memory
        interface.shm.close()
        interface.shm.unlink()

        interface = None
        print("Python: Algorithm interface cleaned up successfully")
    except Exception as e:
        print(f"Python: Error during cleanup: {e}")

