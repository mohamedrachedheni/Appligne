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
    // Récupère la valeur de l'évaluation précédente dans le champ caché
    var previousValue = document.getElementById('temoignage-value').value;

    // Si une ancienne valeur existe, appliquez la note aux étoiles
    if (previousValue) {
        rate(parseInt(previousValue));
    }
}

// Appelle la fonction restorePreviousRating lorsque la page est chargée
window.onload = function() {
    restorePreviousRating();
};

document.addEventListener("DOMContentLoaded", function() {
    // Récupérer la page enregistrée dans localStorage
    var savedPage = localStorage.getItem('currentPage');
    
    // Si une page est enregistrée, donner le focus au lien de cette page
    if (savedPage) {
        var pageLink = document.querySelector('.pagination a.page-link[href="?page=' + savedPage + '"]');
        if (pageLink) {
            pageLink.focus();
        }
    }

    // Ajouter un écouteur d'événements sur chaque lien de pagination
    var pageLinks = document.querySelectorAll('.pagination a.page-link');
    pageLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            var pageNumber = this.getAttribute('href').split('page=')[1];
            // Enregistrer la page cliquée dans localStorage
            localStorage.setItem('currentPage', pageNumber);
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Parcourir tous les témoignages ayant l'ID qui commence par 'value_id_'
    document.querySelectorAll('[id^="value_id_"]').forEach(function(inputElement) {
        let temoignageId = inputElement.id.split('_')[2]; // Récupère l'ID du témoignage
        let evaluation = parseInt(inputElement.value); // Récupère la note d'évaluation
        
        // Parcourir les étoiles associées à ce témoignage
        for (let i = 1; i <= 5; i++) {
            let star = document.getElementById(`id_${temoignageId}_t${i}`);
            
            if (i <= evaluation) {
                // Active les étoiles correspondant à la note avec !important
                star.style.setProperty('color', 'rgb(0, 200, 255)', 'important');
            } else {
                // Désactive les étoiles au-dessus de la note avec !important
                star.style.setProperty('color', 'grey', 'important');
            }
        }
    });
});




