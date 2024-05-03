
// ****************************  pour plusieur pages   debut  ***********************
    // fonction pour supprimer un champ div pour un diplome
    function supprimerDiv(divId) {
        var div = document.getElementById(divId);
        if (div) {
            div.parentNode.removeChild(div);
        }
    }

//****************************  liste déroulante de diplome  début ************************/
// Fonction pour mettre à jour la valeur de l'input lorsque l'utilisateur sélectionne un élément dans la liste déroulante
function updateInputValue(event) {
    // Récupérer l'ID de l'input associé à la liste déroulante
    var inputId = event.target.closest('.dropdown').querySelector('input[type="text"]').id;
    // Récupérer la valeur sélectionnée dans la liste déroulante
    var selectedValue = event.target.getAttribute('data-value');
    // Mettre à jour la valeur de l'input avec la valeur sélectionnée
    document.getElementById(inputId).value = selectedValue;

    // Masquer le menu déroulant après la sélection
    var dropdown = event.target.closest('.dropdown-menu');
    dropdown.style.display = 'none';
}

// Ajout d'un écouteur d'événements à chaque élément de la liste déroulante pour détecter le clic sur un élément
document.addEventListener('DOMContentLoaded', function () {
    // Sélectionner tous les éléments de la liste déroulante
    var dropdownItems = document.querySelectorAll('ul.dropdown-menu a.dropdown-item');
    dropdownItems.forEach(function(item) {
        // Ajouter un gestionnaire d'événements à chaque élément de la liste déroulante
        item.addEventListener('click', function(event) {
            // Appeler la fonction pour mettre à jour la valeur de l'input
            updateInputValue(event);
            // Empêcher le comportement par défaut du lien
            event.preventDefault();
        });
    });
});

// Ajout d'un gestionnaire d'événements pour masquer le menu déroulant lorsque l'utilisateur clique en dehors
document.addEventListener('click', function(event) {
    // Sélectionner tous les menus déroulants
    var dropdowns = document.querySelectorAll('.dropdown-menu');
    dropdowns.forEach(function(dropdown) {
        // Vérifier si l'événement click est en dehors du menu déroulant
        if (!dropdown.contains(event.target)) {
            // Masquer le menu déroulant si l'événement click est en dehors
            dropdown.style.display = 'none';
        }
    });
});

// Ajout d'un écouteur d'événements à chaque input pour afficher le menu déroulant
document.addEventListener('DOMContentLoaded', function () {
    // Sélectionner tous les inputs de type texte
    var inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(function(input) {
        // Ajouter un gestionnaire d'événements à chaque input
        input.addEventListener('click', function(event) {
            // Afficher le menu déroulant correspondant à l'input cliqué
            var dropdown = input.parentElement.querySelector('.dropdown-menu');
            dropdown.style.display = 'block';
            // Empêcher la propagation de l'événement click jusqu'au document
            event.stopPropagation();
        });
    });
});

//****************************  liste déroulante de diplome  fin ************************/