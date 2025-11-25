from PIL import Image
import os
import numpy as np
path = "Heightmap.png"

print("Fichier existe :", os.path.exists(path))
print("Taille fichier :", os.path.getsize(path))

def save_array_to_csv(array: np.ndarray, filename: str):
    """
    Sauvegarde toutes les valeurs d'un tableau NumPy dans un fichier texte,
    avec des virgules entre chaque valeur.

    :param array: np.ndarray à sauvegarder
    :param filename: nom du fichier de sortie
    """
    # On aplatit le tableau pour avoir toutes les valeurs en 1D
    flat_array = array.flatten()
    
    # Convertir en chaîne séparée par des virgules
    line = ",".join(map(str, flat_array))
    
    # Écrire dans le fichier
    with open(filename, "w") as f:
        for row in array:
            line = ",".join(map(str, row))
            f.write(f"[{line}],\n")
    print(f"Tableau sauvegardé dans {filename}, {flat_array.size} valeurs.")

try:
    print(">>>load map...")
    img = Image.open(path)
    print("<<< map load")
    print("Mode :", img.mode)
    print("Taille :", img.size)
    img.load()
    print("Image chargée complètement")
    rgb = img.getpixel((0, 0))
    print (rgb)
    p = 288 * 100 / 65535
    hauteur = p * 205 / 100
    print (p, "/" , hauteur)
    matrix = np.array(img)
    print(matrix)
    save_array_to_csv(matrix, "array")
except Exception as e:
    print(">>>> ERREUR :", e)



