# Projet IA03

Ce projet permet de capturer un flux vidéo, de le traiter avec un modèle YOLOv8, puis de le diffuser vers une interface web de supervision.

Il est composé de :
- `socket_feed.py` : gestion du flux vidéo en socket TCP
- `traitement.py` : traitement de la vidéo avec YOLO et exposition des endpoints HTTP
- `interface.js` : serveur web qui sert l’interface utilisateur et agit comme passerelle vers le traitement
- `public/` : fichiers frontend de l’interface utilisateur
- `model/` : modèles YOLO disponibles

## Prérequis

- Python 3.11
- Node.js
- Un environnement avec les dépendances Python installées

## Installation des dépendances

### 1. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 2. Installer Node.js

Installez Node.js et npm si ce n’est pas déjà fait.

Vérification :

```bash
node -v
npm -v
```

puis 

```bash
npm install
```

## Structure du projet

```text
Projet_IA03/
├── interface.js
├── traitement.py
├── socket_feed.py
├── requirements.txt
├── readme.md
├── public/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── model/
│   ├── yolov8n.pt
│   ├── yolov8s.pt
│   └── readme.md
└── ...
```

## Description des composants

### `socket_feed.py`

Ce script permet de :
- démarrer un serveur socket pour diffuser un flux vidéo,
- ou un client pour recevoir ce flux,
- et afficher l’image reçue localement.

### `traitement.py`

Ce script :
- lit un flux vidéo entrant,
- applique un modèle YOLOv8 (yolov8n ou yolov8s),
- détecte des objets selon une classe et un seuil de confiance,
- rediffuse l’image traitée via des flux HTTP et sockets.

Il expose aussi plusieurs endpoints API pour contrôler :
- le modèle utilisé,
- la classe cible,
- la résolution,
- le seuil de confiance,
- la caméra source.

### `interface.js`

Ce script lance un serveur web permettant :
- de servir l’interface utilisateur,
- de communiquer avec `traitement.py`,
- d’afficher le flux vidéo et de contrôler les paramètres de détection.

## Lancement

*Dans cette ordre, il est à la discrétion de l'utilisateur d'adapter les arguments*

### Démarrer le flux socket

Mode serveur :

```bash
python socket_feed.py --host 0.0.0.0 --port 2500 --server
```

Mode client :

```bash
python socket_feed.py --host 0.0.0.0 --port 2500 --client
```

### Démarrer le traitement

```bash
python traitement.py --host_in 0.0.0.0 --port_in 2500 --host_out 0.0.0.0 --port_out 2501 --port_web 8080
```

### Démarrer l’interface web

```bash
node interface.js --ip 0.0.0.0 --port_traitement 8080 --port_interface 3000
```

Ensuite, ouvrez l’URL suivante dans le navigateur :

```text
http://localhost:3000
```

## Modèles disponibles

Le dossier `model/` contient :
- `yolov8n.pt`
- `yolov8s.pt`

Le programme peut basculer entre ces deux modèles selon les réglages de l’interface ou des endpoints.

## Notes

- Les ports doivent être compatibles entre les composants du projet.
- Le flux vidéo doit être correctement configuré entre le serveur source et le traitement.
- L’interface Node.js sert de passerelle entre l’utilisateur et l’API Flask de `traitement.py`.

## Auteur

G.Genevois, D.Ezhova, N.Coiffin, P.Ribet
