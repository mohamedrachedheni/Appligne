// Fonction pour redimensionner les textarea selon leur contenu
function adjustTextareaHeight(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight - 2) + 'px';
}

// Fonction pour gérer l'affichage des étoiles
function updateStarRatings() {
    document.querySelectorAll('[id^="value_id_"][data-group="temoignage"]').forEach(inputElement => {
        const temoignageId = inputElement.id.split('_')[2];
        const evaluation = parseInt(inputElement.value);

        for (let i = 1; i <= 5; i++) {
            const star = document.getElementById(`id_${temoignageId}_t${i}`);
            if (star) {
                star.style.color = i <= evaluation ? 'rgb(0, 200, 255)' : 'grey';
            }
        }
    });

    const profInput = document.querySelector('[data-group="professeur"]');
    if (profInput) {
        const evaluationProf = parseInt(profInput.value);

        for (let i = 1; i <= 5; i++) {
            const star = document.getElementById(`t${i}`);
            if (star) {
                star.style.color = i <= evaluationProf ? 'rgb(0, 200, 255)' : 'grey';
            }
        }
    }
}

function rate(value, id, group) {
    const labels = ["Mauvais", "Moyen", "Bien", "Très bien", "Excellent"];
    const prefix = group === 'temoignage' ? `id_${id}_t` : `id_t`;

    for (let i = 1; i <= 5; i++) {
        const star = document.getElementById(`${prefix}${i}`);
        if (star) {
            star.style.color = i <= value ? 'rgb(0, 100, 255)' : 'grey';
        }
    }

    if (group === 'temoignage') {
        document.getElementById(`label_${id}`).innerText = labels[value - 1];
        document.getElementById(`value_id_${id}`).value = value;
    } else if (group === 'professeur') {
        document.getElementById('label_prof').innerText = labels[value - 1];
        document.getElementById('value_id_prof').value = value;
    }
}

// Fonction pour restaurer l'état des étoiles pour chaque groupe en fonction de la valeur précédente
function restorePreviousRating() {
    document.querySelectorAll('[id^="value_id_"]').forEach(inputElement => {
        const id = inputElement.id.includes('prof') ? 'prof' : inputElement.id.split('_')[2];
        const previousValue = parseInt(inputElement.value);
        const group = inputElement.getAttribute('data-group');

        if (previousValue && group) {
            rate(previousValue, id, group);
        }
    });
}
