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

document.addEventListener("DOMContentLoaded", function() {
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


// Combine les deux onload et DOMContentLoaded dans une seule fonction
window.onload = function() {
    restorePreviousRating(); // Appelle la fonction pour restaurer les étoiles
};