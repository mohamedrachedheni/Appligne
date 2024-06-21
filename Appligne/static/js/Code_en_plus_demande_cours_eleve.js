document.addEventListener('DOMContentLoaded', function() {


    //****************************  liste déroulante de diplôme  début ************************/

    // Fonction pour mettre à jour la valeur de l'input lorsque l'utilisateur sélectionne un élément dans la liste déroulante
    function updateInputValue(event) {
        var input = event.target.closest('.dropdown').querySelector('input[type="text"]');
        if (input) {
            var selectedValue = event.target.getAttribute('data-value');
            input.value = selectedValue;

            var dropdown = event.target.closest('.dropdown-menu');
            if (dropdown) {
                dropdown.style.display = 'none';
            }
        }
    }

    // Sélectionner tous les éléments de la liste déroulante
    var dropdownItems = document.querySelectorAll('ul.dropdown-menu a.dropdown-item');
    dropdownItems.forEach(function(item) {
        item.addEventListener('click', function(event) {
            updateInputValue(event);
            event.preventDefault();
        });
    });

    // Ajout d'un gestionnaire d'événements pour masquer le menu déroulant lorsque l'utilisateur clique en dehors
    document.addEventListener('click', function(event) {
        var dropdowns = document.querySelectorAll('.dropdown-menu');
        dropdowns.forEach(function(dropdown) {
            if (!dropdown.contains(event.target)) {
                dropdown.style.display = 'none';
            }
        });
    });

    // Sélectionner tous les inputs de type texte
    var inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(function(input) {
        input.addEventListener('click', function(event) {
            var dropdown = input.parentElement.querySelector('.dropdown-menu');
            if (dropdown) {
                dropdown.style.display = 'block';
            }
            event.stopPropagation();
        });
    });

    //****************************  liste déroulante de diplome  fin ************************/
    //******************** début actualiser le formulaire  ******************************** //

    // Ajouter un gestionnaire d'événements aux éléments de classe "form-check-input"
    var checkboxes = document.querySelectorAll('.form-check-input');
    checkboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function(event) {
            checkboxes.forEach(function(input) {
                if (input !== checkbox) {
                    input.checked = false;
                }
            });
            document.getElementById('demande_cours_id').submit();
        });
    });

    // Ajouter un gestionnaire d'événements aux éléments du menu déroulant
    var dropdownItemsDemande = document.querySelectorAll('.dropdown-item-demande');
    dropdownItemsDemande.forEach(function(item) {
        item.addEventListener('click', function(event) {
            event.preventDefault();
            var value = item.getAttribute('data-value');
            var inputId = item.getAttribute('data-target');

            var input = document.getElementById(inputId);
            if (input) {
                if (inputId === 'departement_id') {
                    input.value = '';
                } else {
                    input.value = value;
                }
            }
            document.getElementById('demande_cours_id').submit();
        });
    });

    // focus sur département suite à actualiser
    document.getElementById('departement_id').focus();
});
