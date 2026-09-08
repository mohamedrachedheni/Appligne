//***********************************  liée à tous les pages contenant un champ input téléphone début   *********************** */

//<!-- pour charger bootstrap@5.3.2 -->
//document.write('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"'
// + 'integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL"' +
//'crossorigin="anonymous" ></script>');

// Lien vers Font Awesome
// il permet à la page web d'utiliser les icônes de la bibliothèque Font Awesome 
//document.write('<script src="https://kit.fontawesome.com/1d95b4176e.js" crossorigin="anonymous"></script>');

////***********************************  liée à tous les pages contenant un champ input téléphone fin   *********************** */

//***********************************  liée à tous les pages contenant un champ input téléphone début   *********************** */

// Fonction pour charger les scripts dynamiquement (méthode moderne)
function loadScript(src, integrity = null, crossorigin = null) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        if (integrity) script.integrity = integrity;
        if (crossorigin) script.crossOrigin = crossorigin;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Chargement de Bootstrap 5.3.2 (méthode moderne)
loadScript(
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL',
    'anonymous'
).catch(error => console.error('Erreur chargement Bootstrap:', error));

// Chargement de Font Awesome (méthode moderne)
loadScript('https://kit.fontawesome.com/1d95b4176e.js')
    .catch(error => console.error('Erreur chargement FontAwesome:', error));

//***********************************  liée à tous les pages contenant un champ input téléphone fin   *********************** */