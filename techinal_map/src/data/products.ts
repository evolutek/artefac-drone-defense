export type Product = {
  id: string;
  name: string;
  category: 'munitions' | 'attachments' | 'medicaments' | 'communication' | 'logistique' | 'autre';
  description?: string;
  weight_kg?: number;
  image_url?: string;
};

export const PRODUCTS: Product[] = [
  { id: 'ammo-556', name: 'Munitions 5.56mm', category: 'munitions', weight_kg: 15, description: 'Caisses de 1000 cartouches 5.56mm', image_url: '/products/ammo-556.svg' },
  { id: 'ammo-9mm', name: 'Munitions 9mm', category: 'munitions', weight_kg: 12, description: 'Caisses de 1000 cartouches 9mm', image_url: '/products/ammo-9mm.svg' },
  { id: 'med-kit', name: 'Kit Médical Avancé', category: 'medicaments', weight_kg: 8, description: 'Pansements, garrots, antiseptiques', image_url: '/products/med-kit.svg' },
  { id: 'optic-x', name: 'Viseur Optique X', category: 'attachments', weight_kg: 1.2, description: 'Viseur optique compatible rails Picatinny', image_url: '/products/optic-x.svg' },
  { id: 'radio-secure', name: 'Radio cryptée', category: 'communication', weight_kg: 2.4, description: 'Radio longue portée, chiffrement intégré', image_url: '/products/radio-secure.svg' },
  { id: 'power-pack', name: 'Pack Énergie', category: 'logistique', weight_kg: 20, description: 'Batteries portables haute capacité', image_url: '/products/power-pack.svg' },
  { id: 'fuel-jerrycan-20l', name: 'Carburant en jerrican 20L', category: 'logistique', weight_kg: 18, description: 'Jerrican 20L (diesel) — ~18 kg', image_url: '/products/fuel-jerrycan-20l.svg' },
  { id: 'water-jerrycan-20l', name: 'Eau potable jerrican 20L', category: 'logistique', weight_kg: 20, description: 'Jerrican 20L eau — ~20 kg', image_url: '/products/water-jerrycan-20l.svg' },
  { id: 'water-pack-6x1.5l', name: 'Pack eau 6×1.5L', category: 'logistique', weight_kg: 9, description: 'Pack de 6 bouteilles 1.5L — ~9 kg', image_url: '/products/water-pack-6x1.5l.svg' },
  { id: 'food-mre-box', name: 'Rations MRE (boîte)', category: 'logistique', weight_kg: 2.5, description: 'Boîte de rations MRE — ~2.5 kg', image_url: '/products/food-mre-box.svg' },
  { id: 'food-dry-kit', name: 'Kit nourriture déshydratée', category: 'logistique', weight_kg: 6, description: 'Plats lyophilisés variés — ~6 kg', image_url: '/products/food-dry-kit.svg' },
  { id: 'hygiene-kit', name: 'Kit hygiène complet', category: 'logistique', weight_kg: 3, description: 'Savon, lingettes, brosse à dents, papier, gel hydro', image_url: '/products/hygiene-kit.svg' },
  { id: 'grenade-offensive', name: 'Grenade offensive', category: 'munitions', weight_kg: 0.45, description: 'Grenade offensive (onde de choc, faible fragmentation)', image_url: '/products/grenade-offensive.svg' },
  { id: 'grenade-defensive-frag', name: 'Grenade défensive (frag)', category: 'munitions', weight_kg: 0.6, description: 'Grenade à fragmentation (défensive)', image_url: '/products/grenade-frag.svg' },
  { id: 'grenade-smoke', name: 'Grenade fumigène', category: 'munitions', weight_kg: 0.4, description: 'Grenade fumigène multi-couleurs', image_url: '/products/grenade-smoke.svg' },
  { id: 'grenade-flash', name: 'Grenade flash (stun)', category: 'munitions', weight_kg: 0.3, description: 'Grenade assourdissante (flashbang)', image_url: '/products/grenade-flash.svg' },
  { id: 'mech-props-set', name: 'Hélices renforcées (set de 4)', category: 'logistique', weight_kg: 0.5, description: 'Jeu de 4 hélices carbone renforcées', image_url: '/products/propeller-reinforced.svg' },
  { id: 'mech-motor-2212', name: 'Moteur brushless 2212', category: 'logistique', weight_kg: 0.08, description: 'Moteur 2212 KV920 pour drone multirotor', image_url: '/products/motor-brushless.svg' },
  { id: 'mech-esc-30a', name: 'ESC 30A', category: 'logistique', weight_kg: 0.05, description: 'Contrôleur électronique de vitesse 30A', image_url: '/products/esc-30a.svg' },
  { id: 'mech-screws-kit', name: 'Kit visserie inox', category: 'logistique', weight_kg: 0.4, description: 'Assortiment de vis/écrous/entretoises inox', image_url: '/products/screw-kit.svg' },
  { id: 'ext-co2-2kg', name: 'Extincteur CO2 2kg', category: 'logistique', weight_kg: 6, description: 'Extincteur CO2 2kg pour feux B/électriques', image_url: '/products/extinguisher-co2-2kg.svg' },
  { id: 'ext-powder-6kg', name: 'Extincteur poudre 6kg', category: 'logistique', weight_kg: 9, description: 'Extincteur poudre polyvalent ABC 6kg', image_url: '/products/extinguisher-powder-6kg.svg' },
  { id: 'ext-aerosol-1l', name: 'Aérosol anti-feu 1L', category: 'logistique', weight_kg: 1.2, description: 'Aérosol extincteur portable 1L', image_url: '/products/extinguisher-aerosol-1l.svg' },
];