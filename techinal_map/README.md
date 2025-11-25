# Carte Tactique Drone Defense (Frontend)

Frontend React + Vite basé sur les spécifications pour s'intégrer avec le backend Drone Defense.

## Démarrage

- Installer dépendances: `npm i`
- Configurer les URLs (si nécessaire): copier `.env.example` vers `.env` et ajuster `VITE_API_URL` et `VITE_WS_URL`.
- Lancer en dev: `npm run dev` (port `5174`).

## Intégration Backend

- WebSocket temps réel: `VITE_WS_URL` doit pointer vers l'endpoint `ws://<host>:<port>/ws/telemetry` exposé par le backend.
- Création de mission: `POST ${VITE_API_URL}/missions` avec payload `{ drone_id, mission_type, waypoints, priority }`.

## Fonctionnalités

- Carte OpenTopoMap avec zones (sûre / restreinte) paramétrables.
- Drones en temps-réel: marqueurs colorés par statut, tooltip avec métriques.
- Trajectoires: polylignes par drone, bascule On/Off.
- Mission: formulaire simple avec waypoints, priorités et type de mission; envoi au backend.
- Ajout de waypoint par clic sur la carte.

## Personnalisation

- Modifier `src/state/store.ts` pour les zones par défaut.
- Adapter les types `src/types.ts` si le schéma de télémétrie diffère.
- Étendre la gestion WS dans `src/ws.ts` pour d'autres messages (`state_update`, etc.).