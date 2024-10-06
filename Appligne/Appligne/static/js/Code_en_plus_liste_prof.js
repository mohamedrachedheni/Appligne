/*********************** http://localhost:8000/liste_prof  début **************************** */



/*********************** http://localhost:8000/liste_prof  fin **************************** */

// Fonction pour mettre à jour la valeur de l'input lorsque l'utilisateur sélectionne un élément dans la liste déroulante
function updateInputValue(event) {
    const inputId = event.target.closest('.dropdown').querySelector('input[type="text"]').id;
    const selectedValue = event.target.getAttribute('data-value');
    document.getElementById(inputId).value = selectedValue;
    const dropdown = event.target.closest('.dropdown-menu');
    dropdown.style.display = 'none';
}

// Gestion des événements

document.addEventListener('DOMContentLoaded', function () {
    // Afficher le menu déroulant lorsqu'un input est cliqué
    const inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => {
        input.addEventListener('click', function(event) {
            const dropdown = input.parentElement.querySelector('.dropdown-menu');
            dropdown.style.display = 'block';
            event.stopPropagation();
        });
    });

    // Mettre à jour l'input lorsqu'un élément de la liste déroulante est cliqué
    const dropdownItems = document.querySelectorAll('ul.dropdown-menu a.dropdown-item');
    dropdownItems.forEach(item => {
        item.addEventListener('click', function(event) {
            updateInputValue(event);
            event.preventDefault();
        });
    });

    // Masquer le menu déroulant lorsqu'on clique en dehors
    document.addEventListener('click', function(event) {
        const dropdowns = document.querySelectorAll('.dropdown-menu');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(event.target)) {
                dropdown.style.display = 'none';
            }
        });
    });

    // Soumettre le formulaire lorsqu'un élément de la liste déroulante est cliqué
    const dropdownRegion = document.getElementById("dropdownMenu_region_id");
    dropdownRegion.addEventListener("click", function(event) {
        event.preventDefault(); 
        const selectedRegion = event.target.getAttribute("data-value");
        document.getElementById("region_id").value = selectedRegion; 
        document.getElementById("liste_prof_id").submit(); 
    });

    // Actualiser le formulaire lorsqu'une case est cochée
    const checkboxes = document.querySelectorAll('.form-check-input');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function(event) {
            checkboxes.forEach(input => {
                if (input !== checkbox) {
                    input.checked = false;
                }
            });
        });
    });
});


