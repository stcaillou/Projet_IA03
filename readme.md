##-----------------------------------------
Installation des dépendances

-> Python : 

-> (NodeJS : Nécessaire pour l'interface web) : 



##-----------------------------------------

Lancement des programmes 


socket_feed.py 
-> Crée un serveur / client pour envoyer / lire le flux d'une caméra

traitement.py
-> Permet de traiter le flux vidéo d'une caméra pour appliquer YOLO dessus
        -> Renvoie l'image sous forme d'un serveur avec un flux vidéo ( lecture possible avec socket_feed )
        -> Renvoie l'image par trame http

interface.js
-> Permet de mettre en place un serveur web qui sert une interface web de contrôle
        -> Elle simplifie l'interaction entre l'utilisateur et l'api déservi par traitement.py

##-----------------------------------------
