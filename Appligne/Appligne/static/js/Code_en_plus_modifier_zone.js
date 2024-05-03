
// ****************************  pour plusieur pages   debut  ***********************
    // fonction pour supprimer un champ div pour un diplome
    function supprimerDiv(divId) {
        var div = document.getElementById(divId);
        if (div) {
            div.parentNode.removeChild(div);
        }
    }
// ****************************  pour plusieur pages   fin  ***********************