const messageDiv = document.getElementById('message');

function showMessage(text, isSuccess) {
    messageDiv.textContent = text;
    messageDiv.className = isSuccess ? 'success' : 'error';
}

async function post(url, body) {
    try {
        const options = { method: 'POST' };
        if (body) {
            options.headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
            options.body = body;
        }
        const response = await fetch(url, options);
        const data = await response.json();
        showMessage(data.message, !!data.success);
        return data;
    } catch (error) {
        showMessage("Erreur lors de la requête.", false);
        return null;
    }
}

const classList = document.getElementById('classList');

// Classes cochées au premier chargement (0 = person, valeur par défaut côté traitement.py)
const DEFAULT_CLASS_IDS = ['0'];
let classListInitialised = false;

// Retourne les identifiants des classes cochées
function getSelectedClasses() {
    return Array.from(classList.querySelectorAll('input[type="checkbox"]:checked'))
        .map((checkbox) => checkbox.value);
}

function showClassListMessage(text) {
    classList.innerHTML = '';
    const item = document.createElement('li');
    item.className = 'class-list-empty';
    item.textContent = text;
    classList.appendChild(item);
}

function populateClasses(classNames) {
    if (!classNames) return;
    // Au premier rendu, on coche les classes détectées par défaut par le modèle
    const selected = classListInitialised ? getSelectedClasses() : DEFAULT_CLASS_IDS;
    const entries = Object.entries(classNames)
        .sort((a, b) => Number(a[0]) - Number(b[0]));

    if (entries.length === 0) {
        showClassListMessage("Aucune classe disponible");
        return;
    }

    classList.innerHTML = '';
    for (const [id, name] of entries) {
        const item = document.createElement('li');
        const label = document.createElement('label');
        const checkbox = document.createElement('input');

        checkbox.type = 'checkbox';
        checkbox.value = id;
        checkbox.checked = selected.includes(id);

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(`${name} (${id})`));
        item.appendChild(label);
        classList.appendChild(item);
    }
    classListInitialised = true;
}

async function loadClasses() {
    try {
        const response = await fetch('/class-info');
        const data = await response.json();
        if (data.success) {
            populateClasses(data.classNames);
        } else {
            showClassListMessage("Classes indisponibles");
            showMessage(data.message, false);
        }
    } catch (error) {
        showClassListMessage("Classes indisponibles");
        showMessage("Erreur lors de la récupération des classes.", false);
    }
}
loadClasses();

const confidenceInput = document.getElementById('confidence');
const confidenceValue = document.getElementById('confidenceValue');
const ipEntry = document.getElementById('ipEntry');
const portEntry = document.getElementById('portEntry');

function renderConfidence() {
    confidenceValue.textContent = Number(confidenceInput.value).toFixed(2);
}
confidenceInput.addEventListener('input', renderConfidence);
renderConfidence();

document.getElementById('changeModelBtn').addEventListener('click', async () => {
    const data = await post('/change-model');
    if (data && data.success) populateClasses(data.classNames);
});

document.getElementById('changeClassBtn').addEventListener('click', async () => {
    const classIds = getSelectedClasses();

    if (classIds.length === 0) {
        showMessage("Veuillez sélectionner au moins une classe.", false);
        return;
    }
    const body = classIds
        .map((classId) => `classId=${encodeURIComponent(classId)}`)
        .join('&');
    const data = await post('/change-class', body);
    if (data && data.success) populateClasses(data.classNames);
});

document.getElementById('changeResBtn').addEventListener('click', () => {
    const resolution = document.getElementById('resolution').value;
    post('/change-res', `resolution=${encodeURIComponent(resolution)}`);
});

document.getElementById('changeConfBtn').addEventListener('click', () => {
    const confidence = confidenceInput.value;
    post('/change-conf', `confidence=${encodeURIComponent(confidence)}`);
});

document.getElementById('changeCamera').addEventListener('click', () => {
    const ip = ipEntry.value;
    const port = portEntry.value;
    post('/set_ip', `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`);
});
