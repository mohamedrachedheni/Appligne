// Récupérer le token CSRF à partir du meta-tag
const csrftoken = document.querySelector('[name=csrf-token]').content;

// Fonction pour mettre à jour l'input de dropdown
function updateDropdownInput(dropdownId, inputId) {
    const dropdown = document.getElementById(dropdownId);
    dropdown.addEventListener("click", function(event) {
        event.preventDefault();
        const selectedValue = event.target.getAttribute("data-value");
        if (selectedValue) {
            document.getElementById(inputId).value = selectedValue;
        }
    });
}

// Fonction pour obtenir les départements de la région sélectionnée
function fetchDepartements(regionId) {
    fetch('/accounts/obtenir_liste_department', {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ region: regionId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.para_departement) {
            const departements = data.para_departement.departement;
            const departementDefaut = data.para_departement.departement_defaut;
            const departementInput = document.getElementById("departement_id");
            const departementDropdown = document.getElementById("dropdownMenu_departement_id");

            // Mettre à jour l'input du département par défaut
            departementInput.value = departementDefaut ? departementDefaut.departement : '';

            // Vider la liste des départements
            departementDropdown.innerHTML = '';

            // Ajouter les nouveaux départements dans le menu déroulant
            departements.forEach(dep => {
                const li = document.createElement("li");
                const a = document.createElement("a");
                a.classList.add("dropdown-item", "dropdown-item-demande");
                a.href = "#";
                a.setAttribute("data-value", dep.departement);
                a.textContent = dep.departement;
                li.appendChild(a);
                departementDropdown.appendChild(li);
            });
        } else {
            console.error("Erreur: ", data.error);
        }
    })
    .catch(error => console.error("Erreur lors de la récupération des départements:", error));
}

// Ajouter les événements pour chaque dropdown
document.addEventListener('DOMContentLoaded', function () {
    // Région
    updateDropdownInput("dropdownMenu_region_id", "region_id");
    document.getElementById("dropdownMenu_region_id").addEventListener("click", function(event) {
        const selectedRegion = event.target.getAttribute("data-value");
        if (selectedRegion) {
            fetchDepartements(selectedRegion);
        }
    });

    // Département
    updateDropdownInput("dropdownMenu_departement_id", "departement_id");

    // Matière
    updateDropdownInput("dropdownMenu_matiere_id", "matiere_id");

    // Niveau
    updateDropdownInput("dropdownMenu_niveau_id", "niveau_id");

    // Ajout d'un gestionnaire d'événements pour chaque bouton radio
    const radioButtons = document.querySelectorAll('input[type="radio"]');
    
    radioButtons.forEach(radio => {
        radio.addEventListener('change', function() {
            // Lorsqu'un radio est sélectionné, désélectionner les autres
            radioButtons.forEach(otherRadio => {
                if (otherRadio !== radio) {
                    otherRadio.checked = false;
                }
            });
        });
    });
});
