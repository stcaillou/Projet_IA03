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

const classSelect = document.getElementById('classId');

function populateClasses(classNames) {
    if (!classNames) return;
    const previous = classSelect.value;
    const entries = Object.entries(classNames)
        .sort((a, b) => Number(a[0]) - Number(b[0]));

    classSelect.innerHTML = '';
    for (const [id, name] of entries) {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = name;
        classSelect.appendChild(option);
    }
    classSelect.disabled = entries.length === 0;
    if (previous && classSelect.querySelector(`option[value="${previous}"]`)) {
        classSelect.value = previous;
    }
}

async function loadClasses() {
    try {
        const response = await fetch('/class-info');
        const data = await response.json();
        if (data.success) {
            populateClasses(data.classNames);
        } else {
            classSelect.innerHTML = '<option value="">Classes indisponibles</option>';
            showMessage(data.message, false);
        }
    } catch (error) {
        classSelect.innerHTML = '<option value="">Classes indisponibles</option>';
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
    const classId = classSelect.value;
    if (!classId) {
        showMessage("Veuillez sélectionner une classe.", false);
        return;
    }
    const data = await post('/change-class', `classId=${encodeURIComponent(classId)}`);
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
