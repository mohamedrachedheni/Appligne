// Code_en_plus.js

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






// Lien vers Font Awesome
document.write('<script src="https://kit.fontawesome.com/1d95b4176e.js" crossorigin="anonymous"></script>');


//<!-- Appliquer le masque de saisie -->
document.write('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"'
 + 'integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL"' +
'crossorigin="anonymous" ></script>');

$(document).ready(function(){
    $('#phoneInput').inputmask('99 99 99 99 99');
});


// Lien vers Pikaday
document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/pikaday/1.8.0/pikaday.min.js"></script>');

// Pikaday avec date par défaut 01/01/1985 et en Françai
document.addEventListener('DOMContentLoaded', function () {
    // Date par défaut
    var defaultDate = new Date(1985, 0, 1);

    // Utilisation de la bibliothèque Pikaday pour faciliter la sélection de la date
    var picker = new Pikaday({
        field: document.getElementById('dateInput'),
        format: 'DD/MM/YYYY', // Format de la date en français
        i18n: {
            previousMonth: 'Mois précédent',
            nextMonth: 'Mois suivant',
            months: [
                'Janvier',
                'Février',
                'Mars',
                'Avril',
                'Mai',
                'Juin',
                'Juillet',
                'Août',
                'Septembre',
                'Octobre',
                'Novembre',
                'Décembre'
            ],
            weekdays: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
            weekdaysShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
        },
        defaultDate: defaultDate, // Définir la date par défaut
        onSelect: function(date) {
            var formattedDate = ("0" + date.getDate()).slice(-2) + "/" + ("0" + (date.getMonth() + 1)).slice(-2) + "/" + date.getFullYear();
            document.getElementById('dateInput').value = formattedDate;
        }
    });
});
// Pikaday avec date par défaut 01/01/1985 et en Françai
document.addEventListener('DOMContentLoaded', function () {
    // Date par défaut
    var defaultDate = new Date(1985, 0, 1);

    // Utilisation de la bibliothèque Pikaday pour faciliter la sélection de la date
    var picker = new Pikaday({
        field: document.getElementById('dateInput2'),
        format: 'DD/MM/YYYY', // Format de la date en français
        i18n: {
            previousMonth: 'Mois précédent',
            nextMonth: 'Mois suivant',
            months: [
                'Janvier',
                'Février',
                'Mars',
                'Avril',
                'Mai',
                'Juin',
                'Juillet',
                'Août',
                'Septembre',
                'Octobre',
                'Novembre',
                'Décembre'
            ],
            weekdays: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
            weekdaysShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
        },
        defaultDate: defaultDate, // Définir la date par défaut
        onSelect: function(date) {
            var formattedDate = ("0" + date.getDate()).slice(-2) + "/" + ("0" + (date.getMonth() + 1)).slice(-2) + "/" + date.getFullYear();
            document.getElementById('dateInput2').value = formattedDate;
        }
    });
});


// Fonction pour réordonner les ID et les paramètres des div des diplomes
function ReOrderId(){

    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-dipl");

    for (var i = 0; i < listDiv.length; i++) {
        var newId = "supprimerDivDiplome-" + (i + 1);
        listDiv[i].id = newId;

        var button = listDiv[i].querySelector("button");
        button.setAttribute("onclick", "supprimerDiv('" + newId + "')");

        // Mettez à jour le texte du bouton avec la valeur de newId
        //button.innerText = "Sup-" + (i + 1);
    }
}

// fonction pour supprimer un champ div pour un diplome
function supprimerDiv(divId) {
    var div = document.getElementById(divId);
    if (div) {
        div.parentNode.removeChild(div);
    }

}

// Fonction pour ajouter un diplôme
function ajouterDiplome() {
            
    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-dipl");
    // le compte de la liste des class des div des diplomes
    var indice = listDiv.length;

    // Code HTML du nouveau diplôme
    var nouveauDiplomeHTML = `
    <div class="row g-2 ajout-dipl" id="supprimerDivDiplome-${indice+1}" >
        <div class="col-md-1 col-sm-3 position-relative">
        
            <label class="form-label" for="invalidCheckDipl${indice+1}">Principal</label>
            <input class="form-check-input" type="checkbox" value="" id="invalidCheckDipl${indice+1}" >
        </div>   
        <div class="col-lg-3 col-md-4 col-sm-4 position-relative">
            <label for="validationTooltipDipl${indice+1}" class="form-label">Diplôme</label>
            <select class="form-select" id="validationTooltipDipl${indice+1}" required>
                <option >AgroParsTech</option>
                <option   >Polytechnique</option>
                <option  >MathSup</option>
                
            </select>
            <div class="invalid-tooltip">
                Please select a valid state.
            </div>
        </div>
        <div class="col-lg-2 col-md-3 col-sm-2 position-relative">
            <label for="validationTooltipAnnee${indice+1}" class="form-label">Optenu</label>
            <input type="text" class="form-control" id="validationTooltipAnnee${indice+1}" value="" required>
            <div class="valid-tooltip">
                Looks good!
            </div>
        </div>
        <div class="col-lg-6 col-md-2 col-sm-3 position-relative">
            <label for="validationTooltipIntitule${indice+1}" class="form-label">Intitulé</label>
            <div class="row">
                <div class="col-lg-10 col-md-6 col-sm-6 position-relative">
                    <input type="text" class="form-control" id="validationTooltipIntitule${indice+1}" value="" required>
                    <div class="valid-tooltip">
                        Looks good!
                    </div>
                </div>
                <div class="col-lg-2 col-md-6 col-sm-6 position-relative">
                    <button class="btn  btn-sup " onclick="supprimerDiv('supprimerDivDiplome-${indice+1}')">
                    <svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="100" height="100" viewBox="0 0 26 26">
                    <path d="M 11.5 -0.03125 C 9.542969 -0.03125 7.96875 1.59375 7.96875 3.5625 L 7.96875 4 L 4 4 C 3.449219 4 3 4.449219 3 5 L 3 6 L 2 6 L 2 8 L 4 8 L 4 23 C 4 24.644531 5.355469 26 7 26 L 19 26 C 20.644531 26 22 24.644531 22 23 L 22 8 L 24 8 L 24 6 L 23 6 L 23 5 C 23 4.449219 22.550781 4 22 4 L 18.03125 4 L 18.03125 3.5625 C 18.03125 1.59375 16.457031 -0.03125 14.5 -0.03125 Z M 11.5 2.03125 L 14.5 2.03125 C 15.304688 2.03125 15.96875 2.6875 15.96875 3.5625 L 15.96875 4 L 10.03125 4 L 10.03125 3.5625 C 10.03125 2.6875 10.695313 2.03125 11.5 2.03125 Z M 6 8 L 11.125 8 C 11.25 8.011719 11.371094 8.03125 11.5 8.03125 L 14.5 8.03125 C 14.628906 8.03125 14.75 8.011719 14.875 8 L 20 8 L 20 23 C 20 23.5625 19.5625 24 19 24 L 7 24 C 6.4375 24 6 23.5625 6 23 Z M 8 10 L 8 22 L 10 22 L 10 10 Z M 12 10 L 12 22 L 14 22 L 14 10 Z M 16 10 L 16 22 L 18 22 L 18 10 Z"></path>
                    </svg>
                    </button>
                </div>
            </div>
        </div>
        
    </div>
    `;

    // Créer un élément div temporaire
    var tempDiv = document.createElement('div');
    tempDiv.innerHTML = nouveauDiplomeHTML;

    // Insérer le nouveau diplôme juste avant le bouton "Ajouter un diplôme"
    var boutonAjouterDiplomeDiv = document.getElementById('boutonAjouterDiplome');
    boutonAjouterDiplomeDiv.insertAdjacentHTML('afterend', nouveauDiplomeHTML);

    // re-ordonner les ID et les Paramètre des fonctions
    ReOrderId();
}

// Fonction pour ajouter une éxpérience
function ajouterExperience() {
            
    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-exper");
    // le compte de la liste des class des div des diplomes
    var indice = listDiv.length;

    // Code HTML du nouveau diplôme
    var nouveauDiplomeHTML = `
    <div class="row g-2 ajout-exper" id="supprimerDivExperience-${indice+1}" >
                    <div class="col-lg-1 col-md-2 col-sm-2 position-relative">
                    
                        <label class="form-label" for="invalidCheckExp${indice+1}">Principal</label>
                        <input class="form-check-input" type="checkbox" value="" id="invalidCheckExp${indice+1}" >
                    </div>   
                    <div class="col-lg-2 col-md-10 col-sm-10 position-relative">
                        <label for="validationTooltipExpTyp${indice+1}" class="form-label">Type</label>
                        <select class="form-select" id="validationTooltipExpTyp${indice+1}" required>
                            <option >Professeur(e) en sciences</option>
                            <option   >Professeur(e) en chimie</option>
                            <option  >Professeur(e) en physique</option>
                            
                        </select>
                        <div class="invalid-tooltip">
                            Please select a valid state.
                        </div>
                    </div>
                    <div class="col-lg-1 col-md-6 col-sm-6 position-relative">
                        <label for="validationTooltipDebut${indice+1}" class="form-label">Début</label>
                        <input type="text" class="form-control" id="validationTooltipFin${indice+1}" value="" required>
                        <div class="valid-tooltip">
                            Looks good!
                        </div>
                    </div>
                    <div class="col-lg-1 col-md-6 col-sm-6 position-relative">
                        <label for="validationTooltipFin${indice+1}" class="form-label">Fin</label>
                        <input type="text" class="form-control" id="validationTooltipFin${indice+1}" value="" required>
                        <div class="valid-tooltip">
                            Looks good!
                        </div>
                    </div>
                    <div class="col-lg-2 col-md-4 col-sm-6 g-3 ">
                        <div class="row " >
                            <div class="col-12"  style="padding: -25px; margin-top: -8px;">
                                <label class="form-check-label" for="flexSwitchCheckChecked" >Actuellement</label>

                            </div>
                            <div class="col-12" style="padding: 15px; padding-left: 45px;">
                                <div class="form-check form-switch switch-column">
                                    <input class="form-check-input mg-checkbox" type="checkbox" role="switch" id="flexSwitchCheckChecked" checked onchange="toggleText()" style="padding-right: -5px;" >
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-5 col-md-8 col-sm-6 position-relative" style="margin-left: -40px; ">
                        <label for="validationTooltipExpComm${indice+1}" class="form-label">Commentaires</label>
                        <div class="row" style="margin-right:-100px" >
                            <div class="col-lg-10 col-md-6 col-sm-6 position-relative">
                                <input type="text" class="form-control" id="validationTooltipExpComm${indice+1}" value="" required>
                                <div class="valid-tooltip">
                                    Looks good!
                                </div>
                            </div>
                            <div class="col-lg-2 col-md-6 col-sm-6 position-relative">
                                <button class="btn  btn-sup " onclick="supprimerDiv('supprimerDivExperience-${indice+1}')">
                                    <svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="100" height="100" viewBox="0 0 26 26">
                                    <path d="M 11.5 -0.03125 C 9.542969 -0.03125 7.96875 1.59375 7.96875 3.5625 L 7.96875 4 L 4 4 C 3.449219 4 3 4.449219 3 5 L 3 6 L 2 6 L 2 8 L 4 8 L 4 23 C 4 24.644531 5.355469 26 7 26 L 19 26 C 20.644531 26 22 24.644531 22 23 L 22 8 L 24 8 L 24 6 L 23 6 L 23 5 C 23 4.449219 22.550781 4 22 4 L 18.03125 4 L 18.03125 3.5625 C 18.03125 1.59375 16.457031 -0.03125 14.5 -0.03125 Z M 11.5 2.03125 L 14.5 2.03125 C 15.304688 2.03125 15.96875 2.6875 15.96875 3.5625 L 15.96875 4 L 10.03125 4 L 10.03125 3.5625 C 10.03125 2.6875 10.695313 2.03125 11.5 2.03125 Z M 6 8 L 11.125 8 C 11.25 8.011719 11.371094 8.03125 11.5 8.03125 L 14.5 8.03125 C 14.628906 8.03125 14.75 8.011719 14.875 8 L 20 8 L 20 23 C 20 23.5625 19.5625 24 19 24 L 7 24 C 6.4375 24 6 23.5625 6 23 Z M 8 10 L 8 22 L 10 22 L 10 10 Z M 12 10 L 12 22 L 14 22 L 14 10 Z M 16 10 L 16 22 L 18 22 L 18 10 Z"></path>
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                    
                </div>
    `;

    // Créer un élément div temporaire
    var tempDiv = document.createElement('div');
    tempDiv.innerHTML = nouveauDiplomeHTML;

    // Insérer le nouveau diplôme juste avant le bouton "Ajouter un diplôme"
    var boutonAjouterDiplomeDiv = document.getElementById('boutonAjouterExperience');
    boutonAjouterDiplomeDiv.insertAdjacentHTML('afterend', nouveauDiplomeHTML);

    // re-ordonner les ID et les Paramètre des fonctions
    ReOrderIdExper();
}

// Fonction pour réordonner les ID et les paramètres des div des éxpériences
function ReOrderIdExper(){

    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-exper");

    for (var i = 0; i < listDiv.length; i++) {
        var newId = "supprimerDivExperience-" + (i + 1);
        listDiv[i].id = newId;

        var button = listDiv[i].querySelector("button");
        button.setAttribute("onclick", "supprimerDiv('" + newId + "')");

        // Mettez à jour le texte du bouton avec la valeur de newId
        //button.innerText = "Sup-" + (i + 1);
    }
}

// Fonction pour ajouter une matière à enseigner
function ajouterMatiere() {
            
    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-matiere");
    // le compte de la liste des class des div des diplomes
    var indice = listDiv.length;

    // Code HTML du nouveau diplôme
    var nouveauDiplomeHTML = `
    <div class="row g-2 ajout-matiere" id="supprimerDivMatiere-1" >
                    <div class="col-md-1  position-relative">
                    
                        <label class="form-label" for="invalidCheckMat${indice+1}">Principal</label>
                        <input class="form-check-input" type="checkbox" value="" id="invalidCheckMat${indice+1}" >
                    </div>   
                    <div class=" col-md-5  position-relative">
                        <label for="validationTooltipMat${indice+1}" class="form-label">Matières</label>
                        <select class="form-select" id="validationTooltipMat${indice+1}" required>
                            
                            <optgroup label="Enseignements scientifiques"></option>
                                <option>Chimie</option>
                                <option>Dessin industriel</option>
                                <option>Electronique</option>
                                <option>Informatique</option>
                                <option>Logique maths</option>
                                <option>Maths</option>
                                <option>NSI</option>
                                <option>Physique</option>
                                <option>Physique-chimie</option>
                                <option>Sciences de l'ingénieurs</option>
                                <option>Statistique</option>
                            </optgroup>
                        
                            <optgroup label="Lettres"></option>
                                <option>Français</option>
                                <option>Grec</option>
                                <option>Latin</option>
                                <option>Orthographe</option>
                                <option>Synthèse de document</option>
                            </optgroup>
                        
                            <optgroup label="Langues vivantes"></option>
                                <option>Allemand</option>
                                <option>Anglais</option>
                                <option>Arabe</option>
                                <option>Chinois</option>
                                <option>Coréen</option>
                                <option>Espagnol</option>
                                <option>FLE</option>
                                <option>Italien</option>
                                <option>Japonais</option>
                                <option>Portugais</option>
                                <option>Russe</option>
                            </optgroup>
                            <optgroup label="Sciences humaines"></option>
                                <option>Culture générale</option>
                                <option>Education civique</option>
                                <option>ESH</option>
                                <option>Géopolitique</option>
                                <option>Histoire - Géographie</option>
                                <option>Humanites litérature philosophie</option>
                                <option>Management</option>
                                <option>Philosophie</option>
                                <option>Sciences politiques</option>
                            </optgroup>
                            <optgroup label="Economie"></option>
                                <option>Comptabilité</option>
                                <option>Control de gestion</option>
                                <option>Droit</option>
                                <option>Economie</option>
                                <option>Fiscalité</option>
                                <option>Gestion financière</option>
                                <option>Macroéconomie</option>
                                <option>Marketing</option>
                                <option>Microéconomie</option>
                                <option>SES</option>
                            </optgroup>
                            <optgroup label="Sciences naturelles"></option>
                                <option>Anatomie</option>
                                <option>Biologie</option>
                                <option>Biologie - Ecologie</option>
                                <option>Biochimie</option>
                                <option>Biophysique</option>
                                <option>Biostatique</option>
                                <option>SVT</option>
                            </optgroup>
                            <optgroup label="Préparation orale"></option>
                                <option>Coaching scolaire</option>
                                <option>Entretien de motivation</option>
                                <option>Grand oral du bac</option>
                                <option>Orientation scolaire</option>
                                <option>TIPE</option>
                                <option>TPE</option>
                            </optgroup>
                            <optgroup label="Enseignements artistiques"></option>
                                <option>Art du cirque</option>
                                <option>Arts plastiques</option>
                                <option>Cinéma audiovisuel</option>
                                <option>Danse</option>
                                <option>Histoire des arts</option>
                                <option>Musique</option>
                                <option>Théatre</option>
                            </optgroup>
                        </select>
                        <div class="invalid-tooltip">
                            Please select a valid state.
                        </div>
                    </div>
                    <div class=" col-md-5  position-relative">
                        <label for="validationTooltipNiv${indice+1}" class="form-label">Niveaux (Sélectionnez un ou plusieurs niveaux)</label>
                        <select class="form-select" id="validationTooltipNiv${indice+1}" required multiple placeholder="Sélectionnez un ou plusieurs niveaux" >
                            <option>Tou les niveaux</option>
                            <optgroup label="Collège" id="college">
                                <option>Tou les niveaux du collège</option>
                                <option>6ème</option>
                                <option>5ème</option>
                                <option>4ème</option>
                                <option>3ème</option>
                            </optgroup>
                            <optgroup label="Lycée">
                                <option>Tou les niveaux du lycée</option>
                                <option>Seconde</option>
                                <option>Première STMGL</option>
                                <option>Première STL</option>
                                <option>Première Générale</option>
                                <option>Première STI2D</option>
                                <option>Terminale STMG</option>
                                <option>Terminale STI2D</option>
                                <option>Terminale Générale</option>
                                <option>Terminale STL</option>
                            </optgroup>
                            <optgroup label="Concours et prépa">
                                <option>Prépa Concours Geipi Polytech</option>
                                <option>Avenir-Puissance Alpha-Advance-Geipi</option>
                                <option>Acces-Sésame</option>
                                <option>Prépa Concours Avenir</option>
                                <option>Prépa Sciences Po</option>
                                <option>Prépa Concours ESA</option>
                                <option>Prépa Concours Advance</option>
                                <option>Prépa Concours Acces</option>
                                <option>Prépa Concours CRPE</option>
                                <option>Pass BBA</option>
                                <option>Prépa Concours Puissance Alpha</option>
                                <option>Prépa Concours Sésame</option>
                                <option>Prépa intégrée 1ère année</option>
                            </optgroup>
                            <optgroup label="Autres">
                                <option>MP2I</option>
                                <option>MPSI</option>
                                <option>TSI</option>
                                <option>TB</option>
                                <option>TBC</option>
                                <option>ATS</option>
                                <option>PTSI</option>
                                <option>BBPST 1</option>
                                <option>PCSI</option>
                                <option>Math Sup</option>
                                <option>MP</option>
                                <option>PSI</option>
                                <option>PC</option>
                                <option>Prépa intégré 2ème année</option>
                                <option>TSI 2</option>
                                <option>MPI</option>
                                <option>PT</option>
                                <option>BCPST 2</option>
                                <option>Maths Spé</option>
                                <option>ECG 1</option>
                                <option>D1 ENS Cachan</option>
                                <option>Hypokhâgne ALL</option>
                                <option>Khâgne AL</option>
                                <option>Khâgne BL</option>
                                <option>Gei Univ</option>
                                <option>CAST Ing</option>
                                <option>TOEIC</option>
                                <option>Tage Mage</option>
                                <option>GMAT</option>
                                <option>Score IAE Message</option>
                                <option>TOEFL</option>
                                <option>Architechture</option>
                                <option>Infirmier</option>
                                <option>Capes</option>
                                <option>Tage 2</option>
                                <option>IELTS</option>
                                <option>DCG</option>
                                <option>DSCG</option>
                                <option>Agrégation</option>
                                <option>BUT</option>
                                <option>BTS</option>
                                <option>Licence 1</option>
                                <option>Licence 2</option>
                                <option>Licence 3</option>
                                <option>Master 1</option>
                                <option>Master 2</option>
                                <option>Adultes</option>
                            </optgroup>
                        </select>
                        <div class="invalid-tooltip">
                            Please select a valid state.
                        </div>
                    </div>
                    <div class="col-lg-1 col-md-6 col-sm-6 position-relative p-2 g-4">
                        <button class="btn  btn-sup " onclick="supprimerDiv('supprimerDivMatiere-1')">
                            <svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="100" height="100" viewBox="0 0 26 26">
                            <path d="M 11.5 -0.03125 C 9.542969 -0.03125 7.96875 1.59375 7.96875 3.5625 L 7.96875 4 L 4 4 C 3.449219 4 3 4.449219 3 5 L 3 6 L 2 6 L 2 8 L 4 8 L 4 23 C 4 24.644531 5.355469 26 7 26 L 19 26 C 20.644531 26 22 24.644531 22 23 L 22 8 L 24 8 L 24 6 L 23 6 L 23 5 C 23 4.449219 22.550781 4 22 4 L 18.03125 4 L 18.03125 3.5625 C 18.03125 1.59375 16.457031 -0.03125 14.5 -0.03125 Z M 11.5 2.03125 L 14.5 2.03125 C 15.304688 2.03125 15.96875 2.6875 15.96875 3.5625 L 15.96875 4 L 10.03125 4 L 10.03125 3.5625 C 10.03125 2.6875 10.695313 2.03125 11.5 2.03125 Z M 6 8 L 11.125 8 C 11.25 8.011719 11.371094 8.03125 11.5 8.03125 L 14.5 8.03125 C 14.628906 8.03125 14.75 8.011719 14.875 8 L 20 8 L 20 23 C 20 23.5625 19.5625 24 19 24 L 7 24 C 6.4375 24 6 23.5625 6 23 Z M 8 10 L 8 22 L 10 22 L 10 10 Z M 12 10 L 12 22 L 14 22 L 14 10 Z M 16 10 L 16 22 L 18 22 L 18 10 Z"></path>
                            </svg>
                        </button>
                    </div>
                </div>
    `;

    // Créer un élément div temporaire
    var tempDiv = document.createElement('div');
    tempDiv.innerHTML = nouveauDiplomeHTML;

    // Insérer le nouveau diplôme juste avant le bouton "Ajouter un diplôme"
    var boutonAjouterDiplomeDiv = document.getElementById('boutonAjouterMatiere');
    boutonAjouterDiplomeDiv.insertAdjacentHTML('afterend', nouveauDiplomeHTML);

    // re-ordonner les ID et les Paramètre des fonctions
    ReOrderIdMatieres();
}

// Fonction pour réordonner les ID et les paramètres des div des matières à enseigner
function ReOrderIdMatieres(){

    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-matiere");

    for (var i = 0; i < listDiv.length; i++) {
        var newId = "supprimerDivMatiere-" + (i + 1);
        listDiv[i].id = newId;

        var button = listDiv[i].querySelector("button");
        button.setAttribute("onclick", "supprimerDiv('" + newId + "')");

        // Mettez à jour le texte du bouton avec la valeur de newId
        //button.innerText = "Sup-" + (i + 1);
    }
}

// Fonction pour ajouter une matière à enseigner
function ajouterZone() {
            
    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-zone");
    // le compte de la liste des class des div des diplomes
    var indice = listDiv.length;

    // Code HTML du nouveau diplôme
    var nouveauDiplomeHTML = `
    <div class="row g-2 ajout-matiere" id="supprimerDivZone-${indice+1}" >
                    <div class=" col-md-3  position-relative">
                        <label for="validationTooltipReg${indice+1}" class="form-label">Régions</label>
                        <select class="form-select" id="validationTooltipReg${indice+1}" required>
                                <option>ALSACE</option>
                                <option>AQUITAINE</option>
                                <option>AUVERGNE</option>
                                <option>BASSE-NORMANDIE</option>
                                <option>BOURGOGNE</option>
                                <option>BRETAGNE</option>
                                <option>CENTRE</option>
                                <option>CHAMPAGNE-ARDENNE</option>
                                <option>CORSE</option>
                                <option>FRANCHE-COMTE</option>
                                <option>GUADELOUPE</option>
                                <option>GUYANE</option>
                                <option>HAUTE-NORMANDIE</option>
                                <option>ILE-DE-FRANCE</option>
                                <option>LANGUEDOC-ROUSSILLON</option>
                                <option>LIMOUSIN</option>
                                <option>LORRAINE</option>
                                <option>MARTINIQUE</option>
                                <option>MAYOTTE</option>
                                <option>MIDI-PYRENEES</option>
                                <option>NORD-PAS-DE-CALAIS</option>
                                <option>PAYS DE LA LOIRE</option>
                                <option>PICARDIE</option>
                                <option>POITOU-CHARENTES</option>
                                <option>PROVENCE-ALPES-COTE D'AZUR</option>
                                <option>REUNION</option>
                                <option>RHONE-ALPES</option>
                        </select>
                        <div class="invalid-tooltip">
                            Please select a valid state.
                        </div>
                    </div>
                    <div class=" col-md-3  position-relative">
                        <label for="validationTooltipDep${indice+1}" class="form-label">Département</label>
                        <select class="form-select" id="validationTooltipDep${indice+1}" required>
                            <option>ESSONNE</option>
                            <option>HAUTS-DE-SEINE</option>
                            <option>PARIS</option>
                            <option>SEINE-ET-MARNE</option>
                            <option>SEINE-SAINT-DENIS</option>
                            <option>VAL-DE-MARNE</option>
                            <option>VAL-D'OISE</option>
                            <option>YVELINES</option>
                        </select>
                        <div class="invalid-tooltip">
                            Please select a valid state.
                        </div>
                    </div>
                    <div class=" col-md-5  position-relative">
                        <label for="validationTooltipCom${indice+1}" class="form-label">Communes (Sélectionnez une ou plusieurs Communes)</label>
                        <select class="form-select" id="validationTooltipCom${indice+1}" required multiple placeholder="Sélectionnez un ou plusieurs niveaux" >
                            <option>Tous les communes</option>
                            <option>PARIS-1ER-ARRONDISSEMENT   (75001)</option>
                            <option>PARIS-2E-ARRONDISSEMENT   (75002)</option>
                            <option>PARIS-3E-ARRONDISSEMENT   (75003)</option>
                            <option>PARIS-4E-ARRONDISSEMENT   (75004)</option>
                            <option>PARIS-5E-ARRONDISSEMENT   (75005)</option>
                            <option>PARIS-6E-ARRONDISSEMENT   (75006)</option>
                            <option>PARIS-7E-ARRONDISSEMENT   (75007)</option>
                            <option>PARIS-8E-ARRONDISSEMENT   (75008)</option>
                            <option>PARIS-9E-ARRONDISSEMENT   (75009)</option>
                            <option>PARIS-10E-ARRONDISSEMENT   (75010)</option>
                            <option>PARIS-11E-ARRONDISSEMENT   (75011)</option>
                            <option>PARIS-12E-ARRONDISSEMENT   (75012)</option>
                            <option>PARIS-13E-ARRONDISSEMENT   (75013)</option>
                            <option>PARIS-14E-ARRONDISSEMENT   (75014)</option>
                            <option>PARIS-15E-ARRONDISSEMENT   (75015)</option>
                            <option>PARIS-16E-ARRONDISSEMENT   (75016)</option>
                            <option>PARIS-17E-ARRONDISSEMENT   (75017)</option>
                            <option>PARIS-18E-ARRONDISSEMENT   (75018)</option>
                            <option>PARIS-19E-ARRONDISSEMENT   (75019)</option>
                            <option>PARIS-20E-ARRONDISSEMENT   (75020)</option>
                        </select>
                        <div class="invalid-tooltip">
                            Please select a valid state.
                        </div>
                    </div>
                    <div class="col-lg-1 col-md-6 col-sm-6 position-relative p-2 g-4">
                        <button class="btn  btn-sup " onclick="supprimerDiv('supprimerDivZone-${indice+1}')">
                            <svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="100" height="100" viewBox="0 0 26 26">
                            <path d="M 11.5 -0.03125 C 9.542969 -0.03125 7.96875 1.59375 7.96875 3.5625 L 7.96875 4 L 4 4 C 3.449219 4 3 4.449219 3 5 L 3 6 L 2 6 L 2 8 L 4 8 L 4 23 C 4 24.644531 5.355469 26 7 26 L 19 26 C 20.644531 26 22 24.644531 22 23 L 22 8 L 24 8 L 24 6 L 23 6 L 23 5 C 23 4.449219 22.550781 4 22 4 L 18.03125 4 L 18.03125 3.5625 C 18.03125 1.59375 16.457031 -0.03125 14.5 -0.03125 Z M 11.5 2.03125 L 14.5 2.03125 C 15.304688 2.03125 15.96875 2.6875 15.96875 3.5625 L 15.96875 4 L 10.03125 4 L 10.03125 3.5625 C 10.03125 2.6875 10.695313 2.03125 11.5 2.03125 Z M 6 8 L 11.125 8 C 11.25 8.011719 11.371094 8.03125 11.5 8.03125 L 14.5 8.03125 C 14.628906 8.03125 14.75 8.011719 14.875 8 L 20 8 L 20 23 C 20 23.5625 19.5625 24 19 24 L 7 24 C 6.4375 24 6 23.5625 6 23 Z M 8 10 L 8 22 L 10 22 L 10 10 Z M 12 10 L 12 22 L 14 22 L 14 10 Z M 16 10 L 16 22 L 18 22 L 18 10 Z"></path>
                            </svg>
                        </button>
                    </div>
                </div>
    `;

    // Créer un élément div temporaire
    var tempDiv = document.createElement('div');
    tempDiv.innerHTML = nouveauDiplomeHTML;

    // Insérer le nouveau diplôme juste avant le bouton "Ajouter un diplôme"
    var boutonAjouterDiplomeDiv = document.getElementById('boutonAjouterZone');
    boutonAjouterDiplomeDiv.insertAdjacentHTML('afterend', nouveauDiplomeHTML);

    // re-ordonner les ID et les Paramètre des fonctions
    ReOrderIdZones();
}

// Fonction pour réordonner les ID et les paramètres des div des matières à enseigner
function ReOrderIdZones(){

    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row g-2 ajout-zone");

    for (var i = 0; i < listDiv.length; i++) {
        var newId = "supprimerDivMatiere-" + (i + 1);
        listDiv[i].id = newId;

        var button = listDiv[i].querySelector("button");
        button.setAttribute("onclick", "supprimerDiv('" + newId + "')");

        // Mettez à jour le texte du bouton avec la valeur de newId
        //button.innerText = "Sup-" + (i + 1);
    }
}

// fonction pour redimentionner les Textarea selon leur contenu
function adjustTextareaHeight() {
    const textareas = document.getElementsByClassName('form-control profil');

    for (let i = 0; i < textareas.length; i++) {
        const textarea = textareas[i];
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight - 2) + 'px';
    }
}