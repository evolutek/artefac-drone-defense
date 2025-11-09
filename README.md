# artefac-drone-defense
Hackathon Drone Defense organisé par Artefac. Ce repo est celui de l'équipe Evolutek&lt;&lt; pour le challenge 4, livrer en situation de crise.

# Besoins
On souhaite que (liste non finale ni exhaustive):
- On puisse mettre un système d'autorisation de départ même si le drone est prêt
- Un drone ne part pas si il n'a pas la batterie nécessaire pour revenir
- Un drone ne peut plus communiquer quand il a quitté l'entrepôt
- Un drone peut de nouveau communiquer quand il retourne en gare
- Les gares de drones et les entrepôts ne sont pas forcément au même endroit
- Les entrepôts ont un stock limité
- Les drones ont une batterie limitée, une vitesse de chargement limitée et une capacité de charge en soute limitée

# Assomptions
On assume que (liste non finale ni exhaustive):
- Le chargement est automatique et instantané (facile à ajouter)
- Une livraison est automatiquement plus prioritaires que les précédentes (exemple: Si D1 ne fait rien et D2 est en train de livrer et q'une nouvelle livraison arrive et que D2 peut la finir avant D1 sans compromettre son retour en gare, il la prend)
- La batterie des drones est calculée en unité de distance et a une valeur fixe (on s'embête pas de pertes de batterie à l'arrêt, de variations des niveaux de perte etc...)
- On s'embête pas de vitesses d'accélération / de décélération
- On s'embête pas de la possibilité que les drones puissent être interceptés en route (facile à ajouter)
- Les gares de drones peuvent en charger une infinité
