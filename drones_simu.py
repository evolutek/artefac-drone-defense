from enum import Enum
import math
import json
import sys

# ---------------
# | UTILITAIRES |
# ---------------

class Status(Enum):
    GARE = 0 # Drone
    TRANQUILLE = 1 # Drone
    PRE_MISSION = 2 # Drone
    MISSION = 3 # Drone
    EN_COURS = 4 # Livraison
    EN_ATTENTE = 5 # Livraison
    EFFECTUEE = 6 # Livraison
    EN_ATTENTE_LIVREUR = 7 # Livraison

def dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def output(text):
    print(text)

def output_tick(text):
    output("[TICK]" + text)

def output_mouv(text):
    output_tick("[MOUV]" + text)

def check_livraisons():
    global LIVRAISONS
    global DRONES
    sortie = True
    for x in LIVRAISONS:
        if x.status != Status.EFFECTUEE:
            sortie = False
            if x.status == Status.EN_ATTENTE:
                x.recalc()
            elif x.status == Status.EN_ATTENTE_LIVREUR:
                res = [dro.peut(x) for dro in DRONES]
                output(f"{x} Comparaison drones: {res}.")
                meilleur_index = res.index(min(res))
                if meilleur_index == float("inf"):
                    output_tick(f"{x} ne peut pas être livrée.")
                else:
                    DRONES[meilleur_index].missionne(x)
                    x.status = Status.EN_COURS
    return sortie

# ----------
# | OBJETS |
# ----------

OBJETS = []
ENTREPOTS = []
GARES = []
LIVRAISONS = []
DRONES = []

class Objet:
    def __init__(self, nom, masse):
        global OBJETS
        self.id = len(OBJETS)
        output(f"{self} Enregistrement.")
        OBJETS.append(self)
        self.nom = nom
        self.masse = masse

    def __str__(self):
        return f"[OBJET {self.id}]"

class Entrepot:
    def __init__(self, coos, matos):
        global ENTREPOTS
        self.id = len(ENTREPOTS)
        output(f"{self} Enregistrement.")
        ENTREPOTS.append(self)
        self.coos = coos
        self.matos = matos

    def a(self, nom):
        for x in self.matos:
            if x.nom == nom:
                return True
        return False

    def donner(self, drone, nom):
        for i in range(len(self.matos)):
            if self.matos[i].nom == nom and drone.remplir(self.matos[i]):
                self.matos.pop(i)
                return True
        return False

    def __str__(self):
        return f"[ENTREPOT {self.id}]"

class Gare:
    def __init__(self, coos):
        global GARES
        self.id = len(GARES)
        output(f"{self} Enregistrement.")
        GARES.append(self)
        self.coos = coos

    def __str__(self):
        return f"[GARE {self.id}]"

class Livraison:
    def __init__(self, coos, objet):
        global LIVRAISONS
        self.id = len(LIVRAISONS)
        output(f"{self} Enregistrement.")
        LIVRAISONS.append(self)
        global ENTREPOTS
        self.coos = coos
        self.objet = objet
        self.recalc()

    def recalc(self):
        mini = None
        min_dist = float("inf")
        for x in ENTREPOTS:
            d = dist(self.coos, x.coos)
            if d < min_dist and x.a(self.objet.nom):
                mini = x
                min_dist = d
        self.entrepot = mini # Check if not None (outside)
        if self.entrepot == None:
            self.status = Status.EN_ATTENTE
            output_tick(f"{self} Manque de matériel pour livrer.")
        else:
            self.status = Status.EN_ATTENTE_LIVREUR
            output(f"{self} Sera apprivisionné à {self.entrepot}.")

    def __str__(self):
        return f"[LIVRAISON {self.id}]"

class Drone:
    def __init__(self, coos, charge, batterie, vitesse, vitesse_charge):
        global DRONES
        self.id = len(DRONES)
        output(f"{self} Enregistrement.")
        DRONES.append(self)
        self.charge = 0
        self.max_charge = charge
        self.batterie = batterie # en unité de distance
        self.max_batterie = batterie
        self.contenu = []
        self.vitesse = vitesse
        self.vitesse_charge = vitesse_charge
        self.coos = coos
        self.trajet = []
        self.cout_trajet = 0
        self.status = Status.GARE
        self.dist_restante = 0
        self.veut = []

    def remplir(self, objet):
        if self.charge + objet.masse > self.max_charge:
            return False
        self.contenu.append(objet)
        return True

    def larguer(self, nom):
        for i in range(len(self.contenu)):
            if self.contenu[i].nom == nom:
                self.charge -= self.contenu[i].masse
                self.contenu.pop(i)
                return True
        return False

    def peut(self, livraison): # Retourne inf ou le temps nécessaire
        global GARES
        if self.status == Status.MISSION or self.charge + livraison.objet.masse > self.max_charge:
            output(f"{self} Trop lourd ou hors communication.")
            return float("inf")
        elif self.trajet == []:
            total_dist = dist(self.coos, livraison.entrepot.coos) + dist(livraison.entrepot.coos, livraison.coos) + min([dist(livraison.coos, x.coos) for x in GARES])
            total_masse = livraison.objet.masse
            if total_dist <= self.batterie:
                return total_dist / self.vitesse
            output(f"{self} Rien à faire: pas assez de batterie.")
            return float("inf")
        else:
            detours_entrepots = [dist(self.trajet[i].coos, livraison.entrepot.coos) + dist(livraison.entrepot.coos, self.trajet[i+1].coos) for i in range(len(self.trajet) - 1)]
            retenu_entrepot = min(detours_entrepots)
            index_entrepot = detours_entrepots.index(retenu_entrepot)
            detours_livraison = [dist(self.trajet[i].coos, livraison.coos) + dist(livraison.coos, self.trajet[i+1].coos) for i in range(index_entrepot, len(self.trajet) - 1)] # On livre APRES s'etre rempli
            retenu_livraison = min(detours_livraison)
            total = self.cout_trajet + retenu_entrepot + retenu_livraison
            if total <= self.batterie:
                return total / self.vitesse
            output(f"{self} En déplacement: pas assez de batterie.")
            return float("inf")

    def missionne(self, livraison):
        # On s'estime valide
        output(f"{self} Part en mission.")
        if self.trajet == []:
            self.trajet.append(livraison.entrepot)
            self.trajet.append(livraison)
            dl = [dist(livraison.coos, x.coos) for x in GARES]
            self.trajet.append(GARES[dl.index(min(dl))])
            self.dist_restante = dist(self.coos, livraison.entrepot.coos)
            self.status = Status.PRE_MISSION
        else:
            detours_entrepots = [dist(self.trajet[i].coos, livraison.entrepot.coos) + dist(livraison.entrepot.coos, self.trajet[i+1].coos) for i in range(len(self.trajet) - 1)]
            retenu_entrepot = min(detours_entrepots)
            index_entrepot = detours_entrepots.index(retenu_entrepot)
            self.trajet.insert(index_entrepot, livraison.entrepot)
            detours_livraison = [dist(self.trajet[i].coos, livraison.coos) + dist(livraison.coos, self.trajet[i+1].coos) for i in range(index_entrepot, len(self.trajet) - 1)] # On livre APRES s'etre rempli
            retenu_livraison = min(detours_livraison)
            self.trajet.insert(detours_livraison.index(retenu_livraison), livraison)
        self.veut.append(livraison.objet.nom)
        self.charge += livraison.objet.masse

    def recalc_coos(self, dest, dist):
        angle = math.atan2(dest.coos[1] - self.coos[1], dest.coos[0] - self.coos[0])
        self.coos = (self.coos[0] + math.cos(angle) * dist, self.coos[1] + math.sin(angle) * dist)
        output_mouv(f"{self} new coos: {self.coos}.")

    def tick(self):
        if self.status == Status.GARE:
            output_tick(f"{self} charge.")
            self.batterie = min(self.max_batterie, self.batterie + self.vitesse_charge)
        elif self.status != Status.TRANQUILLE:
            output_mouv(f"{self} se déplace vers {self.trajet[0]}.")
            self.dist_restante -= self.vitesse
            if self.dist_restante <= 0:
                if self.trajet[0] in GARES:
                    if len(self.trajet) != 1:
                        output(f"{self} ERREUR FAINEANT.")
                    self.status = Status.GARE
                    output(f"{self} Vient d'arriver en gare de {self.trajet[0]}.")
                elif self.trajet[0] in ENTREPOTS:
                    output(f"{self} Vient d'arriver en entrepot de {self.trajet[0]}.")
                    output(f"{self} Chargement automatique.")
                    i = 0
                    while i < len(self.veut):
                        if self.trajet[0].donner(self, self.veut[i]):
                            self.veut.pop(i)
                        else:
                            i += 1
                    self.status = Status.MISSION
                    output(f"{self} Chargé.")
                elif self.trajet[0] in LIVRAISONS:
                    self.larguer(self.trajet[0].objet.nom)
                    output(f"{self} Livraison {self.trajet[0]} effectuée.")
                    self.trajet[0].status = Status.EFFECTUEE
                else:
                    output(f"{self} ERREUR PERDU.")
                self.coos = self.trajet[0].coos
                self.trajet.pop(0)
                if len(self.trajet) == 0:
                    self.dist_restante = 0
                else:
                    self.dist_restante = dist(self.coos, self.trajet[0].coos)
            else:
                self.recalc_coos(self.trajet[0], self.vitesse)

    def __str__(self):
        return f"[DRONE {self.id}]"

# ----------------------
# | COEUR DU PROGRAMME |
# ----------------------

try:
    with open(sys.argv[1], "r") as f:
        data = json.load(f)
except:
    sys.exit("Please specify which file to use like: python drones_simu.py config.json")

for x in data["objets"]:
    Objet(x["nom"], x["masse"])
for x in data["entrepots"]:
    Entrepot((x["x"], x["y"]), [OBJETS[i] for i in x["objets"]])
for x in data["gares"]:
    Gare((x["x"], x["y"]))
for x in data["drones"]:
    Drone((x["x"], x["y"]), x["charge"], x["batterie"], x["vitesse"], x["vitesse_charge"])
for x in data["livraisons"]:
    Livraison((x["x"], x["y"]), OBJETS[x["objet"]])

temps = 0
while not check_livraisons():
    temps += 1
    for x in DRONES:
        x.tick()
output(f"Mission achevée en {temps} ticks !")
