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
