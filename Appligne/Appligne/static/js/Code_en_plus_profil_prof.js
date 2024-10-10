// Fonction pour gérer la note des étoiles
function rate(value) {
    // Met à jour la couleur des étoiles sélectionnées
    for (var i = 1; i <= 5; i++) {
        document.getElementById('t' + i).style.color = i <= value ? 'blue' : 'grey';
    }
    
    // Met à jour le texte du label en fonction de la valeur sélectionnée
    var labels = ["Mauvais", "Moyen", "Bien", "Très bien", "Excellent"];
    document.getElementById('t6').innerHTML = labels[value - 1];
    
    // Met à jour la valeur du champ caché
    document.getElementById('temoignage-value').value = value;
}

// Fonction pour restaurer l'état des étoiles en fonction de la valeur précédente
function restorePreviousRating() {
    var previousValue = document.getElementById('temoignage-value').value;

    if (previousValue) {
        rate(parseInt(previousValue));
    }
}

// Fonction pour redimensionner les textarea selon leur contenu
function adjustTextareaHeight() {
    const textareas = document.getElementsByClassName('form-control profil');

    for (let i = 0; i < textareas.length; i++) {
        const textarea = textareas[i];
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight - 2) + 'px';
    }
}

// Combine les deux onload et DOMContentLoaded dans une seule fonction
window.onload = function() {
    restorePreviousRating(); // Appelle la fonction pour restaurer les étoiles
    adjustTextareaHeight(); // Redimensionne les textarea
};

document.addEventListener("DOMContentLoaded", function() {
    // Gestion des liens de pagination avec localStorage
    var savedPage = localStorage.getItem('currentPage');
    if (savedPage) {
        var pageLink = document.querySelector('.pagination a.page-link[href="?page=' + savedPage + '"]');
        if (pageLink) {
            pageLink.focus();
        }
    }

    var pageLinks = document.querySelectorAll('.pagination a.page-link');
    pageLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            var pageNumber = this.getAttribute('href').split('page=')[1];
            localStorage.setItem('currentPage', pageNumber);
        });
    });

    // Redimensionne les textarea sur input
    document.addEventListener('input', adjustTextareaHeight);

    // Gestion des étoiles pour chaque témoignage
    document.querySelectorAll('[id^="value_id_"]').forEach(function(inputElement) {
        let temoignageId = inputElement.id.split('_')[2]; // Récupère l'ID du témoignage
        let evaluation = parseInt(inputElement.value); // Récupère la note d'évaluation
        
        for (let i = 1; i <= 5; i++) {
            let star = document.getElementById(`id_${temoignageId}_t${i}`);
            
            if (i <= evaluation) {
                star.style.setProperty('color', 'rgb(0, 200, 255)', 'important');
            } else {
                star.style.setProperty('color', 'grey', 'important');
            }
        }
    });
});
