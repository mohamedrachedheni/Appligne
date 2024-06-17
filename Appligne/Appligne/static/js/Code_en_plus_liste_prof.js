document.addEventListener('DOMContentLoaded', function () {
    // Fonction pour afficher ou masquer le menu déroulant
    function toggleDropdown(event) {
        const dropdown = event.currentTarget.parentElement.querySelector('.dropdown-menu');
        const isDropdownVisible = dropdown.style.display === 'block';
        
        // Masque tous les autres menus déroulants
        const dropdowns = document.querySelectorAll('.dropdown-menu');
        dropdowns.forEach(d => {
            d.style.display = 'none';
        });

        // Affiche ou masque le menu déroulant actuel en fonction de son état
        dropdown.style.display = isDropdownVisible ? 'none' : 'block';
        event.stopPropagation();
    }

    // Sélectionne tous les inputs de type "text"
    const inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => {
        // Ajoute un événement 'click' et 'touchstart' à chaque input
        input.addEventListener('click', toggleDropdown);
        input.addEventListener('touchstart', toggleDropdown);
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

    // Ajoute un événement 'touchstart' au document pour masquer les menus déroulants lorsque l'utilisateur touche en dehors
    document.addEventListener('touchstart', function(event) {
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

        // Ajoute un événement 'change', 'click', et 'touchstart' à chaque case à cocher
        checkbox.addEventListener('change', handleCheckboxChange);
        checkbox.addEventListener('click', handleCheckboxChange);
        checkbox.addEventListener('touchstart', handleCheckboxChange);
    });
});
