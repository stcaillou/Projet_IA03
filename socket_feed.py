import argparse
import socket
import pickle
import struct
import cv2 as cv
import numpy as np
import sys
import threading

#-------------------------------------------------------------------------------------

clients = []
clients_lock = threading.Lock()

#-------------------------------------------------------------------------------------

def accept_clients(server_socket):
    r'''
        Cette méthode permet de rajouter les clients qui viennent de se connecter dans la liste
        des destinataire du flux vidéo du serveur associé.
    '''
    while True:
        try:
            client_socket, addr = server_socket.accept()
            with clients_lock:
                clients.append(client_socket)
        except OSError:
            break

def start_server(host='localhost', port=2500):
    r'''
        Cette méthode permet de mettre en place un serveur socket TCP qui envoie frame par frame
        le flux vidéo au différent client qui se connecte à lui.
    '''
    #On démarre le serveur socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)

    #On capture la vidéo de la caméra (Il est tout à fait possible de changer la source du flux vidéo)
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        sys.exit(1)

    threading.Thread(target=accept_clients,args=(server_socket,),daemon=True).start()

    try:
        #Cette boucle permet l'envoie des 'frames' capturer sur la caméra
        while True:

            ret, frame = cap.read()

            if not ret:
                break

            #On compresse l'image pour gagner en débit
            success, buffer = cv.imencode(".jpg",frame,[cv.IMWRITE_JPEG_QUALITY, 80])

            if not success:
                continue

            data = buffer.tobytes()
            message = struct.pack("Q", len(data)) + data

            disconnected_clients = []

            with clients_lock:
                current_clients = clients.copy()

            #On envoie la frame à chaque client connecter
            for client_socket in current_clients:
                try:
                    client_socket.sendall(message)

                except (BrokenPipeError, ConnectionResetError, OSError):
                    disconnected_clients.append(client_socket)

            #On retire les clients déconnecter de la liste des destinataire
            if disconnected_clients:
                with clients_lock:
                    for client_socket in disconnected_clients:

                        if client_socket in clients:
                            clients.remove(client_socket)

                        try:
                            client_socket.close()
                        except OSError:
                            pass

    except KeyboardInterrupt:
        pass
    finally:#Ici on termine la boucle de manière conventionnelle ( on ferme le serveur et on déconnecte les clients )
        cap.release()
        with clients_lock:
            for client_socket in clients:
                try:
                    client_socket.close()
                except OSError:
                    pass

        server_socket.close()

#-------------------------------------------------------------------------------------

def start_client(host='localhost', port=2500):
    r'''
        Cette méthode permet de mettre en place un client qui reçoit frame par frame le flux vidéo
        d'un serveur associé ( qui respecte la trame d'envoie )
    '''
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    try:
        while True:
            data_size = struct.unpack("Q", client_socket.recv(8))[0]
            if not data_size:
                break

            received_data = b""
            while len(received_data) < data_size:
                packet = client_socket.recv(data_size - len(received_data))
                if not packet:
                    break
                received_data += packet

            frame = cv.imdecode(np.frombuffer(received_data, dtype=np.uint8), cv.IMREAD_COLOR)
            if frame is None:
                break

            #Ici on affichage l'image côté client
            cv.imshow("", frame)
            if cv.waitKey(1) == ord('q'):
                break

    except KeyboardInterrupt:
        None
    finally:
        cv.destroyAllWindows()
        client_socket.close()


#------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transmission vidéo via socket (Serveur/Client)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Adresse IP (par défaut: localhost)")
    parser.add_argument("--port", type=int, default=2500, help="Port (par défaut: 2500)")
    parser.add_argument("--server", action="store_true", help="Mode serveur (envoi des images)")
    parser.add_argument("--client", action="store_true", help="Mode client (réception des images)")

    args = parser.parse_args()

    if args.server:
        start_server(args.host, args.port)
    elif args.client:
        start_client(args.host, args.port)
    else:
        sys.exit(1)
