#!/bin/bash
# Script de lancement de l'interface mobile de contrôle simulation
# Usage: ./start_mobile.sh

set -e

echo "=== Lancement de l'interface mobile de contrôle simulation ==="
echo ""

# Naviguer vers le dossier mobile
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/mobile"

# Vérifier que npm est installé
if ! command -v npm &> /dev/null; then
    echo "❌ npm n'est pas installé. Installez Node.js d'abord."
    exit 1
fi

# Vérifier/créer le fichier .env
if [ ! -f ".env" ]; then
    echo "⚠️  Fichier .env manquant. Création..."
    cat > .env << 'EOF'
EXPO_PUBLIC_API_URL=http://localhost:8080
EOF
    echo "✅ Fichier .env créé avec EXPO_PUBLIC_API_URL=http://localhost:8080"
    echo "   Si vous testez depuis un appareil physique, modifiez cette URL."
    echo ""
fi

# Installer les dépendances si nécessaire
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances npm..."
    npm install
    echo ""
fi

# Vérifier et installer react-dom pour le support web
if [ ! -d "node_modules/react-dom" ]; then
    echo "📦 Installation de react-dom pour le support web..."
    npx expo install react-dom
    echo ""
fi

# Demander le mode de lancement (défaut: web)
echo "Choisissez le mode de lancement:"
echo "  1) Web (navigateur - recommandé pour tests) [DÉFAUT]"
echo "  2) Android (émulateur/appareil)"
echo "  3) iOS (simulateur macOS uniquement)"
echo ""
read -p "Votre choix [1-3] (Entrée = Web): " choice

# Défaut = 1 si vide
choice=${choice:-1}

case $choice in
    1)
        echo "🚀 Lancement de la version web..."
        npm run web
        ;;
    2)
        echo "🚀 Lancement sur Android..."
        npm run android
        ;;
    3)
        echo "🚀 Lancement sur iOS..."
        npm run ios
        ;;
    *)
        echo "❌ Choix invalide. Lancement de la version web par défaut..."
        npm run web
        ;;
esac
