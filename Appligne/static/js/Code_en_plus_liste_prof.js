/*********************** http://localhost:8000/liste_prof  début **************************** */

// Fonction pour modifier le texte et les prix en fonction de la réduction d'impôts
function toggleText() {
    const priceText = document.getElementById("priceText");
    const prixParHeureElements = document.querySelectorAll(".prix_par_heure");

    for (let i = 0; i < prixParHeureElements.length; i++) {
        const prixActuel = parseFloat(prixParHeureElements[i].innerHTML);
        const nouveauPrix01 = prixActuel * 0.5;
        const nouveauPrix02 = prixActuel * 2;

        if (document.getElementById("flexSwitchCheckChecked").checked) {
            priceText.innerHTML = "Prix <b>après</b> réduction d'impôts";
            prixParHeureElements[i].innerHTML = nouveauPrix01.toFixed(2);
        } else {
            priceText.innerHTML = "Prix <b>avant</b> réduction d'impôts";
            prixParHeureElements[i].innerHTML = nouveauPrix02.toFixed(2);
        }
    }
}

/*********************** http://localhost:8000/liste_prof  fin **************************** */

// Fonction pour mettre à jour la valeur de l'input lorsqu'un élément dans la liste déroulante est sélectionné
function updateInputValue(event) {
    const inputId = event.target.closest('.dropdown').querySelector('input[type="text"]').id;
    const selectedValue = event.target.getAttribute('data-value');
    document.getElementById(inputId).value = selectedValue;
    const dropdown = event.target.closest('.dropdown-menu');
    dropdown.style.display = 'none';
}

// Gestion des événements

document.addEventListener('DOMContentLoaded', function () {
    // Fonction pour afficher le menu déroulant
    function showDropdown(event) {
        const dropdown = event.currentTarget.parentElement.querySelector('.dropdown-menu');
        dropdown.style.display = 'block';
        event.stopPropagation();
    }

    // Sélectionne tous les inputs de type "text"
    const inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => {
        // Ajoute un événement 'click' et 'touchstart' à chaque input
        input.addEventListener('click', showDropdown);
        input.addEventListener('touchstart', showDropdown);
    });

    // Sélectionne tous les éléments de la liste déroulante
    const dropdownItems = document.querySelectorAll('ul.dropdown-menu a.dropdown-item');
    dropdownItems.forEach(item => {
        // Ajoute un événement 'click' et 'touchstart' à chaque élément de la liste déroulante
        item.addEventListener('click', function(event) {
            updateInputValue(event);
            event.preventDefault();
        });
        item.addEventListener('touchstart', function(event) {
            updateInputValue(event);
            event.preventDefault();
        });
    });

    // Ajoute un événement 'click' au document pour masquer les menus déroulants lorsque l'utilisateur clique en dehors
    document.addEventListener('click', function(event) {
        const dropdowns = document.querySelectorAll('.dropdown-menu');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(event.target)) {
                dropdown.style.display = 'none';
            }
        });
    });

    // Sélectionne le menu déroulant de la région
    const dropdownRegion = document.getElementById("dropdownMenu_region_id");
    dropdownRegion.addEventListener("click", function(event) {
        event.preventDefault(); 
        const selectedRegion = event.target.getAttribute("data-value");
        document.getElementById("region_id").value = selectedRegion; 
        document.getElementById("liste_prof_id").submit(); 
    });

    // Sélectionne toutes les cases à cocher avec la classe 'form-check-input'
    const checkboxes = document.querySelectorAll('.form-check-input');
    checkboxes.forEach(checkbox => {
        // Fonction pour gérer le changement de case à cocher
        function handleCheckboxChange(event) {
            checkboxes.forEach(input => {
                if (input !== checkbox) {
                    input.checked = false;
                }
            });
        }

        // Ajoute un événement 'change' et 'touchstart' à chaque case à cocher
        checkbox.addEventListener('change', handleCheckboxChange);
        checkbox.addEventListener('touchstart', handleCheckboxChange);
    });
});
