# Modèles YOLO

Ce dossier contient les fichiers de poids des modèles YOLOv8 utilisés par le projet.

## Modèles disponibles

- `yolov8n.pt` : version légère, plus rapide, adaptée aux ressources limitées
- `yolov8s.pt` : version plus puissante, avec un meilleur compromis précision / performance

## Téléchargement

Les poids officiels peuvent être téléchargés depuis la page Ultralytics YOLOv8 :

https://huggingface.co/Ultralytics/YOLOv8/tree/main

## Remarque

Placez ici les fichiers `.pt` avant de lancer le traitement. Le script `traitement.py` charge automatiquement les modèles présents dans ce dossier.