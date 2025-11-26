#ifndef SCENARIO_H
#define SCENARIO_H

#include <stdbool.h>
#include <stddef.h>

typedef struct {
  // TODO
  int x;
} ExclusionZone;

typedef struct {
  bool quiet;
  ExclusionZone* zones;
  size_t max_zones;
  size_t zone_count;
} Scenario;  

#endif /* ! SCENARIO_H */
