/*********************** http://localhost:8000/liste_prof  dédut **************************** */
// Prix de heure avant ou apres reduction
function toggleText() {
    var priceText = document.getElementById("priceText");
    // Récupérer l'élément avec la classe "prix_par_heure"
    var prixParHeureElements = document.getElementsByClassName("prix_par_heure");

    // Parcourir la liste d'éléments avec la classe "prix_par_heure"
    for (var i = 0; i < prixParHeureElements.length; i++) {
        // Récupérer la valeur actuelle, la convertir en nombre
        var prixActuel = parseFloat(prixParHeureElements[i].innerHTML);
        var nouveauPrix01 = prixActuel * 0.5;
        var nouveauPrix02 = prixActuel * 2;

        if (document.getElementById("flexSwitchCheckChecked").checked) {
            priceText.innerHTML = "Prix <b>après</b> réduction d'impôts";
            prixParHeureElements[i].innerHTML = nouveauPrix01.toFixed(2); // Pour afficher deux décimales
        } else {
            priceText.innerHTML = "Prix <b>avant</b> réduction d'impôts";
            prixParHeureElements[i].innerHTML = nouveauPrix02.toFixed(2); // Pour afficher deux décimales
        }
    }
}
/*********************** http://localhost:8000/liste_prof  fin  **************************** */