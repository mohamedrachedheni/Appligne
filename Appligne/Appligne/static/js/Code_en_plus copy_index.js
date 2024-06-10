// Fonction pour mettre à jour la valeur de l'input lorsque l'utilisateur sélectionne un élément dans la liste déroulante
function updateInputValue(event) {
    var inputId = event.target.closest('.dropdown').querySelector('input[type="text"]').id;
    var selectedValue = event.target.getAttribute('data-value');
    document.getElementById(inputId).value = selectedValue;
    var dropdown = event.target.closest('.dropdown-menu');
    dropdown.style.display = 'none';
}

// Ajout d'un écouteur d'événements à chaque élément de la liste déroulante pour détecter le clic sur un élément
document.addEventListener('DOMContentLoaded', function () {
    var dropdownItems = document.querySelectorAll('ul.dropdown-menu a.dropdown-item');
    dropdownItems.forEach(function(item) {
        item.addEventListener('click', function(event) {
            updateInputValue(event);
            event.preventDefault();
        });
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

// Ajout d'un écouteur d'événements à chaque input pour afficher le menu déroulant
document.addEventListener('DOMContentLoaded', function () {
    var inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(function(input) {
        input.addEventListener('click', function(event) {
            var dropdown = input.parentElement.querySelector('.dropdown-menu');
            dropdown.style.display = 'block';
            event.stopPropagation();
        });
    });
});

// Ajout d'un gestionnaire d'événements pour soumettre le formulaire lors du clic sur un élément de la liste déroulante
document.addEventListener("DOMContentLoaded", function() {
    var dropdownRegion = document.getElementById("dropdownMenu_region_id");
    dropdownRegion.addEventListener("click", function(event) {
        event.preventDefault(); // Empêcher le comportement de lien par défaut
        var selectedRegion = event.target.getAttribute("data-value");
        document.getElementById("region_id").value = selectedRegion; // Mettre à jour la valeur de l'entrée cachée
        document.getElementById("index_id").submit(); // Soumettre le formulaire
    });
});

// Ajout d'un gestionnaire d'événements aux éléments de classe "form-check-input" pour actualiser le formulaire
document.addEventListener('DOMContentLoaded', function () {
    var checkboxes = document.querySelectorAll('.form-check-input');
    checkboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function(event) {
            checkboxes.forEach(function(input) {
                if (input !== checkbox) {
                    input.checked = false;
                }
            });
        });
    });
});


