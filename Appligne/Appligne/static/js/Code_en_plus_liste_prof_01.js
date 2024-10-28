document.addEventListener("DOMContentLoaded", function () {
    // Récupérer tous les inputs dont l'ID commence par 'temoignage_'
    const temoignageInputs = document.querySelectorAll("input[id^='temoignage_']");

    temoignageInputs.forEach(input => {
        const profId = input.id.split('_')[1];  // Extraire l'ID du professeur
        const ratingValue = parseInt(input.value);  // Valeur de l'input (1 à 5)

        // Mettre à jour les étoiles en fonction de la valeur de l'input
        for (let i = 1; i <= 5; i++) {
            const starElement = document.getElementById(`temoignage_${profId}_t${i}`);
            if (i <= ratingValue) {
                starElement.classList.add("text-primary");  // Ajoute la classe bleue
                starElement.classList.remove("text-secondary");  // Retire la classe grise
            } else {
                starElement.classList.add("text-secondary");  // Ajoute la classe grise
                starElement.classList.remove("text-primary");  // Retire la classe bleue
            }
        }
    });
});

// Fonction pour modifier le texte en fonction de la réduction d'impôts
function toggleText() {
    const priceText = document.getElementById("priceText");
    const prixParHeureElements = document.querySelectorAll(".prix_par_heure");

    for (let i = 0; i < prixParHeureElements.length; i++) {
        const prixActuel = prixParHeureElements[i].innerHTML.trim(); // Supprimer les espaces vides
        const prixActuelFloat = parseFloat(prixActuel);

        // Vérifier si prixActuelFloat est un nombre valide
        if (isNaN(prixActuelFloat) || prixActuel === "Le prix de l'heure n'est pas défini") {
            // Si ce n'est pas un nombre ou si le prix n'est pas défini, ne rien changer
            prixParHeureElements[i].innerHTML = "Le prix de l'heure n'est pas défini";
            continue; // Passer à l'élément suivant
        }

        const nouveauPrix01 = prixActuelFloat * 0.5;
        const nouveauPrix02 = prixActuelFloat * 2;

        if (document.getElementById("flexSwitchCheckChecked").checked) {
            priceText.innerHTML = "Prix <b>après</b> réduction d'impôts";
            prixParHeureElements[i].innerHTML = nouveauPrix01.toFixed(2) + " €/h";
        } else {
            priceText.innerHTML = "Prix <b>avant</b> réduction d'impôts";
            prixParHeureElements[i].innerHTML = nouveauPrix02.toFixed(2) + " €/h";
        }
    }
}

