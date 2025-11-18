#include "utils.h"
#include "utils/darray.h"
#include <stdlib.h>

typedef struct {
    Item* item;
    size_t count;
} ItemStack;

typedef struct {
    ItemStack* stock;
    Position pos;
} Warehouse;

typedef struct {
    Delivery* deliveries_darray;
    Warehouse* warehouses_darray;
    Drone* drones_darray;
} Ctx;

static Ctx ctx;

typedef struct {
    Delivery** deliveries;
    Item* const* items;
    size_t item_count;
} Archetype;

static bool compare_items(Delivery* delivery, Archetype* archetype) {
    if (delivery->quantity != archetype->item_count)
        return false;
    for (size_t i = 0; i < archetype->item_count; i++) {
        if (delivery->items[i] != archetype->items[i])
            return false;
    }

    return true;
}

static Archetype* generate_archetypes(void) {
    size_t delivery_count = darray_size(ctx.deliveries_darray);

    decl_darray(archetypes, Archetype, 2);

    for (size_t i = 0; i < delivery_count; i++) {
        Delivery* delivery     = &ctx.deliveries_darray[i];
        size_t archetype_count = darray_size(archetypes);
        bool found_archetype   = false;
        for (size_t j = 0; j < archetype_count; j++) {
            Archetype* arch = &archetypes[i];
            if (compare_items(delivery, arch)) {
                // Add delivery to archetype
                darray_add(arch->deliveries, delivery);
                found_archetype = true;
                break;
            }
        }
        if (!found_archetype) {
            Archetype new_arch = {
                .items      = delivery->items,
                .item_count = delivery->quantity,
                .deliveries = darray_create(4, sizeof(Delivery*)),
            };
            darray_add(new_arch.deliveries, delivery);
            darray_add(archetypes, new_arch);
        }
    }

    return archetypes;
}

void cut(void) {
  Archetype* archetypes = generate_archetypes();
  size_t archetype_count = darray_size(archetypes);

  
}
