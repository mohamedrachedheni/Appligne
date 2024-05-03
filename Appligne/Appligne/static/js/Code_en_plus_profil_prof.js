// http://localhost:8000/profil_prof/2/
// fonction pour redimentionner les Textarea selon leur contenu
function adjustTextareaHeight() {
    const textareas = document.getElementsByClassName('form-control profil');

    for (let i = 0; i < textareas.length; i++) {
        const textarea = textareas[i];
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight - 2) + 'px';
    }
}
