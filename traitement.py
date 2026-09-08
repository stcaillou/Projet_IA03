import argparse
import socket
import pickle
import struct
import cv2
import numpy as np
import sys
from ultralytics import YOLO
import threading
import time
from flask import Flask, jsonify, request, Response

#--------------------------------------------------

changed = True

HAS_CHANGED = False
HOST_IN = ""
PORT_IN = 0

clients = []
clients_lock = threading.Lock()

CONFIDENCE_THRESHOLD = 0.8

model = YOLO("model/yolov8n.pt", verbose=False)
class_yolo = 0
resolution = 320
buffer_to_send = b''

#--------------------------------------------------

app = Flask(__name__)

# Permet de basculer entre les deux modèles disponibles
@app.route("/change_model", methods=["GET"]) 
def change_model(): 
    global changed
    global model
    if changed:
        model = YOLO("model/yolov8n.pt", verbose=False)
        changed = False
    else:
        changed = True
        model = YOLO("model/yolov8s.pt", verbose=False)
    return jsonify({ "message": model.names})

# Permet de changer la classe à détecter
@app.route("/change_class", methods=["GET"])
def change_class():
    global model
    global class_yolo
    class_yolo = int(request.args.get('class'))
    return jsonify({ "message": model.names})

# Permet de changer la résolution d'inférence
@app.route("/change_res", methods=["GET"])
def change_res():
    global resolution
    class_yolo = int(request.args.get('res'))
    return jsonify({ "message": "ok"})

# Permet de récupérer les classes disponibles dans le modèle
@app.route("/class_info", methods=["GET"])
def class_info():
    global model
    return jsonify({ "message": model.names})


# Permet de changer le seuil de confiance
@app.route("/change_conf", methods=["GET"])
def change_conf():
    global CONFIDENCE_THRESHOLD
    CONFIDENCE_THRESHOLD = float(request.args.get('conf'))
    return jsonify({ "message": "ok"})


# Permet d'éviter les problèmes de concurrence
buffer_lock = threading.Lock()

def generate_frames():
    global buffer_to_send
    while True:
        with buffer_lock:
            if buffer_to_send: 
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer_to_send + b'\r\n')
        time.sleep(0.03)

# Permet de récupérer la caméra sous forme d'une image JPEG qui s'actualise en continu
@app.route("/camera", methods=["GET"])
def display_camera():
    return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

# Permet de modifier l'IP du serveur caméra
@app.route("/set_ip", methods=["GET"])
def set_ip():
    global HOST_IN
    global PORT_IN
    HOST_IN = request.args.get('ip')
    PORT_IN = int(request.args.get('port'))
    global HAS_CHANGED
    HAS_CHANGED = True
    print("TEST")
    return

#----------------------------------------------------

def accept_clients(server_socket):
    while True:
        try:
            client_socket_1, addr = server_socket.accept()
            with clients_lock:
                clients.append(client_socket_1)
        except OSError:
            break

def start_server(host_in='localhost', port_in=2500, host_out='localhost', port_out=2500):
    global buffer_to_send
    global HAS_CHANGED
    HAS_CHANGED = False
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host_out, port_out))
    server_socket.listen(5)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host_in, port_in))

    threading.Thread(target=accept_clients,args=(server_socket,),daemon=True).start()

    try:
        while not HAS_CHANGED:  # Permet de changer la caméra

            # Réception du flux vidéo -------------------------------
            data_size = struct.unpack("Q", client_socket.recv(8))[0]
            if not data_size:
                break
            
            received_data = b""
            while len(received_data) < data_size:
                packet = client_socket.recv(data_size - len(received_data))
                if not packet:
                    break
                received_data += packet
            
            frame = cv2.imdecode(np.frombuffer(received_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                    break

            # Détection des éléments avec le modèle ------------------
            detections = model(frame, verbose=False, classes=[class_yolo], imgsz=resolution)[0]
            
            for box in detections.boxes:
                label = model.names.get(box.cls.item())
                confidence = box.data.tolist()[0][4]
            
                if confidence > CONFIDENCE_THRESHOLD:
                    xmin, ymin, xmax, ymax = map(int, box.data.tolist()[0][:4])
                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)

            # Compression de l'image ----------------------------------
            success, buffer = cv2.imencode(".jpg",frame,[cv2.IMWRITE_JPEG_QUALITY, 80])

            if not success:
                continue

            data = buffer.tobytes()
            with buffer_lock:
                    buffer_to_send = data


            message = struct.pack("Q", len(data)) + data

            disconnected_clients = []

            with clients_lock:
                current_clients = clients.copy()

            # Gestion des envois clients et des déconnexions ----------
            for client_socket_i in current_clients:
                try:
                    client_socket_i.sendall(message)

                except (BrokenPipeError, ConnectionResetError, OSError):
                    disconnected_clients.append(client_socket_i)

            if disconnected_clients:
                with clients_lock:
                    for client_socket_i in disconnected_clients:

                        if client_socket in clients:
                            clients.remove(client_socket_i)

                        try:
                            client_socket.close()
                        except OSError:
                            pass

    except KeyboardInterrupt:
        None
    finally:

        with clients_lock:
            for client_socket in clients:
                try:
                    client_socket.close()
                except OSError:
                    pass

        server_socket.close()


#----------------------------------------------------

def launch_app(port):
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transmission vidéo via socket (serveur/client)")
    parser.add_argument("--host_in", type=str, default="0.0.0.0", help="Adresse IP du flux vidéo d'entrée (par défaut : 0.0.0.0)")
    parser.add_argument("--port_in", type=int, default=2500, help="Port du flux vidéo d'entrée (par défaut : 2500)")
    parser.add_argument("--host_out", type=str, default="0.0.0.0", help="Adresse IP du serveur de sortie du flux vidéo (par défaut : 0.0.0.0)")
    parser.add_argument("--port_out", type=int, default=2500, help="Port du serveur de sortie du flux vidéo (par défaut : 2500)")
    parser.add_argument("--port_web", type=int, default=8080, help="Port du serveur web de l'interface (par défaut : 8080)")
    args = parser.parse_args()
    threading.Thread(target=launch_app, args=[args.port_web],daemon=True).start()
    HOST_IN = args.host_in
    PORT_IN = args.port_in
    while True:
        start_server(HOST_IN, PORT_IN, args.host_out, args.port_out)
