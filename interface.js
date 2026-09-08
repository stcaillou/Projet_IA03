const express = require('express');
const axios = require('axios');
const path = require('path');
var dev = require("ip")
const app = express();

//-----------------------------------------

const args = process.argv.slice(2);

const ipIndex = args.indexOf("--ip");
const ip = ipIndex !== -1 ? args[ipIndex + 1] : undefined;

const portIndex = args.indexOf("--port_traitement");
const port = portIndex !== -1 ? args[portIndex + 1] : undefined;

const portITIndex = args.indexOf("--port_interface");
const portIT = portITIndex !== -1 ? args[portITIndex + 1] : undefined;

if (ip == undefined || port == undefined || portIT == undefined){
    console.log("Mettre l'ip avec --ip et port_traitement avec --port_traitement et port_interface avec --port_interface")
    process.exit(1);
}

const FLASK_URL = 'http://'+ip +':' + port;
const PORT = portIT; 

//-----------------------------------------

/*
    Les endpoints déclaré dans se fichier font écho à ceux déclarer dans traitement.py
    Ici on ne réalise qu'une passerelle entre deux ordinateurs, celui ayant traitement.py et celui qui dessert l'interface utilisateur
*/

app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));

app.get('/camera', (req,res) => {
    res.redirect(FLASK_URL + "/camera");
})

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/class-info', async (req, res) => {
    try {
        const response = await axios.get(`${FLASK_URL}/class_info`);
        res.json({ success: true, classNames: response.data.message });
    } catch (error) {
        res.json({ success: false, message: "Erreur lors de la récupération des classes." });
    }
});

app.post('/change-model', async (req, res) => {
    try {
        const response = await axios.get(`${FLASK_URL}/change_model`);
        res.json({ success: true, message: "Modèle changé avec succès.", classNames: response.data.message });
    } catch (error) {
        res.json({ success: false, message: "Erreur lors du changement de modèle." });
    }
});

app.post('/change-class', async (req, res) => {
    const classId = req.body.classId;
    try {
        const response = await axios.get(`${FLASK_URL}/change_class`, { params: { class: classId } });
        res.json({ success: true, message: "Classe changée avec succès.", classNames: response.data.message });
    } catch (error) {
        res.json({ success: false, message: "Erreur lors du changement de classe." });
    }
});

app.post('/change-res', async (req, res) => {
    const resolution = req.body.resolution;
    try {
        await axios.get(`${FLASK_URL}/change_res`, { params: { res: resolution } });
        res.json({ success: true, message: `Résolution changée avec succès (${resolution} px).` });
    } catch (error) {
        res.json({ success: false, message: "Erreur lors du changement de résolution." });
    }
});

app.post('/change-conf', async (req, res) => {
    const confidence = req.body.confidence;
    try {
        const response = await axios.get(`${FLASK_URL}/change_conf?conf=${confidence}`);
        res.json({ success: true, message: "Seuil de confiance changé avec succès." });
    } catch (error) {
        res.json({ success: false, message: "Erreur lors du changement de seuil de confiance." });
    }
});

app.post('/set_ip', async (req, res) => {
    const ip = req.body.ip;
    const port = req.body.port;
    try {
        const response = await axios.get(`${FLASK_URL}/set_ip?ip=${ip}&port=${port}`);
        res.json({ success: true, message: "Camera changé avec succès." });
    } catch (error) {
        res.json({ success: false, message: "Erreur lors du changement de la camera." });
    }
});


app.listen(PORT, () => {console.log(`Serveur web démarré sur http://${dev.address()}:${PORT}`)})