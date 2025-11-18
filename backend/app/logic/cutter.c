#include "utils.h"

typedef struct Item Item;

typedef struct {
  Item *item;
  size_t count;
} ItemStack;  

typedef struct {
  ItemStack* stock;
  struct Position pos;

} Warehouse;
