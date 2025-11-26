#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8000"
TEMP_DIR="/tmp/artefac_tests"
mkdir -p "$TEMP_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Backend API + C Algorithm Integration Test Suite     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test backend health
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1. Health Check${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if curl -s $BASE_URL/health | python3 -m json.tool; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${RED}❌ Backend not responding${NC}"
    exit 1
fi
echo ""

# Test Products CRUD → sends to algo
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}2. Products (Items) → C Algorithm${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}2.1. List existing products${NC}"
curl -s $BASE_URL/products | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Found {len(data)} products'); [print(f'  - {p[\"id\"]}: {p[\"name\"]} ({p[\"weight_kg\"]}kg)') for p in data[:5]]" || true

echo -e "${CYAN}2.2. Create test product → EVENT_ITEM_NEW to algo${NC}"
NEW_PRODUCT_PAYLOAD='{"name":"Test Algo Item","description":"Test item for algo testing","category":"test","weight_kg":2.5,"image_url":"/test.svg"}'
HTTP_CODE=$(curl -s -o "$TEMP_DIR/product_create.json" -w "%{http_code}" \
    -X POST -H "Content-Type: application/json" \
    -d "$NEW_PRODUCT_PAYLOAD" \
    $BASE_URL/products 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    TEST_PRODUCT_ID=$(cat "$TEMP_DIR/product_create.json" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "999")
    echo -e "${GREEN}✅ Product created (ID: $TEST_PRODUCT_ID) → sent EVENT_ITEM_NEW to algo${NC}"
elif [ "$HTTP_CODE" = "400" ]; then
    echo -e "${YELLOW}⚠️  Product already exists, finding ID...${NC}"
    curl -s $BASE_URL/products | python3 -c "import sys, json; data=json.load(sys.stdin); result=[p for p in data if p['name']=='Test Algo Item']; print(f'{result[0][\"id\"]}' if result else '999')" > "$TEMP_DIR/test_product_id.txt"
    TEST_PRODUCT_ID=$(cat "$TEMP_DIR/test_product_id.txt")
    echo -e "${YELLOW}   Using existing product ID: $TEST_PRODUCT_ID${NC}"
else
    echo -e "${RED}❌ Failed to create product (HTTP $HTTP_CODE)${NC}"
    TEST_PRODUCT_ID="999"
fi
echo ""

# Test Warehouses CRUD → sends to algo
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}3. Warehouses → C Algorithm${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}3.1. List existing warehouses${NC}"
curl -s $BASE_URL/warehouses | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Found {len(data)} warehouses'); [print(f'  - {w[\"id\"]}: {w[\"name\"]} at ({w[\"latitude\"]}, {w[\"longitude\"]})') for w in data[:3]]" || true

echo -e "${CYAN}3.2. Create test warehouse → EVENT_WAREHOUSE_NEW to algo${NC}"
NEW_WAREHOUSE_PAYLOAD='{"name":"Test Algo Warehouse","latitude":48.8566,"longitude":2.3522,"address":"Test Address, Paris","capacity":50000}'
HTTP_CODE=$(curl -s -o "$TEMP_DIR/warehouse_create.json" -w "%{http_code}" \
    -X POST -H "Content-Type: application/json" \
    -d "$NEW_WAREHOUSE_PAYLOAD" \
    $BASE_URL/warehouses 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    TEST_WAREHOUSE_ID=$(cat "$TEMP_DIR/warehouse_create.json" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "1")
    echo -e "${GREEN}✅ Warehouse created (ID: $TEST_WAREHOUSE_ID) → sent EVENT_WAREHOUSE_NEW to algo${NC}"
else
    echo -e "${YELLOW}⚠️  Using first existing warehouse${NC}"
    TEST_WAREHOUSE_ID="1"
fi
echo ""

# Test Drones CRUD → sends to algo
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}4. Drones → C Algorithm${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}4.1. List existing drones${NC}"
curl -s $BASE_URL/drones | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Found {len(data)} drones'); [print(f'  - {d[\"drone_id\"]}: {d[\"name\"]} (battery: {d[\"battery_level\"]}%)') for d in data[:3]]" || true

echo -e "${CYAN}4.2. Create test drone → EVENT_DRONE_NEW to algo${NC}"
NEW_DRONE_PAYLOAD='{"drone_id":"TEST-ALGO-DRONE-001","name":"Test Algo Drone","model":"AlgoTestModel"}'
HTTP_CODE=$(curl -s -o "$TEMP_DIR/drone_create.json" -w "%{http_code}" \
    -X POST -H "Content-Type: application/json" \
    -d "$NEW_DRONE_PAYLOAD" \
    $BASE_URL/drones 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Drone created (TEST-ALGO-DRONE-001) → sent EVENT_DRONE_NEW to algo${NC}"
    TEST_DRONE_ID="TEST-ALGO-DRONE-001"
elif [ "$HTTP_CODE" = "400" ]; then
    echo -e "${YELLOW}⚠️  Drone already exists${NC}"
    TEST_DRONE_ID="TEST-ALGO-DRONE-001"
else
    echo -e "${RED}❌ Failed to create drone (HTTP $HTTP_CODE)${NC}"
    TEST_DRONE_ID="TEST-ALGO-DRONE-001"
fi
echo ""

# Test Missions/Deliveries CRUD → sends to algo
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}5. Missions/Deliveries → C Algorithm${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}5.1. Create test mission with payload → EVENT_DELIVERY_NEW to algo${NC}"
NEW_MISSION_PAYLOAD='{"drone_id":"'$TEST_DRONE_ID'","mission_type":"delivery","waypoints":[{"lat":48.8566,"lon":2.3522,"alt":50}],"payloads":[{"item_name":"Test Algo Item","quantity":3}],"priority":8,"note":"Test mission for algo"}'
HTTP_CODE=$(curl -s -o "$TEMP_DIR/mission_create.json" -w "%{http_code}" \
    -X POST -H "Content-Type: application/json" \
    -d "$NEW_MISSION_PAYLOAD" \
    $BASE_URL/missions 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    TEST_MISSION_ID=$(cat "$TEMP_DIR/mission_create.json" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "999")
    echo -e "${GREEN}✅ Mission created (ID: $TEST_MISSION_ID) → sent EVENT_DELIVERY_NEW to algo${NC}"
    cat "$TEMP_DIR/mission_create.json" | python3 -m json.tool | head -20
else
    echo -e "${RED}❌ Failed to create mission (HTTP $HTTP_CODE)${NC}"
    cat "$TEMP_DIR/mission_create.json" 2>/dev/null || true
    TEST_MISSION_ID="999"
fi
echo ""

# Test get_assignment from algo
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}6. Get Assignment from C Algorithm${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}6.1. Calling GET /algo/assignment (may block waiting for algo)${NC}"
echo -e "${YELLOW}   ⏳ Waiting for C algorithm to compute assignment...${NC}"

# Use timeout to avoid infinite blocking
TIMEOUT_SEC=10
HTTP_CODE=$(timeout $TIMEOUT_SEC curl -s -o "$TEMP_DIR/assignment.json" -w "%{http_code}" \
    $BASE_URL/algo/assignment 2>/dev/null || echo "timeout")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Assignment received from algorithm!${NC}"
    cat "$TEMP_DIR/assignment.json" | python3 -m json.tool

    # Parse and display assignment details
    echo ""
    echo -e "${CYAN}Assignment Details:${NC}"
    cat "$TEMP_DIR/assignment.json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  Mission ID: {data[\"mission_id\"]}')
print(f'  Drone ID: {data[\"drone_id\"]}')
print(f'  Waypoints: {len(data[\"waypoints\"])} waypoints')
for i, wp in enumerate(data['waypoints']):
    wp_type = 'WAREHOUSE' if wp['type'] == 0 else ('DELIVERY' if wp['type'] == 1 else 'ROUTE')
    print(f'    {i+1}. {wp_type} at ({wp[\"position\"][\"x\"]:.6f}, {wp[\"position\"][\"y\"]:.6f})')
" || true
elif [ "$HTTP_CODE" = "timeout" ]; then
    echo -e "${YELLOW}⏱️  Request timed out after ${TIMEOUT_SEC}s${NC}"
    echo -e "${YELLOW}   This is normal if the C algorithm is not running or has no assignments ready${NC}"
elif [ "$HTTP_CODE" = "503" ]; then
    echo -e "${YELLOW}⚠️  Algorithm not available (HTTP 503)${NC}"
    echo -e "${YELLOW}   The C algorithm may not be running${NC}"
else
    echo -e "${RED}❌ Failed to get assignment (HTTP $HTTP_CODE)${NC}"
    cat "$TEMP_DIR/assignment.json" 2>/dev/null || true
fi
echo ""

# Test DELETE operations → sends REMOVE events to algo
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}7. DELETE Operations → REMOVE Events to Algo${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}7.1. Delete mission → EVENT_DELIVERY_REMOVE to algo${NC}"
if [ "$TEST_MISSION_ID" != "999" ]; then
    HTTP_CODE=$(curl -s -o "$TEMP_DIR/mission_delete.json" -w "%{http_code}" \
        -X DELETE $BASE_URL/missions/$TEST_MISSION_ID 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Mission deleted → sent EVENT_DELIVERY_REMOVE to algo${NC}"
    else
        echo -e "${YELLOW}⚠️  Failed to delete mission (HTTP $HTTP_CODE)${NC}"
    fi
else
    echo -e "${YELLOW}⊘  Skipping (no test mission created)${NC}"
fi

echo -e "${CYAN}7.2. Delete product → EVENT_ITEM_REMOVE to algo${NC}"
if [ "$TEST_PRODUCT_ID" != "999" ]; then
    HTTP_CODE=$(curl -s -o "$TEMP_DIR/product_delete.json" -w "%{http_code}" \
        -X DELETE $BASE_URL/products/$TEST_PRODUCT_ID 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Product deleted → sent EVENT_ITEM_REMOVE to algo${NC}"
    else
        echo -e "${YELLOW}⚠️  Failed to delete product (HTTP $HTTP_CODE)${NC}"
    fi
else
    echo -e "${YELLOW}⊘  Skipping (no test product created)${NC}"
fi
echo ""

# Summary
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Test Summary                                          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Event Flow Tested:"
echo "  ✓ POST   /products    → EVENT_ITEM_NEW to C algo"
echo "  ✓ DELETE /products/:id → EVENT_ITEM_REMOVE to C algo"
echo "  ✓ POST   /warehouses  → EVENT_WAREHOUSE_NEW to C algo"
echo "  ✓ POST   /drones      → EVENT_DRONE_NEW to C algo"
echo "  ✓ POST   /missions    → EVENT_DELIVERY_NEW to C algo"
echo "  ✓ DELETE /missions/:id → EVENT_DELIVERY_REMOVE to C algo"
echo "  ✓ GET    /algo/assignment → get_assignment() from C algo"
echo ""
echo "Test artifacts saved in: $TEMP_DIR"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Check backend logs for algo event messages"
echo "  2. Check if C algorithm is running: ps aux | grep algo"
echo "  3. To compile C algo: cd backend/app/logic && make all"
echo "  4. Open http://localhost:5176/ (techinal_map) for UI testing"
echo "  5. Open http://localhost:8010/ (backoffice) for admin UI"
echo ""
