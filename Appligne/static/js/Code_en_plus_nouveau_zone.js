    // Attache un événement de changement à l'élément select de région (reg_id)
    document.getElementById('reg_id').addEventListener('change', function () {
        // Récupère l'ID de la région sélectionnée
        var regionId = this.value;
        console.log('La valeur de select de région a changé ** début **.');
        // Vérifie si une région est sélectionnée
        if (regionId) {
            // Début de l'affichage d'un message dans la console lorsque la valeur du select de région change
            console.log('La valeur de select de région a changé ** début **.');
            // Effectue une requête AJAX pour obtenir les départements associés à la région sélectionnée
            var xhr = new XMLHttpRequest();
            xhr.open('GET', `/get_departments/?region_id=${regionId}`, true);
            xhr.onload = function () {
                // Vérifie si la requête s'est terminée avec succès
                if (xhr.status === 200) {
                    // Analyse la réponse JSON de la requête
                    var data = JSON.parse(xhr.responseText);
                    // Sélectionne l'élément select de département (dep_id)
                    var depSelect = document.getElementById('dep_id');
                    // Efface les options existantes dans le select de département
                    depSelect.innerHTML = '';

                    // Ajoute d'abord l'option "Sélectionnez un département"
                    var defaultOption = document.createElement('option');
                    defaultOption.text = 'Sélectionnez un département';
                    defaultOption.value = '';
                    defaultOption.disabled = true;
                    defaultOption.selected = true;
                    depSelect.add(defaultOption);

                    // Parcours les données récupérées pour créer les options du select de département
                    data.forEach(function (department) {
                        var option = document.createElement('option');
                        option.text = department.departement;
                        option.value = department.id;
                        depSelect.add(option);
                    });
                } else {
                    // Affiche un message d'erreur dans la console si la requête échoue
                    console.error('Une erreur s\'est produite');
                }
            };
            // Envoie la requête AJAX
            xhr.send();
        } else {
            // Efface les options du select de département si aucune région n'est sélectionnée
            document.getElementById('dep_id').innerHTML = '';
        }
        // Affiche un message dans la console pour indiquer que la valeur du select de région a changé
        console.log('La valeur de select de région a changé.');
    });


    // a voire
    src="https://code.jquery.com/jquery-3.6.0.min.js"

    function chargerRegions() {
        $.ajax({
            url: '/get_regions/', // Mettez ici l'URL correcte
            type: 'GET',
            success: function(data) {
                var select = $('#reg_id');
                select.empty();
                
                // Ajoutez d'abord l'option "Sélectionnez une région"
                select.append($('<option>').attr('selected', 'selected').attr('disabled', 'disabled').text('Sélectionnez une région'));

                // Ensuite, ajoutez les options de la table Region
                $.each(data, function(index, item) {
                    select.append($('<option>').val(item.id).text(item.region));
                });
            }
        });
    }

    $(document).ready(function() {
        chargerRegions();
    });

    // Attache un événement de changement à l'élément select de département (dep_id)
    document.getElementById('dep_id').addEventListener('change', function () {
        // Récupère l'ID du département sélectionné
        var departmentId = this.value;
        
        // Vérifie si un département est sélectionné
        if (departmentId) {
            // Effectue une requête AJAX pour obtenir les communes associées au département sélectionné
            var xhr = new XMLHttpRequest();
            xhr.open('GET', `/get_communes/?department_id=${departmentId}`, true);
            xhr.onload = function () {
                // Vérifie si la requête s'est terminée avec succès
                if (xhr.status === 200) {
                    // Analyse la réponse JSON de la requête
                    var data = JSON.parse(xhr.responseText);
                    // Sélectionne l'élément select des communes (com_id)
                    var comSelect = document.getElementById('com_id');
                    // Efface les options existantes dans le select des communes
                    comSelect.innerHTML = '';
                    // Parcours les données récupérées pour créer les options du select des communes
                    data.forEach(function (commune) {
                        var option = document.createElement('option');
                        // Inclure le code postal entre parenthèses s'il est défini, sinon afficher une chaîne vide
                        var postalCode = commune.code_postal ? ` (${commune.code_postal})` : '';
                        option.text = `${commune.commune}${postalCode}`;
                        option.value = `${commune.id}_${commune.commune}`;
                        option.id = commune.id;
                        comSelect.add(option);
                    });
                } else {
                    // Affiche un message d'erreur dans la console si la requête échoue
                    console.error('Une erreur s\'est produite');
                }
            };
            // Envoie la requête AJAX
            xhr.send();
        } else {
            // Efface les options du select des communes si aucun département n'est sélectionné
            document.getElementById('com_id').innerHTML = '';
        }
    });

    // Définir la matière sélectionnée par Ajouter l'attribut selected
    // le paramètre selector est par défaut = 'com_id'
    function addChangeListener(selector = 'com_id') {
        // le selecteur dont id=selector
        const selectElement = document.querySelector('#'+selector);
        // quant l'évennement sur changement est déclanché
        selectElement.addEventListener('change', function(event) {
        //  récupérer la première option sélectionnée
        const selectedOption = this.selectedOptions[0];
        // si il y a une option selectionnée
        if (selectedOption) {
            selectedOption.setAttribute('selected', 'selected'); // Ajouter l'attribut selected
        }
        // pour tous options non selectionnées
        const options = Array.from(this.querySelectorAll('option'));
        options.forEach(option => {
            if (option !== selectedOption) {
                // Supprimez l'attribut selected           
                option.removeAttribute('selected'); // Supprimer l'attribut selected
            }
        });
        });
    }

    // fonction réservée au moment du chargement de la page
    // pour donner le code JS pour l'option commune si elle est sélectionnée
    // en donnant l'attribut selected
    document.addEventListener('DOMContentLoaded', function() {
        // Appel de la fonction sans paramètre, utilise le sélecteur par défaut
        addChangeListener();
    });

    /* sélectionnez les optios dans le premier select et les ajouter dans le deuxième */
    /* et rendre les options sélectionnées dans le premier select non visibles et désactivées, ou vice-versa, */ 
    /*en réorganisant les options dans le deuxième select par ID de manière croissant*/
    /* Les paramaitres près définis: .btn-ajouter; .btn-enlever; #com_id; #com_chx_id */
    function gestionSelection() {
        // Sélecteurs pour le premier select de la liste de tous les niveaux
        // et le second select des niveaux choisis
        var selecteurPremier = "#com_id";
        var selecteurSecond = "com_chx_id";
        
        // Lorsque le bouton "ajouter" est cliqué
        // les options sélectionnées deviennent non visible dans le premier select et passent au deuxième select

        $(document).on('click', ".btn-ajouter", function() {
            // Récupérez les options sélectionnées dans le premier select
            var selectedOptions = $(selecteurPremier + " option:selected");

            // Parcours de chaque option sélectionnée
            selectedOptions.each(function() {
                var selectedOption = $(this).clone(); // Clone l'option sélectionnée
                var selectedOptionId = selectedOption.attr('id'); // Récupère l'ID de l'option sélectionnée
                
                // rendre l'attribut de l'option selectionnée: selected
                selectedOption.attr('selected', 'selected');

                // Ajoute l'option au second select
                $('#' + selecteurSecond).append(selectedOption);

                // Change le contenu du name de l'option ajoutée pour correspondre à son ID
                //selectedOption.attr('name', selectedOptionId);

                // Réorganisez les options dans le deuxième select par leur ID
                sortOptionsById(selecteurSecond);
                
                // Rendre non visible l'option avec le même ID dans le premier select
                $(selecteurPremier + " option[id='" + selectedOptionId + "']").prop('disabled', true).hide();
            });
        });


        // Lorsque le bouton "enlever" est cliqué
        // les options sélectionnées dans le deuxième select sont
        // supprimées et deviennent visible dans le premier sélect
        $(document).on('click', ".btn-enlever", function() {
            // Récupérez les options sélectionnées dans le second select
            var selectedOptions = $('#' + selecteurSecond + " option:selected");

            // Parcours de chaque option sélectionnée
            selectedOptions.each(function() {
                var selectedOptionId = $(this).attr('id'); // Récupère l'ID de l'option sélectionnée
                
                // Rend visible l'option avec le même ID dans le premier select
                $(selecteurPremier + " option[id='" + selectedOptionId + "']").prop('disabled', false).show();

                $(this).remove(); // Supprime l'option du second select
            });
        });

        // Lorsque le bouton "enlever" est cliqué
        // les options sélectionnées dans le deuxième select sont
        // supprimées et deviennent visible dans le premier sélect
        $(document).on('click', ".btn-enlever", function() {
            // Récupérez les options sélectionnées dans le second select
            var selectedOptions = $('#' + selecteurSecond + " option:selected");

            // Parcours de chaque option sélectionnée
            selectedOptions.each(function() {
                var selectedOptionId = $(this).attr('id'); // Récupère l'ID de l'option sélectionnée
                
                // Rend visible l'option avec le même ID dans le premier select
                $(selecteurPremier + " option[id='" + selectedOptionId + "']").prop('disabled', false).show();

                $(this).remove(); // Supprime l'option du second select
            });
        });
    }

    // Attendez que le DOM soit complètement chargé
    // Pour sélectionner les options du premier sélect vers le deuxième
    // au chargement de la page 
    $(document).ready(function() {
        // Appel de la fonction générique 
        // elle est réservée au moment du chargement des pages web
        gestionSelection();
    });

    /*  oui */
    // Récupération du formulaire
    var formNouvelleMatiere = document.getElementById('formNouvelleZone');
    // Paramaitre par défaut 'com_chx_id', remarque: la fonction à pour origine nouveau_matiere;html
    function selectNiveauxById() {

        // Ajout d'un écouteur d'événements pour l'événement de soumission du formulaire
        formNouvelleMatiere.addEventListener('submit', function(event) {
            
            // Récupération du menu déroulant (select)
            var selectNiveau = document.getElementById('com_chx_id');

            // Sélection de toutes les options dans le menu déroulant
            for(var i = 0; i < selectNiveau.options.length; i++) {
                selectNiveau.options[i].selected = true;
            }
        });
    };
    /*  oui */
    // Ajout d'un écouteur d'événements pour l'événement de soumission du formulaire
    // fonction réservée à l'évennement juste avant le moment du soumission du formulaire au submit
    // lorsque le bouton type="submit" est cliqué (name="btn_eng")
    // pour sélectionner tous les options du deuxième select
    document.addEventListener('DOMContentLoaded', function() {
        // Appel de la fonction sans paramètre, utilise le sélecteur par défaut
        selectNiveauxById();
    });

    /* oui */
    // Fonction pour réorganiser les options par leur ID par ordre croissant
    function sortOptionsById(selectId) {
        var select = $("#" + selectId);
        var options = select.find("option");

        options.sort(function(a, b) {
            return parseInt(a.id.split("_").pop()) - parseInt(b.id.split("_").pop());
        });

        select.html(options);
    }
