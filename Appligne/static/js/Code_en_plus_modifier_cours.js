/*********************** http://localhost:8000/liste_prof  début **************************** */

// Fonction pour modifier le texte en fonction de la réduction d'impôts
// Cette fonction bascule le texte affiché pour indiquer si les prix affichés sont avant ou après la réduction d'impôts
// et met à jour les prix par heure en conséquence.
// function toggleText() {
//     const priceText = document.getElementById("priceText");
//     const prixParHeureElements = document.querySelectorAll(".prix_par_heure");

//     for (let i = 0; i < prixParHeureElements.length; i++) {
//         const prixActuel = parseFloat(prixParHeureElements[i].innerHTML); // Récupère le prix actuel sous forme de nombre
//         const nouveauPrix01 = prixActuel * 0.5; // Calcule le nouveau prix après réduction
//         const nouveauPrix02 = prixActuel * 2;   // Calcule le prix avant réduction (doublement)

//         if (document.getElementById("flexSwitchCheckChecked").checked) {
//             // Si la case de réduction d'impôts est cochée, afficher les prix réduits
//             priceText.innerHTML = "Prix <b>après</b> réduction d'impôts";
//             prixParHeureElements[i].innerHTML = nouveauPrix01.toFixed(2);
//         } else {
//             // Sinon, afficher les prix avant réduction
//             priceText.innerHTML = "Prix <b>avant</b> réduction d'impôts";
//             prixParHeureElements[i].innerHTML = nouveauPrix02.toFixed(2);
//         }
//     }
// }

/*********************** http://localhost:8000/liste_prof  fin **************************** */

// Fonction pour mettre à jour la valeur de l'input lorsque l'utilisateur sélectionne un élément dans la liste déroulante
// Cette fonction prend la valeur sélectionnée dans la liste et l'insère dans l'input correspondant.
function updateInputValue(event) {
    const inputId = event.target.closest('.dropdown').querySelector('input[type="text"]').id;
    const selectedValue = event.target.getAttribute('data-value');
    document.getElementById(inputId).value = selectedValue;
    const dropdown = event.target.closest('.dropdown-menu');
    dropdown.style.display = 'none'; // Masque le menu déroulant après la sélection
}

// Gestion des événements

document.addEventListener('DOMContentLoaded', function () {
    // Afficher le menu déroulant lorsqu'un input est cliqué
    // Cette section ouvre le menu déroulant lorsque l'utilisateur clique sur un champ de texte associé.
    const inputs = document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => {
        input.addEventListener('click', function(event) {
            const dropdown = input.parentElement.querySelector('.dropdown-menu');
            dropdown.style.display = 'block'; // Affiche le menu déroulant
            event.stopPropagation(); // Empêche la propagation de l'événement pour éviter la fermeture instantanée du menu
        });
    });

    // Mettre à jour l'input lorsqu'un élément de la liste déroulante est cliqué
    // Cette section permet de sélectionner un élément de la liste et met à jour l'input correspondant.
    const dropdownItems = document.querySelectorAll('ul.dropdown-menu a.dropdown-item');
    dropdownItems.forEach(item => {
        item.addEventListener('click', function(event) {
            updateInputValue(event); // Met à jour la valeur de l'input avec l'élément sélectionné
            event.preventDefault(); // Empêche l'action par défaut du lien
        });
    });

    // Masquer le menu déroulant lorsqu'on clique en dehors
    // Si l'utilisateur clique en dehors du menu déroulant, celui-ci est masqué.
    document.addEventListener('click', function(event) {
        const dropdowns = document.querySelectorAll('.dropdown-menu');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(event.target)) {
                dropdown.style.display = 'none'; // Masque le menu déroulant
            }
        });
    });

    // Soumettre le formulaire lorsqu'un élément de la liste déroulante est cliqué
    // Lorsqu'une région est sélectionnée dans la liste déroulante, cette fonction met à jour le champ caché et soumet le formulaire.
    const dropdownRegion = document.getElementById("dropdownMenu_region_id");
    dropdownRegion.addEventListener("click", function(event) {
        event.preventDefault(); 
        const selectedRegion = event.target.getAttribute("data-value");
        document.getElementById("region_id").value = selectedRegion; // Met à jour l'ID de la région sélectionnée
        document.getElementById("liste_prof_id").submit(); // Soumet le formulaire
    });

    // Actualiser le formulaire lorsqu'une case est cochée
    // Cette section assure qu'une seule case à cocher est activée à la fois. Si l'utilisateur coche une autre case, toutes les autres se décochent.
    // const checkboxes = document.querySelectorAll('.form-check-input');
    // checkboxes.forEach(checkbox => {
    //     checkbox.addEventListener('change', function(event) {
    //         checkboxes.forEach(input => {
    //             if (input !== checkbox) {
    //                 input.checked = false; // Décoche les autres cases
    //             }
    //         });
    //     });
    // });
});

// Configuration de l'inputmask pour les champs de prix par heure
// Cette section ajoute un masque de saisie sur les champs de prix pour qu'ils respectent un format numérique avec deux décimales, et ajoute le suffixe '€/h'.
$(document).ready(function(){
    $('.prix-heure').inputmask({
        alias: 'numeric',
        groupSeparator: '',
        digits: 2,
        digitsOptional: false,
        placeholder: '0',
        rightAlign: false,
        autoUnmask: true,
        integerDigits: 3, // Permet jusqu'à 3 chiffres avant la virgule
        max: 999.99,
        allowMinus: false,
        suffix: ' €/h' // Ajoute l'unité euro par heure
    });
});
