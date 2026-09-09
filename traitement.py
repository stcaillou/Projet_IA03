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
classes_yolo = [0]
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
    return jsonify({"message": model.names})

# Permet de changer les classes à détecter
@app.route("/change_class", methods=["GET"])
def change_class():
    global model
    global classes_yolo
    try:
        # Les classes peuvent arriver soit répétées (class=0&class=2), soit séparées par des virgules (class=0,2)
        raw_values = request.args.getlist("class")
        if not raw_values:
            return jsonify({"message": "Paramètre 'class' manquant"}), 400

        selected = []
        for raw_value in raw_values:
            for part in str(raw_value).split(","):
                part = part.strip()
                if part == "":
                    continue
                class_id = int(part)
                if class_id not in selected:
                    selected.append(class_id)

        if not selected:
            return jsonify({"message": "Aucune classe sélectionnée", "classes": model.names}), 400

        unknown = [class_id for class_id in selected if class_id not in model.names]
        if unknown:
            return jsonify({"message": "Classe inexistante", "unknown": unknown, "classes": model.names}), 400

        classes_yolo = selected
        print(classes_yolo)
        return jsonify({
            "message": model.names,
            "selected_classes": classes_yolo,
            "selected_names": [model.names[class_id] for class_id in classes_yolo],
        })
    except (TypeError, ValueError):
        return jsonify({"message": "Paramètre 'class' invalide"}), 400

# Permet de changer la résolution d'inférence
@app.route("/change_res", methods=["GET"])
def change_res():
    global resolution
    try:
        resolution = int(request.args.get("res"))
        return jsonify({"message": "ok", "resolution": resolution})
    except (TypeError, ValueError):
        return jsonify({"message": "Paramètre 'res' invalide"}), 400

# Permet de récupérer les classes disponibles dans le modèle
@app.route("/class_info", methods=["GET"])
def class_info():
    global model
    return jsonify({"message": model.names})

# Permet de changer le seuil de confiance
@app.route("/change_conf", methods=["GET"])
def change_conf():
    global CONFIDENCE_THRESHOLD
    try:
        CONFIDENCE_THRESHOLD = float(request.args.get("conf"))
        CONFIDENCE_THRESHOLD = max(0, min(1, CONFIDENCE_THRESHOLD))
        return jsonify({"message": "ok", "confidence": CONFIDENCE_THRESHOLD})
    except (TypeError, ValueError):
        return jsonify({"message": "Paramètre 'conf' invalide"}), 400

# Permet d'éviter les problèmes de concurrence
buffer_lock = threading.Lock()

def generate_frames():
    global buffer_to_send
    while True:
        with buffer_lock:
            if buffer_to_send:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer_to_send + b'\r\n'
        time.sleep(0.03)

# Permet de récupérer la caméra sous forme d'une image JPEG qui s'actualise en continu
@app.route("/camera", methods=["GET"])
def display_camera():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Permet de modifier l'IP du serveur caméra
@app.route("/set_ip", methods=["GET"])
def set_ip():
    global HOST_IN
    global PORT_IN
    global HAS_CHANGED
    try:
        HOST_IN = request.args.get("ip")
        PORT_IN = int(request.args.get("port"))
        HAS_CHANGED = True
        print(f"Changement de caméra demandé : {HOST_IN}:{PORT_IN}")
        return jsonify({"message": "ok", "ip": HOST_IN, "port": PORT_IN})
    except (TypeError, ValueError):
        return jsonify({"message": "IP ou port invalide"}), 400

#----------------------------------------------------

def recv_all(sock, size):
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

def accept_clients(server_socket):
    while True:
        try:
            client_socket_1, addr = server_socket.accept()
            print(f"Nouveau client connecté : {addr}")
            with clients_lock:
                clients.append(client_socket_1)
        except OSError:
            break

def start_server(host_in='localhost', port_in=2500, host_out='localhost', port_out=2501):
    global buffer_to_send
    global HAS_CHANGED

    HAS_CHANGED = False

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host_out, port_out))
    server_socket.listen(5)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((host_in, port_in))
    except Exception as e:
        print(f"[ERREUR] Impossible de se connecter à la caméra : {e}")
        client_socket.close()
        server_socket.close()
        return

    threading.Thread(target=accept_clients, args=(server_socket,), daemon=True).start()

    fps_start_time = time.time()
    fps_frame_count = 0
    fps = 0.0

    try:
        while not HAS_CHANGED:

            # Réception du flux vidéo -------------------------------
            size_data = recv_all(client_socket, 8)
            if size_data is None:
                break

            data_size = struct.unpack("Q", size_data)[0]
            if not data_size:
                break

            received_data = recv_all(client_socket, data_size)
            if received_data is None:
                break

            frame = cv2.imdecode(np.frombuffer(received_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                break

            # Détection des éléments avec le modèle ------------------
            detections = model(frame, verbose=False, classes=list(classes_yolo), imgsz=resolution)[0]
            object_count = 0

            for box in detections.boxes:
                confidence = float(box.conf.item())

                if confidence >= CONFIDENCE_THRESHOLD:
                    object_count += 1
                    class_id = int(box.cls.item())
                    label = model.names.get(class_id, "Objet")
                    xmin, ymin, xmax, ymax = map(int, box.xyxy[0].tolist())

                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                    cv2.putText(frame, f"{label} {confidence:.2f}", (xmin, max(ymin - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            fps_frame_count += 1
            elapsed_time = time.time() - fps_start_time

            if elapsed_time >= 1.0:
                fps = fps_frame_count / elapsed_time
                fps_frame_count = 0
                fps_start_time = time.time()

            cv2.rectangle(frame, (5, 5), (280, 85), (0, 0, 0), -1)
            cv2.putText(frame, f"FPS : {fps:.1f}", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"Objets : {object_count}", (15, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Compression de l'image ----------------------------------
            success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

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
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    disconnected_clients.append(client_socket_i)

            if disconnected_clients:
                with clients_lock:
                    for client_socket_i in disconnected_clients:
                        if client_socket_i in clients:
                            clients.remove(client_socket_i)
                        try:
                            client_socket_i.close()
                        except OSError:
                            pass

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        with clients_lock:
            for client_socket_i in clients:
                try:
                    client_socket_i.close()
                except OSError:
                    pass
            clients.clear()

        try:
            client_socket.close()
        except OSError:
            pass

        try:
            server_socket.close()
        except OSError:
            pass

#----------------------------------------------------

def launch_app(port):
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transmission vidéo via socket (serveur/client)")
    parser.add_argument("--host_in", type=str, default="0.0.0.0", help="Adresse IP du flux vidéo d'entrée (par défaut : 0.0.0.0)")
    parser.add_argument("--port_in", type=int, default=2500, help="Port du flux vidéo d'entrée (par défaut : 2500)")
    parser.add_argument("--host_out", type=str, default="0.0.0.0", help="Adresse IP du serveur de sortie du flux vidéo (par défaut : 0.0.0.0)")
    parser.add_argument("--port_out", type=int, default=2501, help="Port du serveur de sortie du flux vidéo (par défaut : 2501)")
    parser.add_argument("--port_web", type=int, default=8080, help="Port du serveur web de l'interface (par défaut : 8080)")
    args = parser.parse_args()

    threading.Thread(target=launch_app, args=[args.port_web], daemon=True).start()

    HOST_IN = args.host_in
    PORT_IN = args.port_in

    while True:
        start_server(HOST_IN, PORT_IN, args.host_out, args.port_out)