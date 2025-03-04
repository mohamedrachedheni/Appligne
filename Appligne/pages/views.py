
from accounts.models import Prof_zone, Departement, Matiere, Niveau, Region, Professeur, Format_cour, Pro_fichier, Diplome_cathegorie
from accounts.models import Diplome, Experience, Prof_doc_telecharge, Pays, Experience_cathegorie, Mes_eleves, Eleve
from accounts.models import  Email_telecharge, Prix_heure, Prof_mat_niv, Historique_prof, Commune, Payment, Demande_paiement, DetailAccordReglement, AccordReglement
from eleves.models import Temoignage, Parent
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.db.models import OuterRef, Subquery, DecimalField, Q, F, DurationField
from django.core.validators import  EmailValidator
from django.core.exceptions import  ValidationError, ObjectDoesNotExist
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.core.validators import validate_email, EmailValidator
from django.urls import reverse
from django.utils import timezone
from django.db.models import Min, Max




# Create your views here.

# créer une méthode utilitaire :
def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


def index(request):
    # les paramètres par défaut pour les champs de recherche prof
    radio_name = "a_domicile"
    matiere_defaut = "Maths"
    niveau_defaut = "Terminale Générale"
    region_defaut = "ILE-DE-FRANCE"
    departement_defaut = "PARIS"

    # Récupère toutes les matières, niveaux, régions et départements pour les listes déroulentes
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)

    # Gérer la pagination des témoignages avec les 4 meilleurs témoignages (Très bien, Excellent)
    temoignage_tris = []
    eleve_temoignage = set()
    prof_temoignage = set()

    # Récupérer les témoignages avec une évaluation égale ou supérieure à 4 (Très bien, Excellent)
    temoignages = Temoignage.objects.filter(evaluation_eleve__gte=4)

    # Boucle pour filtrer les témoignages uniques par élève et professeur, et limiter à 4 résultats
    for temoignage in temoignages:
        if temoignage.user_eleve not in eleve_temoignage and temoignage.user_prof not in prof_temoignage:
            eleve_temoignage.add(temoignage.user_eleve)
            prof_temoignage.add(temoignage.user_prof)
            temoignage_tris.append(temoignage)
            if len(temoignage_tris) >3:
                break


    context = {
        'matieres': matieres,
        'niveaux': niveaux,
        'regions': regions,
        'departements': departements,
        'radio_name': radio_name,
        'matiere_defaut': matiere_defaut,
        'niveau_defaut': niveau_defaut,
        'region_defaut': region_defaut,
        'departement_defaut': departement_defaut,
        'temoignage_tris': temoignage_tris,
    }

    if 'region' in request.POST: # si la page et actiée par input name='region'
        # celà se produit lorsque  JS  actualiser laliste deroulente Région suite au changement de l'option 
        # sélectionnéée dans la liste déroulente département
        # récupérer matiere_defaut, niveau_defaut, region_defaut
        matiere_defaut = request.POST['matiere'] # les derniers paramètres sélectionnés
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']

        # récupérer format cours
        if request.POST.get('a_domicile', None):
            radio_name = "a_domicile"
        if request.POST.get('webcam', None):
            radio_name = "webcam"
        if request.POST.get('stage', None):
            radio_name = "stage"
        if request.POST.get('stage_webcam', None):
            radio_name = "stage_webcam"

        # actualiser la liste des départements selon la région sélectionnée
        # est définir par défaut le premier département de la liste comme: departement_defaut
        departements = Departement.objects.filter(region__region=region_defaut) # la nouvelle liste des départements pour la liste déroulente département
        departement_defaut = Departement.objects.filter(region__region=region_defaut).first() # le premier de la liste des départements pour le champ input
        
        context.update({ # pour metre à jour les éléments susseptibles d'etre modifiés
            'departements': departements, # liste data
            'radio_name': radio_name,
            'matiere_defaut': matiere_defaut,
            'niveau_defaut': niveau_defaut,
            'region_defaut': region_defaut,
            'departement_defaut': departement_defaut, # paramètre du champ input
            'temoignages': temoignages,
        })
        
    if request.method == 'POST' and 'btn_rechercher' in request.POST:
        # Annuler les données précédentes dans la session
        keys_to_clear = [
            'radio_name', 'radio_name_text', 
            'matiere_defaut', 'niveau_defaut', 
            'region_defaut', 'departement_defaut'
        ]
        for key in keys_to_clear:
            request.session.pop(key, None)  # Supprime si existe, sinon rien

        # Mettre à jour les données de la session pour une nouvelle recherche
        if request.POST.get('a_domicile'):
            request.session['radio_name'] = "a_domicile"
            request.session['radio_name_text'] = "Cours à domicile"
        elif request.POST.get('webcam'):
            request.session['radio_name'] = "webcam"
            request.session['radio_name_text'] = "Cours par webcam"
        elif request.POST.get('stage'):
            request.session['radio_name'] = "stage"
            request.session['radio_name_text'] = "Stage pendant les vacances"
        elif request.POST.get('stage_webcam'):
            request.session['radio_name'] = "stage_webcam"
            request.session['radio_name_text'] = "Stage par webcam"

        # Stocker les filtres dans la session pour persistance
        request.session['matiere_defaut'] = request.POST.get('matiere', 'Non spécifié')
        request.session['niveau_defaut'] = request.POST.get('niveau', 'Non spécifié')
        request.session['region_defaut'] = request.POST.get('region', 'Non spécifié')
        request.session['departement_defaut'] = request.POST.get('departement', 'Non spécifié')

        # # Ajout du message informatif
        # messages.info(
        #     request,
        #     f"radio_name = {request.session.get('radio_name', 'Non spécifié')}; "
        #     f"radio_name_text = {request.session.get('radio_name_text', 'Non spécifié')}; "
        #     f"matiere_defaut = {request.session.get('matiere_defaut', 'Non spécifié')}; "
        #     f"niveau_defaut = {request.session.get('niveau_defaut', 'Non spécifié')}; "
        #     f"region_defaut = {request.session.get('region_defaut', 'Non spécifié')}; "
        #     f"departement_defaut = {request.session.get('departement_defaut', 'Non spécifié')}."
        # )

        return redirect('liste_prof')

    return render(request, 'pages/index.html', context)

def liste_prof(request):
    if request.method == 'POST' and 'btn_rechercher' in request.POST:
        # Annuler les données précédentes dans la session
        keys_to_clear = [
            'radio_name', 'radio_name_text', 
            'matiere_defaut', 'niveau_defaut', 
            'region_defaut', 'departement_defaut'
        ]
        for key in keys_to_clear:
            request.session.pop(key, None)  # Supprime si existe, sinon rien

        # Mettre à jour les données de la session pour une nouvelle recherche
        if request.POST.get('a_domicile'):
            request.session['radio_name'] = "a_domicile"
            request.session['radio_name_text'] = "Cours à domicile"
        elif request.POST.get('webcam'):
            request.session['radio_name'] = "webcam"
            request.session['radio_name_text'] = "Cours par webcam"
        elif request.POST.get('stage'):
            request.session['radio_name'] = "stage"
            request.session['radio_name_text'] = "Stage pendant les vacances"
        elif request.POST.get('stage_webcam'):
            request.session['radio_name'] = "stage_webcam"
            request.session['radio_name_text'] = "Stage par webcam"

        # Stocker les filtres dans la session pour persistance
        request.session['matiere_defaut'] = request.POST.get('matiere', 'Non spécifié')
        request.session['niveau_defaut'] = request.POST.get('niveau', 'Non spécifié')
        request.session['region_defaut'] = request.POST.get('region', 'Non spécifié')
        request.session['departement_defaut'] = request.POST.get('departement', 'Non spécifié')

        # Ajout du message informatif
        # messages.info(
        #     request,
        #     f"radio_name = {request.session.get('radio_name', 'Non spécifié')}; "
        #     f"radio_name_text = {request.session.get('radio_name_text', 'Non spécifié')}; "
        #     f"matiere_defaut = {request.session.get('matiere_defaut', 'Non spécifié')}; "
        #     f"niveau_defaut = {request.session.get('niveau_defaut', 'Non spécifié')}; "
        #     f"region_defaut = {request.session.get('region_defaut', 'Non spécifié')}; "
        #     f"departement_defaut = {request.session.get('departement_defaut', 'Non spécifié')}."
        # )

        return redirect('liste_prof')
    # Récupérer ou définir les valeurs par défaut des filtres de recherche à partir de POST ou de la session
    # donner la priorité au request puis à la session puis à la valeur par défaut
    radio_name = request.POST.get('radio_name', request.session.get('radio_name', "a_domicile"))
    radio_name_text = request.POST.get('radio_name_text', request.session.get('radio_name_text', "Cours à domicile"))
    matiere_defaut = request.POST.get('matiere', request.session.get('matiere_defaut', "Maths"))
    niveau_defaut = request.POST.get('niveau', request.session.get('niveau_defaut', "Terminale Générale"))
    region_defaut = request.POST.get('region', request.session.get('region_defaut', "ILE-DE-FRANCE"))
    departement_defaut = request.POST.get('departement', request.session.get('departement_defaut', "PARIS"))
    tri = request.POST.get('tri', request.session.get('tri', "evaluation_decroissante"))
    if request.method == 'POST':
        request.session['tri'] = request.POST['tri'] # conserver le dernier choix des tris
    # Récupérer les filtres possibles pour les matières, niveaux, régions et départements
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)

    # ce teste est non utile car la fonction ajax l'a remplacé
    if 'region' in request.POST and not 'btn_rechercher' in request.POST: # si la page et actiée par input name='region' seulement sans recherche
        departement_defaut = Departement.objects.filter(region__region=region_defaut).first() # le premier de la liste des départements pour le champ input*
    

    # Gérer les formats de cours sélectionnés dans le cas request.POST avec ou sans recherche
    # ces testes sont obligatoire si non erreur de résultat, c'est la valeur session qui passe
    # if request.POST.get('a_domicile'):
    #     radio_name = "a_domicile"
    #     radio_name_text = "Cours à domicile"
    # elif request.POST.get('webcam'):
    #     radio_name = "webcam"
    #     radio_name_text = "Cours par webcam"
    # elif request.POST.get('stage'):
    #     radio_name = "stage"
    #     radio_name_text = "Stage pendant les vacances"
    # elif request.POST.get('stage_webcam'): # si on utilise else dans le dernier cas le résultat est faux, c'est la valeut "stage_webcam" qui passe dans le cas not request.POST
    #     radio_name = "stage_webcam"
    #     radio_name_text = "Stage par webcam"

    # Sous-requête pour récupérer le prix par heure en fonction des filtres
    prix_heure_subquery = Prix_heure.objects.filter(
        user=OuterRef('pk'),
        prof_mat_niv__matiere__matiere=matiere_defaut,
        prof_mat_niv__niveau__niveau=niveau_defaut,
        format=radio_name_text
    ).values('prix_heure')

    ordre_tri = '-historique_prof__moyenne_point_cumule' if tri == 'evaluation_decroissante' else 'annotated_prix_heure'
    # la recherche des prof doit etre en fonction
    # de la région qui est, elle meme, en foction du type de format du cours
    # Rechercher les professeurs avec les nouveaux critères si format cours est:("a_domicile", "stage")
    if radio_name=="stage" or radio_name=="a_domicile":
        professeurs = User.objects.filter(
            professeur__isnull=False,
            prof_mat_niv__matiere__matiere=matiere_defaut,
            prof_mat_niv__niveau__niveau=niveau_defaut,
            prof_zone__commune__departement__departement=departement_defaut,
            **{f'format_cour__{radio_name}': True}
        ).annotate(
            annotated_prix_heure=Subquery(prix_heure_subquery[:1], output_field=DecimalField())
        ).select_related('historique_prof').prefetch_related(
            'experience_set', 'prof_mat_niv_set', 'diplome_set', 'professeur', 'pro_fichier'
        ).distinct().order_by(ordre_tri)
    else: # Le crière de la région n'est pas prix en compte pour format cours est:("webcam", "stage_webcam")
        # le critaire de la région n'a plus de sense
        professeurs = User.objects.filter(
            professeur__isnull=False,
            prof_mat_niv__matiere__matiere=matiere_defaut,
            prof_mat_niv__niveau__niveau=niveau_defaut,
            # prof_zone__commune__departement__departement=departement_defaut,
            **{f'format_cour__{radio_name}': True}
        ).annotate(
            annotated_prix_heure=Subquery(prix_heure_subquery[:1], output_field=DecimalField())
        ).select_related('historique_prof').prefetch_related(
            'experience_set', 'prof_mat_niv_set', 'diplome_set', 'professeur', 'pro_fichier'
        ).distinct().order_by(ordre_tri)

    # Gérer la pagination avec 4 professeurs par page
    elements_par_page = 4
    paginator = Paginator(professeurs, elements_par_page)
    page = request.GET.get('page', 1)
    professeurs = paginator.get_page(page)

    # Préparer le contexte pour afficher les résultats
    context = {
        'professeurs': professeurs,
        'matieres': matieres,
        'niveaux': niveaux,
        'regions': regions,
        'departements': departements,
        'radio_name': radio_name,
        'matiere_defaut': matiere_defaut,
        'niveau_defaut': niveau_defaut,
        'region_defaut': region_defaut,
        'departement_defaut': departement_defaut,
        'tri': tri,
    }

    # Rendre la page avec le contexte (résultats par défaut ou après recherche)
    return render(request, 'pages/liste_prof.html', context)









def profil_prof(request, id_user):
    # Ajout du message informatif
    # messages.info(
    #     request,
    #     f"radio_name = {request.session.get('radio_name', 'Non spécifié')}; "
    #     f"radio_name_text = {request.session.get('radio_name_text', 'Non spécifié')}; "
    #     f"matiere_defaut = {request.session.get('matiere_defaut', 'Non spécifié')}; "
    #     f"niveau_defaut = {request.session.get('niveau_defaut', 'Non spécifié')}; "
    #     f"region_defaut = {request.session.get('region_defaut', 'Non spécifié')}; "
    #     f"departement_defaut = {request.session.get('departement_defaut', 'Non spécifié')}."
    # )
    user = get_object_or_404(User, id=id_user)

   # Récupérer les témoignages
    temoignages = Temoignage.objects.filter(user_prof=user).distinct()

    # Pagination : diviser la liste des professeurs par pages de 4 éléments
    elements_par_page = 3
    paginator = Paginator(temoignages, elements_par_page)
    page = request.GET.get('page', 1)
    temoignages = paginator.get_page(page)

    # récupérer Historique_prof
    historique_prof = Historique_prof.objects.filter(user=user).first()
    
    # Utilisez prefetch_related avec distinct pour précharger les départements et éviter les répétitions
    prof_zones = Prof_zone.objects.filter(user=user).select_related('commune__departement')
    
    # Récupérer les départements distincts à partir des prof_zones: c'est un regroupement des valeur departement
    departements_distincts = Departement.objects.filter(id__in=prof_zones.values_list('commune__departement_id', flat=True)).distinct()
    
    # Déterminer prix_heure selon les paramètres de recherche dans la session
    niveau = request.session.get('niveau_defaut', None)
    if niveau is not None:
        niveau_id = Niveau.objects.get(niveau=niveau)
    else:
        niveau_id = None

    matiere = request.session.get('matiere_defaut', None)
    if matiere is not None:
        matiere_id = Matiere.objects.get(matiere=matiere)
    else:
        matiere_id = None

    if niveau_id and matiere_id:
        prof_mat_niv = Prof_mat_niv.objects.get(user=user, matiere=matiere_id, niveau=niveau_id)
        
        format = request.session.get('radio_name', None)
        if format == "a_domicile":
            format_cour = "Cours à domicile"
        elif format == "webcam":
            format_cour = "Cours par webcam"
        elif format == "stage":
            format_cour = "Stage pendant les vacances"
        else:
            format_cour = "Stage par webcam"
        
        prix_heure_obj = Prix_heure.objects.filter(user=user, format=format_cour, prof_mat_niv=prof_mat_niv).first()
        prix_heure = str(prix_heure_obj.prix_heure) if prix_heure_obj else 'N/A'
    else:
        prix_heure = 'N/A'

    # Liste des Prof
    # Valeurs par défaut pour les paramètres de recherche
    radio_name = request.session.get('radio_name', "a_domicile")  # Cours à domicile par défaut
    radio_name_text = request.session.get('radio_name_text', "Cours à domicile")
    matiere_defaut = request.session.get('matiere_defaut', "Maths")
    niveau_defaut = request.session.get('niveau_defaut', "Terminale Générale")
    region_defaut = request.session.get('region_defaut', "ILE-DE-FRANCE")
    departement_defaut = request.session.get('departement_defaut', "PARIS")
    tri = 'evaluation_decroissante'

    # # Récupérer les listes des matières, niveaux, régions et départements pour les filtres de recherche
    # matieres = Matiere.objects.all()
    # niveaux = Niveau.objects.all()
    # regions = Region.objects.filter(nom_pays__nom_pays='France')
    # departements = Departement.objects.filter(region__region=region_defaut)

    # Sous-requête pour récupérer le prix par heure selon la matière, le niveau et le format du cours
    prix_heure_subquery = Prix_heure.objects.filter(
        user=OuterRef('pk'),  # Lien avec le professeur
        prof_mat_niv__matiere__matiere=matiere_defaut,
        prof_mat_niv__niveau__niveau=niveau_defaut,
        format=radio_name_text  # Format du cours (domicile, webcam, etc.)
    ).values('prix_heure')

    # Récupérer la liste des professeurs filtrés par les paramètres de recherche par défaut
    professeurs = User.objects.filter(
    professeur__isnull=False,  # Exclure les utilisateurs qui ne sont pas professeurs
    prof_mat_niv__matiere__matiere=matiere_defaut,
    prof_mat_niv__niveau__niveau=niveau_defaut,
    prof_zone__commune__departement__departement=departement_defaut,
    **{f'format_cour__{radio_name}': True}  # Dynamique selon le type de cours sélectionné
    ).annotate(
        # Annoter les professeurs avec leur prix par heure en fonction de la sous-requête
        annotated_prix_heure=Subquery(prix_heure_subquery[:1], output_field=DecimalField())
    ).select_related(
        'historique_prof'  # Charger les enregistrements Historique_prof liés via OneToOne
    ).prefetch_related(
        'experience_set', 'prof_mat_niv_set', 'diplome_set', 'professeur', 'pro_fichier'
    ).distinct().order_by('-historique_prof__moyenne_point_cumule')

    # Pagination : diviser la liste des professeurs par pages de 4 éléments
    elements_par_page_prof = 3
    paginator_prof = Paginator(professeurs, elements_par_page_prof)
    page_prof = request.GET.get('page', 1)
    professeurs = paginator_prof.get_page(page_prof)

    

    context = {
        'user': user,
        'departements_distincts': departements_distincts,
        'prix_heure': prix_heure,
        'historique_prof': historique_prof,
        'temoignages': temoignages,
        'professeurs': professeurs,
    }
    return render(request, 'pages/profil_prof.html', context)





# destiné au email envoyées par les visiteur qui n'ont pas encore de compte
def nous_contacter(request):
    email = request.POST.get('email_user', '').strip()
    text_email = request.POST.get('text_email', '').strip()
    sujet = request.POST.get('sujet', '').strip()
    context={
    'email': email,
    'text_email': text_email,
    'sujet': sujet,
    }
    # Sélectionnez le premier utilisateur qui est superuser, staff et actif
    # par defaux pour eviter erreur de la base de donnée user-id can not be null
    # car le visiteur n'a pas de compt user
    # user = User.objects.filter(is_superuser=True, is_staff=True, is_active=True).first()
    teste = True
    if request.method == 'POST' and 'btn_enr' in request.POST:
        if not text_email:
            messages.error(request, "Vous devez désigner le contenu de votre email ")
            teste = False
        if not email:
                messages.error(request, "Vous devez indiquer votre email ")
                teste = False
        else:
            email_validator = EmailValidator() 
            try:
                email_validator(email) #teste format email
            except ValidationError:
                messages.error(request, "L'adresse email n'est pas valide.")
                teste = False
            
        # Sélectionner le premier enregistrement des superusers qui est dans ce cas le destinataire de l'Email
        user_destinataire = User.objects.filter(is_staff=1, is_active=1, is_superuser=1).first()
        user_destinataire_id = user_destinataire.id
        
        
        
        # si le sujet de l'email n'est pas défini dans le GET alors sujet='Sujet non défini'
        if not sujet: sujet = 'Sujet non défini'
        # on peut ajouter d'autres destinations: destinations = ['prosib25@gmail.com', 'autre_adresse_email']
        destinations = ['prosib25@gmail.com']
        # Validation des emails dans destinations
        for destination in destinations:
            email_validator = EmailValidator() 
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                teste = False
        if teste:        
            try:
                send_mail(
                    sujet,
                    text_email,
                    email,
                    destinations,
                    fail_silently=False,
                )
                messages.success(request, "L'email a été envoyé avec succès. ")
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email: {str(e)}")
                teste = False
        
        if teste:
            email_telecharge = Email_telecharge( email_telecharge=email, text_email=text_email, user_destinataire=user_destinataire_id, sujet=sujet)
            email_telecharge.save()
            messages.success(request, "L'email a été enregistrer. ")
            return redirect('index')
        
    return render(request, 'pages/nous_contacter.html', context)

def compte_administrateur(request):
    # Récupérer l'utilisateur actuel
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not user.is_superuser and not user.is_staff:
        messages.error(request, "Vous n'êtes pas autorisé à acceder au compte administrateur.")
        return redirect('signin')


    # Effacer tous les paramètres de session sauf l'utilisateur
    keys_to_keep = ['_auth_user_id', '_auth_user_backend', '_auth_user_hash']
    keys_to_delete = [key for key in request.session.keys() if key not in keys_to_keep]
    for key in keys_to_delete:
        del request.session[key]
        
    return render(request, 'pages/compte_administrateur.html')



# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_compte_prof(request, user_id=0):
    """
    Vue permettant d'afficher tous les utilisateurs ayant un compte de professeur.
    Accessible uniquement par les administrateurs actifs.
    """
    if request.method == 'POST' and 'btn_fermer' in request.POST:
        return redirect('compte_administrateur')

    # Filtrer les utilisateurs liés au rôle de professeur et trier par prénom puis nom
    user_profs = User.objects.filter(professeur__isnull=False).order_by('first_name', 'last_name')

    # Vérifier si la liste est vide et ajouter un message d'erreur
    if not user_profs.exists():
        messages.error(request, "Aucun professeur trouvé.")
        return render(request, 'pages/admin_compte_prof.html')
    
    # Définir l'ID du professeur sélectionné (valeur par défaut : premier professeur)
    user_prof_first = User.objects.filter(professeur__isnull=False).last() # A changer user_prof_first par user_prof_last dans le template et le view
    user_prof_select_id = request.POST.get('user_prof_select_id', user_prof_first.id)

    if user_id!=0:
        user_prof_select_id=user_id
        user_prof_first = User.objects.filter(id=user_id).last()


    # Convertir l'ID sélectionné en entier avec gestion des erreurs
    try:
        user_prof_select_id = int(user_prof_select_id)
    except (ValueError, TypeError):
        user_prof_select_id = user_prof_first.id  # Utiliser l'ID du premier professeur par défaut

    # Récupérer l'utilisateur sélectionné ou lever une erreur 404 si non trouvé
    user_prof_select = get_object_or_404(User, id=user_prof_select_id, professeur__isnull=False)


    teste = True # pour autoriser l'enregistrement si tous les condition sont respectées

    # Modifier l'enregistrement du prof électionné dans la table user
    if request.method == 'POST' and 'btn_enr_user_prof' in request.POST:
        # récupérer les données du template
        username = request.POST.get('username', user_prof_select.username).strip()
        first_name = request.POST.get('first_name', user_prof_select.first_name).strip()
        last_name = request.POST.get('last_name', user_prof_select.last_name).strip()
        email = request.POST.get('email', user_prof_select.email).strip()

        if not first_name.strip() or not last_name.strip() or not email.strip() or not username.strip():
            messages.error(request, "Les champs email, first_name, last_name et username sont obligatoires de la table user.")
            teste = False
        
        # si l'email a été changé et que le nouveau email existe déjà
        if email != user_prof_select.email and User.objects.filter(email=email).exists():
            messages.error(request, "L'email est déjà utilisé, donnez un autre email")
            teste = False
        
        # si le user a été changé et que le nouveau user existe déjà
        if username != user_prof_select.username and User.objects.filter(username=username).exists():
            messages.error(request, "Le username est déjà utilisé, donnez un autre username")
            teste = False
        
        #tester le format de l'email
        email_validator = EmailValidator() # Initialiser le validateur d'email
        # Validation de l'email_prof
        try:
            email_validator(email)
        except ValidationError:
            messages.error(request, "Le format de l'email est incorrecte.")
            teste = False
        
        if teste: # si tous les données sont valides
            user_prof_select.first_name = first_name
            user_prof_select.last_name = last_name
            user_prof_select.email = email
            user_prof_select.username = username
            user_prof_select.is_active = 'is_active' in request.POST
            user_prof_select.save()

    # Modifier l'enregistrement du prof sélectionné dans la table Professeur
    if request.method == 'POST' and 'btn_enr_prof' in request.POST:
        # récupérer les données du template
        civilite = request.POST.get('civilite', user_prof_select.professeur.civilite).strip()
        phone = request.POST.get('phone', user_prof_select.professeur.numero_telephone).strip()
        date_naissance = request.POST.get('date_naissance', user_prof_select.professeur.date_naissance)
        adresse = request.POST.get('adresse', user_prof_select.professeur.adresse).strip()

        #Vérifier le format de la date
        try:
                # si la convertion est réussie
                date_naissance_nouveau_01 = datetime.strptime(date_naissance, '%d/%m/%Y') # date_naissance_nouveau_01 est crée juste pour tester le format de la date
        except ValueError:
            messages.error(request, "Format de date de naissance invalide. Utilisez jj/mm/aaaa")
            #date_naissance = user_prof_select.professeur.date_naissance
            teste = False
        if teste: # si tous les données sont valides
            # Mettre à jour les données du professeur 
            user_prof_select.professeur.adresse = adresse
            user_prof_select.professeur.numero_telephone = phone
            user_prof_select.professeur.civilite = civilite
            user_prof_select.professeur.set_date_naissance_from_str(date_naissance)
            # s'il y a un changement de photo d'identité
            if 'photo' in request.FILES: # s'il y a une nouvelle photo d'identité
                # Si l'ancienne photo d'identité existe son ficher est supprimé
                if user_prof_select.professeur.photo:
                    user_prof_select.professeur.photo.delete(save=False)
                user_prof_select.professeur.photo = request.FILES['photo'] # sésir la nouvelle photo d'identité
            user_prof_select.professeur.save()
    
    
    
    # Vérifier si la requête est POST et si le bouton 'btn_enr_format_cours' est soumis
    if request.method == 'POST' and 'btn_enr_format_cours' in request.POST:
        # Récupérer le format cours initial ou définir la valeur par défaut
        format_cour = Format_cour.objects.filter(user=user_prof_select).first()

        # Modifier l'enregistrement du prof électionné dans la table format_cour
        # Liste des formats possibles
        formats = ['chk_a_domicile', 'chk_webcam', 'chk_stage', 'chk_stage_webcam']
        # Création d'un dictionnaire pour vérifier les formats cochés
        format_states = {format: request.POST.get(format) is not None for format in formats}

        # Vérifier qu'au moins un format est coché
        if not any(format_states.values()):
            messages.error(request, "Il faut au moins cocher une case d'un format de cours.")
            teste = False

        if teste:
            # Mettre à jour ou créer un objet Format_cour
            if format_cour:
                # Mise à jour des champs existants
                format_cour.a_domicile = format_states.get('chk_a_domicile', format_cour.a_domicile)
                format_cour.webcam = format_states.get('chk_webcam', format_cour.webcam)
                format_cour.stage = format_states.get('chk_stage', format_cour.stage)
                format_cour.stage_webcam = format_states.get('chk_stage_webcam', format_cour.stage_webcam)
                format_cour.save()
            else:
                # Création d'un nouvel objet si aucun n'existe
                Format_cour.objects.create(
                    user=user_prof_select,
                    a_domicile=format_states.get('chk_a_domicile', False),
                    webcam=format_states.get('chk_webcam', False),
                    stage=format_states.get('chk_stage', False),
                    stage_webcam=format_states.get('chk_stage_webcam', False)
                )
                
            # Suppression des enregistrements Prix_heure non utilisés a la suite
            # de la Mise à jour des formats si l'objet existe déjà
            if not format_cour.a_domicile:
                Prix_heure.objects.filter(user=user_prof_select, format="Cours à domicile").delete()
            if not format_cour.webcam:
                Prix_heure.objects.filter(user=user_prof_select, format="Cours par webcam").delete()
            if not format_cour.stage:
                Prix_heure.objects.filter(user=user_prof_select, format="Stage pendant les vacances").delete()
            if not format_cour.stage_webcam:
                Prix_heure.objects.filter(user=user_prof_select, format="Stage par webcam").delete()
            
            messages.success(request, "Les nouveaux formats des cours sont enregistrés. Vous devez réviser vos prix par heure pour chaque enregistrement nouveau.")
    
    # Vérifier si la requête est POST et si le bouton 'btn_enr_fichier' est soumis
    if request.method == 'POST' and 'btn_enr_fichier' in request.POST:
        # Modifier l'enregistrement du prof électionné dans la table Prof_fichier
        titre_fiche  = request.POST.get('titre_fiche','')
        parcours  = request.POST.get('parcours','')
        pedagogie  = request.POST.get('pedagogie','')
        video_youtube_url = request.POST.get('video_youtube_url','')
        # Récupérer l'enregistrement existant
        ancien_enregistrement = Pro_fichier.objects.filter(user=user_prof_select).first()

        if ancien_enregistrement:
            # Mettre à jour les champs de l'enregistrement existant
            ancien_enregistrement.titre_fiche = titre_fiche
            ancien_enregistrement.parcours = parcours
            ancien_enregistrement.pedagogie = pedagogie
            ancien_enregistrement.video_youtube_url = video_youtube_url
            ancien_enregistrement.save()
        else:
            # Créer un nouvel enregistrement si aucun n'existe
            Pro_fichier.objects.create(
                user=user_prof_select,
                titre_fiche=titre_fiche,
                parcours=parcours,
                pedagogie=pedagogie,
                video_youtube_url=video_youtube_url
            )

        messages.success(request, "Les nouvelles descriptions sont enregistrés")

    # Vérifier si la requête est POST et si le bouton 'btn_enr_diplome' est soumis
    if request.method == 'POST' and 'btn_enr_diplome' in request.POST:
        # Stoquer les anciennes données du prof de la table Diplome
        prof_diplomes = Diplome.objects.filter(user_id=user_prof_select_id)
        # Modifier l'enregistrement du prof électionné dans la table Diplome
        # Liste des diplômes dans le request dont le nom commence par: diplome_
        diplome_keys = [key for key in request.POST.keys() if key.startswith('diplome_')]
        
        if not diplome_keys:
            messages.error(request, "Il faut donner au moins un diplôme  ")
            teste = False
        

        # début de l'enregistrement
        if teste:
            # supprimer les anciens enregistrements
            diplomes = Diplome.objects.filter(user_id=user_prof_select_id)
            diplomes.delete() # une copi des enregistrement est sauvegardée dans prof_diplomes en cas d"echec d'enregistrement
            for diplome_key in diplome_keys:
                i = int(diplome_key.split('_')[1])
                diplome_key = f'diplome_{i}' # c'est le name de la balise input diplome
                date_obtenu_key = f'date_obtenu_{i}'
                principal_key = f'principal_diplome_{i}'
                intitule_key = f'intitule_{i}'
                j = 0 # Pour tester s'il y a eu d'enregistrement si non les anciens enregistrement supprimés doivent être récupérés
                if request.POST.get(diplome_key):
                    diplome = request.POST.get(diplome_key)
                    if not diplome.strip() :  # Vérifie si la chaîne est vide ou contient seulement des espaces
                        messages.error(request, "Le diplôme ne peut pas être vide ou contenir uniquement des espaces.")
                        continue  # Move to the next iteration of the loop
                    if len(diplome) > 100:
                        diplome = diplome[:100]  # Prendre seulement les 100 premiers caractères
                        messages.info(request, "Le diplôme a été tronqué aux 100 premiers caractères.")
                    diplome_cathegorie = Diplome_cathegorie.objects.filter(dip_cathegorie=diplome)
                    if not diplome_cathegorie.exists():
                        # Le diplôme n'existe pas, nous devons l'ajouter à la table Diplome_cathegorie
                        pays_default = Pays.objects.get(nom_pays='France')  # Remplacez 'Default' par le nom du pays par défaut
                        new_diplome_cathegorie = Diplome_cathegorie.objects.create(nom_pays=pays_default, dip_cathegorie=diplome)
                        new_diplome_cathegorie.save()
                    
                    # Le diplôme existe déjà dans la table Diplome_cathegorie
                    # Requête pour récupérer l'objet Diplome_cathegorie
                    diplome_obj = Diplome_cathegorie.objects.get(dip_cathegorie=diplome)
                    # Récupérer l'ID de l'objet Diplome_cathegorie
                    diplome_cathegorie_id = diplome_obj.id
                    date_obtenu = request.POST.get(date_obtenu_key, None)
                    if date_obtenu:
                        # tester le format des dates
                        try:
                            # si la convertion est réussie
                            date_obtenu_01 = datetime.strptime(date_obtenu, '%d/%m/%Y') # debut_01 juste pour le try seulement
                        except ValueError:
                            date_obtenu = datetime.now().strftime('%d/%m/%Y')  # à améliorer cette logique d'enregistrement
                    if request.POST.get(principal_key, None) == "on":
                        principal = True
                    else: principal = False
                    intitule = request.POST.get(intitule_key, None)
                    # Vérification si le diplôme n'existe pas déjà pour cet utilisateur
                    if not  Diplome.objects.filter(user=user_prof_select, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule).exists():
                        if not date_obtenu:
                            date_obtenu = datetime.now().strftime('%d/%m/%Y')  # Prendre la date du jour au format jj/mm/aaaa
                        diplome_instance = Diplome(user=user_prof_select, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule, principal=principal)
                        diplome_instance.set_date_obtenu_from_str(date_obtenu)
                        diplome_instance.save()
                        j = j+1
                        
                    else: # si le diplome existe 
                        continue
                

            if j == 0:
                # récupérer les enregistrements supprimés
                k=0 # pour vérifier si tous les enregistrements ont été récupérés
                for prof_diplome in prof_diplomes: # erreur car prof_diplomes est supprimé
                    try:
                        # Créer et sauvegarder un nouveau diplôme
                        Diplome.objects.create(
                            obtenu=prof_diplome.obtenu,
                            intitule=prof_diplome.intitule,
                            principal=prof_diplome.principal,
                            user_id=prof_diplome.user_id,
                            diplome_cathegorie=prof_diplome.diplome_cathegorie,
                        )
                        k=k+1
                        if k==prof_diplomes.count(): messages.success(request, "Tous les anciens enregistrement du diplôme ont été récupérés.")
                        
                    except Exception as e:
                        messages.error(request, f"Erreur lors de l'ajout du diplôme : {str(e)}")
                        
    # Vérifier si la requête est POST et si le bouton 'btn_enr_experience' est soumis
    if request.method == 'POST' and 'btn_enr_experience' in request.POST:
        # Modifier l'enregistrement du prof électionné dans la table Experience
        experiences = Experience.objects.filter(user_id=user_prof_select_id)
        z=experiences.count()
        # Liste des expériences dans le request dont le nom commence par: experience_
        experience_keys = [key for key in request.POST.keys() if key.startswith('experience_')]
        if not experience_keys:
            messages.error(request, "Il faut donner au moins une expérience  ")
            teste = False
        

        # début de l'enregistrement
        if teste and z>0:
            
            # Stocker les anciennes données du prof dans la table Experience
            ancien_experiences = []

            # Préparer les anciennes expériences à partir des données initiales
            for experience in experiences:
                ancien_experiences.append({
                    'type': experience.type,
                    'debut': experience.debut,
                    'fin': experience.fin,
                    'actuellement': experience.actuellement,
                    'commentaire': experience.commentaire,
                    'principal': experience.principal,
                    'user_id': experience.user_id,
                })

            
            # pour paramètrer les indices des expèriences (voire template)
            diplomes = Diplome.objects.filter(user_id=user_prof_select_id)
            prof_diplomes_count= diplomes.count()
            # supprimer les anciens enregistrements
            experiences.delete()

            # Récupérer les diplômes modifiés dans le template
            for experience_key in experience_keys:
                i = int(experience_key.split('_')[1])
                experience_key = f'experience_{i}' # c'est le name de la balise input name="experience_{{ forloop.counter }}"
                date_debut_key = f'date_debut_{i*2 + prof_diplomes_count}'
                date_fin_key = f'date_fin_{i*2 + prof_diplomes_count + 1}'
                principal_key = f'principal_experience_{i}'
                actuellement_key = f'act_{i}'
                commentaire_key = f'comm_{i}'
                j = 0 # Pour tester s'il y a eu d'enregistrement si non les anciens enregistrement supprimés doivent être récupérés
                if request.POST.get(experience_key):
                    experience = request.POST.get(experience_key)
                    if not experience.strip() :  # Vérifie si la chaîne est vide ou contient seulement des espaces
                        messages.error(request, "Le diplôme ne peut pas être vide ou contenir uniquement des espaces.")
                        continue  # Move to the next iteration of the loop
                    if len(experience) > 100:
                        experience = experience[:100]  # Prendre seulement les 100 premiers caractères
                        messages.info(request, "Le diplôme a été tronqué aux 100 premiers caractères.")
                    
                    date_debut = request.POST.get(date_debut_key, None)
                    if date_debut:
                        # tester le format des dates
                        try:
                            # si la convertion est réussie
                            date_obtenu_01 = datetime.strptime(date_debut, '%d/%m/%Y') # debut_01 juste pour le try seulement
                        except ValueError:
                            date_debut = None
                    
                    date_fin = request.POST.get(date_fin_key, None)
                    if date_fin:
                        # tester le format des dates
                        try:
                            # si la convertion est réussie
                            date_obtenu_01 = datetime.strptime(date_fin, '%d/%m/%Y') # debut_01 juste pour le try seulement
                        except ValueError:
                            date_fin = None
                    # messages.info(request, f"debut = {date_debut} ; fin= {date_fin}")
                    if request.POST.get(principal_key, None) == "on":
                        principal = True
                    else: principal = False
                    actuellement = request.POST.get(actuellement_key) == "on" # c'est la même logique que pour principal_key
                    commentaire = request.POST.get(commentaire_key, None)

                    # Vérification si l'expérience n'existe pas déjà pour cet utilisateur
                    if not Experience.objects.filter(user=user_prof_select, type=experience,  commentaire=commentaire  ).exists():
                        experience_instance = Experience(user=user_prof_select, type=experience, commentaire=commentaire , principal=principal, actuellement=actuellement)
                        if date_debut: experience_instance.set_date_debut_from_str(date_debut)
                        if date_fin: experience_instance.set_date_fin_from_str(date_fin)
                        experience_instance.save()
                        j = j+1
                    else: # si le diplome existe 
                        continue
            if j>0: messages.success(request, f"Il y a eu {j} enregistrement(s) dans la table Experience et {z-j} enregistrement(s) supprimé(s)")    

            if j == 0:
                # récupérer les enregistrements supprimés
                k=0 # pour vérifier si tous les enregistrements ont été récupérés
                
                # Insérer les expériences dans la table Experience
                for ancien_experience in ancien_experiences:
                    try:
                        # Créer et sauvegarder une nouvelle expérience
                        Experience.objects.create(
                            type=ancien_experience['type'],
                            debut=ancien_experience['debut'],
                            fin=ancien_experience['fin'],
                            actuellement=ancien_experience['actuellement'],
                            commentaire=ancien_experience['commentaire'],
                            principal=ancien_experience['principal'],
                            user_id=ancien_experience['user_id'],
                        )
                        k += 1
                    except Exception as e:
                        # Ajouter un message d'erreur pour chaque échec
                        messages.error(request, f"Échec de l'enregistrement pour l'expérience : {ancien_experience}. Erreur : {e}")

                # Vérifier si tous les enregistrements ont été récupérés
                if k == len(ancien_experiences):
                    messages.success(request, "Tous les anciens enregistrements de la table Experience ont été récupérés.")
                else:
                    messages.warning(request, f"{k} sur {len(ancien_experiences)} expériences ont été récupérées avec succès.")
                        
    # Vérifier si la requête est POST et si le bouton 'btn_enr_mat_niv' est soumis
    if request.method == 'POST' and 'btn_enr_mat_niv' in request.POST:
        # Liste des matières dans le template
        matiere_keys = [key for key in request.POST.keys() if key.startswith('matiere_')]
        if not matiere_keys:
            messages.error(request, "Vous devez garder au moins une matière.")
            teste = False
        
        # début de l'enregistrement
        if teste:
            # Stoquer les enregistrement du prof de la table Prof_mat_nov
            matieres = Prof_mat_niv.objects.filter(user_id=user_prof_select_id)
            # supprimer les anciens enregistrements, mais ils sont stoqués dans prof_mat_niv au besoin
            prof_mat_niv_ancien = Prof_mat_niv.objects.filter(user_id=user_prof_select_id)
            prof_mat_niv_ancien.delete() # une copi des enregistrement est sauvegardée dans prof_diplomes en cas d"echec d'enregistrement
            
            j = 0 # pour tester si tous les enregistrement modifiés sont enregistrés
            for matiere_key in matiere_keys:
                # pour extraire du request les données des enregistrements
                i = int(matiere_key.split('_')[1])
                principal_key = f'principal_matiere_{i}'
                matiere_key = f'matiere_{i}'
                niveau_key = f'niveau_{i}'

                principal = request.POST.get(principal_key, False)
                matiere_name = request.POST.get(matiere_key, None)
                niveau_name = request.POST.get(niveau_key, None)
                principal_modif = True if principal == "on" else False

                # Récupération des objets Matiere et Niveau correspondants
                matiere_modif = Matiere.objects.get(matiere=matiere_name)
                niveau_modif = Niveau.objects.get(niveau=niveau_name)

                # Enregistrement
                prof_mat_niv = Prof_mat_niv(user_id=user_prof_select_id, matiere=matiere_modif, niveau=niveau_modif, principal=principal_modif)
                prof_mat_niv.save()
                j +=1
            if j==0:
                # récupérer les enregistrements supprimés
                k=0 # pour vérifier si tous les enregistrements ont été récupérés
                for matiere in matieres:
                    try:
                        # Créer et sauvegarder les anciens enregistrements
                        Prof_mat_niv.objects.create(
                            principal=matiere.principal,
                            matiere=matiere.matiere,
                            niveau=matiere.niveau,
                            user_id=matiere.user_id,
                        )
                        k=k+1
                        if k==matieres.count(): messages.success(request, "Tous les anciens enregistrement de la table Prof_mat_niv ont été récupérés.")
                        
                    except Exception as e:
                        messages.error(request,(
                                "Echèque d'enregistrement des modifications dans la table Prof_mat_niv"
                                "Erreur lors de la récupération des enregistrements dans la table Prof_mat_niv. "
                                "Probablement, il y a une perte d'enregistrement des expériences du professeur : "
                                f"{str(e)}"))

    # Vérifier si la requête est POST et si le bouton 'btn_enr_mat_niv' est soumis
    if request.method == 'POST' and 'btn_enr_prix' in request.POST:
        # Prépare les formats de cours en fonction des choix de l'utilisateur
        format_cour = Format_cour.objects.filter(user=user_prof_select).first() # 
        formats = {
            'a_domicile': 'Cours à domicile',
            'webcam': 'Cours par webcam',
            'stage': 'Stage pendant les vacances',
            'stage_webcam': 'Stage par webcam'
        }
        selected_formats = {key: value for key, value in formats.items() if getattr(format_cour, key)}

        # Récupère les prix horaires existants
        prix_heure_qs = Prix_heure.objects.filter(user=user_prof_select)
        
        # Liste des prix dans le template
        prix_keys = [key for key in request.POST.keys() if key.startswith('prix_heure-')]
        if not prix_keys:
            messages.error(request, "Vous devez sélectionner au moins une matière et un format de cours pour pouvoir définir vos tarifs horaires.")
            teste = False
        if teste:
            liste_prix_mat_niv_for = []
            for prix_key, prix in request.POST.items():
                if prix_key.startswith('prix_heure-') and prix: # Si le prix est défini
                    try:
                        prix_dec = Decimal(prix[:-4]).quantize(Decimal('0.00'))
                    except (InvalidOperation, ValueError):
                        messages.error(request, f"Erreur lors de la conversion du prix '{prix[:-4]}' en décimal.")
                        continue

                    if prix_dec < 10:
                        messages.info(request, "Les prix inférieurs à 10 Euro sont ignorés.")
                        continue

                    mat_niv_id_str, format_key = prix_key.split('-')[1].split('__') # définir mat_niv_id_str, format_key selon la structure de l'attribut name de la balise prix
                    try:
                        mat_niv_id = int(mat_niv_id_str)
                    except ValueError:
                        messages.error(request, f"Erreur lors de la conversion de l'ID '{mat_niv_id_str}' en entier.")
                        continue

                    liste_prix_mat_niv_for.append((mat_niv_id, selected_formats[format_key], prix_dec))

            if not liste_prix_mat_niv_for:
                messages.error(request, "Vous devez fixer au moins un prix supérieur ou égal à 10 Euro.") # à réviser avec Hichem
                teste = False

            if teste:
                # Remplace les anciens prix horaires par les nouveaux
                Prix_heure.objects.filter(user=user_prof_select).delete()
                Prix_heure.objects.bulk_create([
                    Prix_heure(user=user_prof_select, prof_mat_niv_id=mat_niv_id, format=format_label, prix_heure=prix_dec)
                    for mat_niv_id, format_label, prix_dec in liste_prix_mat_niv_for
                ])

                messages.success(request, "Lenregistrement des tarifs des cours par heure est achevé.")
    
    # Vérifier si la requête est POST et si le bouton 'btn_enr_zone' est soumis
    if request.method == 'POST' and 'btn_enr_zone' in request.POST:
        # Récupération de toutes les prof_zones pour le prof sélectionné dans list_prof_zones = {}
        list_prof_zones = [] # liste des zones enregistrées
        prof_zones = Prof_zone.objects.filter(user_id=user_prof_select_id)
        z=prof_zones.count()
        # Remplir la liste des zones
        for prof_zone in prof_zones:
            list_prof_zones.append(prof_zone.commune.commune)

        # Liste des zones dans le template
        zone_keys = [key for key in request.POST.keys() if key.startswith('zone_')]
        
        # messages.info(request, f"list_prof_zones = {list_prof_zones}")
        # Gérer le cas s'il n'y a pas de zone à enregistrées
        if not zone_keys and len(list_prof_zones ) >0:
            messages.info(request, f"Vous avez supprimé toutes les zones . ({len(list_prof_zones )} )")
            messages.info(request, "Vous devez avoir au moins une zone d'activité définie si vous proposez des cours en présentiel.")
            prof_zones.delete()
            teste = False
        if not zone_keys and len(list_prof_zones )==0:
            messages.info(request, f"Vous devez au moins avoire une zone d'activité si vous donner des cours en présentiel. ")
            teste = False
        
        if teste:
            prof_zones.delete() # pour les remplacer par les nouvelles
            try:
                j = 0 # Pour tester si tous les zones sont enregistrées
                # Boucle sur les zones soumises via le formulaire
                for zone_key in zone_keys:
                    i = int(zone_key.split('_')[1])
                    zone_key = f'zone_{i}'
                    zone_value = request.POST.get(zone_key, None)
                    # Diviser la chaîne en deux parties en utilisant '-- ' comme séparateur
                    parts = zone_value.split('-- ')
                    # Vérifier s'il y a au moins deux parties après la division
                    if len(parts) >= 2:
                        # Extraire la deuxième partie qui est celle juste après '--'
                        commune_nom = parts[1].strip()
                        # Récupération l'objets commune
                        commune_obj = Commune.objects.get(commune=commune_nom)
                        # Création de la relation Prof_zone
                        Prof_zone.objects.create(user=user_prof_select, commune=commune_obj)
                        j = j + 1
                    else: 
                        messages.info(request, f"Revoire le programmeur => erreur enregistrement zone d'activité: zone_value: {zone_value}")
                if j==0:
                    for commune_name in list_prof_zones:
                        commune = Commune.objects.get(commune=commune_name)
                        Prof_zone.objects.create(user=user_prof_select, commune=commune)
                    messages.info(request, "Les anciennes zones sont récupérées")
                elif j < len(zone_keys): f"Il y a {zone_keys.count() - j} zone(s) non enregistrée(s)."
                else: messages.success(request,f"Il y a {z-j} zone(s) supprimée(s) et {j} zone(s) gardée(s) ")
            except Exception as e:
                # Restaurer les anciennes zones
                for commune_name in list_prof_zones:
                    commune = Commune.objects.get(commune=commune_name)
                    Prof_zone.objects.create(user=user_prof_select, commune=commune)
                messages.error(request, "Une erreur système est survenue. Les anciennes zones ont été restaurées.")
                messages.error(request, f"Détails de l'erreur : {str(e)}")

    # Vérifier si la requête est POST et si le bouton 'btn_enr_prof_doc_telecharge' est soumis
    if request.method == 'POST' and 'btn_enr_prof_doc_telecharge' in request.POST:
        # Récupérer tous les documents associés au professeur sélectionné
        prof_docs = Prof_doc_telecharge.objects.filter(user_id=user_prof_select_id)
        existe_docs = prof_docs.exists()  # Vérifier si des documents existent

        # Obtenir les clés des documents envoyées dans le formulaire
        doc_keys = [key for key in request.POST.keys() if key.startswith('doc_telecharge_')]

        if existe_docs:
            if not doc_keys:  # Tous les documents ont été supprimés dans le template
                messages.info(request, f"Vous avez supprimé tous les documents. ({prof_docs.count()})")
                # Supprimer les documents et leurs fichiers associés
                for prof_doc in prof_docs:
                    if prof_doc.doc_telecharge:
                        prof_doc.doc_telecharge.delete(save=False)
                prof_docs.delete()  # Suppression des enregistrements
            else:
                # Supprimer uniquement les documents non présents dans les clés du template
                doc_ids_in_template = {
                    int(key.split('_id_')[1])
                    for key in doc_keys
                    if '_id_' in key and key.split('_id_')[1].isdigit()
                }
                doc_ids_to_delete = prof_docs.exclude(id__in=doc_ids_in_template)
                if doc_ids_to_delete.exists():
                    messages.info(request, f"{doc_ids_to_delete.count()} document(s) supprimé(s).")
                    for prof_doc in doc_ids_to_delete:
                        if prof_doc.doc_telecharge:
                            prof_doc.doc_telecharge.delete(save=False)
                    doc_ids_to_delete.delete()
                else:
                    messages.info(request, "Aucun changement dans les documents téléchargés.")

                

    # Vérifier si la requête est POST et si le bouton 'btn_email' est soumis
    if request.method == 'POST' and 'btn_email' in request.POST:
        email_user = request.POST.get('email_user', request.user.email)
        email_prof = request.POST.get('email_prof', user_prof_select.email)
        sujet = request.POST.get('sujet', 'Sujet non défini')
        text_email = request.POST.get('text_email')
        if not text_email:
            messages.error(request, "Veuillez compléter le contenu de l'email avant de l'envoyer.")
            teste=False

        # Valider l'adresse e-mail du professeur
        try:
            validate_email(email_prof)
        except ValidationError:
            messages.error(request, "L'adresse e-mail du professeur n'est pas valide.")

        # Valider l'adresse e-mail du email_user
        try:
            validate_email(email_user)
        except ValidationError:
            messages.error(request, "L'adresse e-mail du user n'est pas valide.")

        destinations = ['prosib25@gmail.com', email_prof]

        if teste:
            try:
                # Envoie l'email à tous les destinataires
                send_mail(sujet, text_email, email_user, destinations, fail_silently=False)
                # Message de succès si l'email a été envoyé
                messages.success(request, "L'email a été envoyé avec succès.")
            except Exception as e:
                # Message d'erreur si l'envoi échoue
                messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")

            # Enregistre l'email dans la base de données
            Email_telecharge.objects.create(
                user=request.user,
                email_telecharge=email_prof,
                text_email=text_email,
                user_destinataire=user_prof_select.id,
                sujet=sujet
            )
            messages.success(request, "Email enregistré")

    # Récupération de tous les diplomes pour le prof sélectionné
    diplomes = Diplome.objects.filter(user_id=user_prof_select_id)
    if not diplomes: 
        messages.info(request, "Aucun diplôme n'est enregistré. (Non obligatoire) ")
    prof_diplomes_count= diplomes.count() # pour paramétrer ID et Name des date_début et date_fin des expériences

    
    # Récupération de toutes les expériances pour le prof sélectionné
    experiences = Experience.objects.filter(user_id=user_prof_select_id)
    if not experiences: messages.info(request, "Aucune expérience n'est enregistrée. (Non obligatoire)")
    
    # Récupération de tous les prof_mat_nivs pour le prof sélectionné
    prof_mat_nivs = Prof_mat_niv.objects.filter(user_id=user_prof_select_id)
    if not prof_mat_nivs: messages.info(request, "Pas d'enregistrement dans la table prof_mat_niv pour le prof. (Il faut définir au moins une matière)")

    # Récupération de toutes les prof_zones pour le prof sélectionné
    prof_zones = Prof_zone.objects.filter(user_id=user_prof_select_id)
    if not prof_zones: messages.info(request, "Aucune zone d'activité n'est définie. (Non obligatoire si le format cours est à distance)")

    # Récupération de toutes les documente télécharger par le prof sélectionné
    prof_doc_telecharges = Prof_doc_telecharge.objects.filter(user_id=user_prof_select_id)
    if not prof_doc_telecharges: messages.info(request, "Aucun document justificatif n'est téléchargé. (non obligatoire)")

    # contenu émail du document téléchargé

    # Construction de la liste des chaînes "région - département - commune"
    zone_lists = []
    selected_formats = {}
    liste_enregistrements = []

    # Si le prof sélectionné a déjà des zones enregistrées
    if prof_zones.exists():
        
        for prof_zone in prof_zones:
            commune = prof_zone.commune
            departement = commune.departement
            region = departement.region
            zone_string = f"{region.region} - {departement.departement} -- {commune.commune}"
            zone_lists.append(zone_string)

    # Vérifie si le prof sélectionné a défini un format de cours
    format_cour = Format_cour.objects.filter(user_id=user_prof_select_id).first()

    if format_cour:
        # Récupère le premier enregistrement de format de cours
        # format_cour = format_cour_qs.first()

        # Vérifie si le prof sélectionné a défini des matières et niveaux
        prof_mat_niv = Prof_mat_niv.objects.filter(user_id=user_prof_select_id)
        if not prof_mat_niv:
            messages.error(request, "Vous n'avez pas encore défini de matière pour vos cours.")
            # return redirect('compte_prof')

        # Prépare les formats de cours en fonction des choix du prof sélectionné
        formats = {
            'a_domicile': 'Cours à domicile',
            'webcam': 'Cours par webcam',
            'stage': 'Stage pendant les vacances',
            'stage_webcam': 'Stage par webcam'
        }
        selected_formats = {key: value for key, value in formats.items() if getattr(format_cour, key)}

        # Récupère les prix horaires existants
        prix_heure_qs = Prix_heure.objects.filter(user_id=user_prof_select_id)

        # Prépare la liste des enregistrements pour le template
        for format_key, format_label in selected_formats.items():
            for prof_mat_niveau in prof_mat_niv:
                prix_heure = prix_heure_qs.filter(
                    prof_mat_niv=prof_mat_niveau.id, format=format_label).first()
                prix_heure_value = str(prix_heure.prix_heure) if prix_heure else ""
                liste_enregistrements.append(
                    (prof_mat_niveau.id, prof_mat_niveau.matiere, prof_mat_niveau.niveau, prix_heure_value, format_key)
                )
    else:
        # Pas de format de cours défini pour ce professeur
        messages.info(request, "Vous n'avez pas encore défini de format pour vos cours. (Obligatoire)")


 
    experience_cathegories = Experience_cathegorie.objects.all()
    diplome_cathegories = Diplome_cathegorie.objects.all()
    matieres = Matiere.objects.all()
    niveaus = Niveau.objects.all()
    # Préparer les données du contexte
    context = {
        'user_profs': user_profs,
        'user_prof_select': user_prof_select,
        'experiences': experiences,
        'prof_mat_nivs': prof_mat_nivs,
        'zone_lists': zone_lists,
        'prof_doc_telecharges': prof_doc_telecharges,
        'liste_format': list(selected_formats.keys()),
        'liste_enregistrements': liste_enregistrements,
        'prof_diplomes_count': prof_diplomes_count, # pour paramétrer ID et Name des date_début et date_fin des expériences
        'diplomes': diplomes,
        'diplome_cathegories': diplome_cathegories,
        'matieres': matieres,
        'niveaus': niveaus,
        'experience_cathegories': experience_cathegories,
        'user_id':user_id,
    }
        

    # Rendre la page avec les données
    return render(request, 'pages/admin_compte_prof.html', context)


@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_email_recu(request, email_id):
    """ Afficher le contenu de l'email """

    email = Email_telecharge.objects.filter(id=email_id).first()  # envoyé par l'élève
    
    # Vérifier si l'email existe
    if not email:
        return HttpResponse("Email introuvable", status=404)

    # Conversion de la date au format jj/mm/aaaa
    date_telechargement = email.date_telechargement.strftime('%d/%m/%Y') if email.date_telechargement else "Non spécifiée"

    text_email = f"""
        Date de réception : {date_telechargement}

        Envoyé par : {email.user.first_name} {email.user.last_name}

        Email d'envoie : {email.email_telecharge}

        Sujet de l'email : {email.sujet}

        Contenu de l'email :
        {email.text_email}
        """
    context = {'text_email': text_email}

    if request.method == 'POST' and 'btn_fermer' in request.POST:
        return redirect('compte_administrateur')
    return render(request, 'pages/admin_email_recu.html', context)

@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_doc_recu(request, doc_id):
    """ Afficher le contenu de l'email """

    prof_doc_telecharge = Prof_doc_telecharge.objects.filter(id=doc_id).first()  # envoyé par l'élève
    
    # Vérifier si l'email existe
    if not prof_doc_telecharge:
        return HttpResponse("Document introuvable", status=404)

    # Conversion de la date au format jj/mm/aaaa
    date_telechargement = prof_doc_telecharge.date_telechargement.strftime('%d/%m/%Y') if prof_doc_telecharge.date_telechargement else "Non spécifiée"

    doc_telecharge = prof_doc_telecharge.doc_telecharge
    context = {'doc_telecharge': doc_telecharge}

    
    return render(request, 'pages/admin_doc_recu.html', context)

# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_compte_eleve(request, user_id=0):
    """
    Vue permettant d'afficher tous les utilisateurs ayant un compte de élève.
    Accessible uniquement par les administrateurs actifs.
    """
    # si le bouton 'btn_fermer' est activé revenir au template 'compte_administrateur'
    if request.method == 'POST' and 'btn_fermer' in request.POST:
        return redirect('compte_administrateur')

    # Filtrer les utilisateurs liés au rôle de élève et trier par prénom puis nom
    user_eleves = User.objects.filter(eleve__isnull=False).order_by('first_name', 'last_name')

    # Vérifier si la liste est vide et ajouter un message d'erreur
    if not user_eleves.exists():
        messages.error(request, "Aucun élève trouvé.")
        return render(request, 'pages/admin_compte_eleve.html')
    
    # Définir l'ID de l'élève sélectionné (valeur par défaut : dernier élève enregistré)
    user_eleve_last = User.objects.filter(eleve__isnull=False).last()
    user_eleve_select_id = request.POST.get('user_prof_select_id', user_eleve_last.id)

    if user_id != 0:
        user_eleve_select_id = user_id
        user_eleve_last = User.objects.filter(id=user_id).last()

    # Convertir l'ID sélectionné en entier avec gestion des erreurs
    try:
        user_eleve_select_id = int(user_eleve_select_id)
    except (ValueError, TypeError):
        user_eleve_select_id = user_eleve_last.id  # Utiliser l'ID du dernier élève enregistré par défaut

    # Récupérer l'utilisateur sélectionné ou lever une erreur 404 si non trouvé
    user_eleve_select = get_object_or_404(User, id=user_eleve_select_id, eleve__isnull=False)


    teste = True # pour autoriser l'enregistrement si tous les condition sont respectées

    # Modifier l'enregistrement électionné dans la table user
    if request.method == 'POST' and 'btn_enr_user_eleve' in request.POST:
        # récupérer les données du template
        username = request.POST.get('username', user_eleve_select.username).strip()
        first_name = request.POST.get('first_name', user_eleve_select.first_name).strip()
        last_name = request.POST.get('last_name', user_eleve_select.last_name).strip()
        email = request.POST.get('email', user_eleve_select.email).strip()

        if not first_name.strip() or not last_name.strip() or not email.strip() or not username.strip():
            messages.error(request, "Les champs email, first_name, last_name et username sont obligatoires de la table user.")
            teste = False
        
        # si l'email a été changé et que le nouveau email existe déjà
        if email != user_eleve_select.email and User.objects.filter(email=email).exists():
            messages.error(request, "L'email est déjà utilisé, donnez un autre email")
            teste = False
        
        # si le user a été changé et que le nouveau user existe déjà
        if username != user_eleve_select.username and User.objects.filter(username=username).exists():
            messages.error(request, "Le username est déjà utilisé, donnez un autre username")
            teste = False

        #tester le format de l'email
        email_validator = EmailValidator() # Initialiser le validateur d'email
        # Validation de l'email
        try:
            email_validator(email)
        except ValidationError:
            messages.error(request, "Le format de l'email est incorrecte.")
            teste = False
        
        if teste: # si tous les données sont valides
            user_eleve_select.first_name = first_name
            user_eleve_select.last_name = last_name
            user_eleve_select.email = email
            user_eleve_select.username = username
            user_eleve_select.is_active = 'is_active' in request.POST
            user_eleve_select.save()

    
    # Modifier l'enregistrement de l'élève sélectionné dans la table Eleve
    if request.method == 'POST' and 'btn_enr_eleve' in request.POST:
        # récupérer les données du template
        civilite = request.POST.get('civilite', user_eleve_select.eleve.civilite).strip()
        phone = request.POST.get('phone', user_eleve_select.eleve.numero_telephone).strip()
        date_naissance = request.POST.get('date_naissance', user_eleve_select.eleve.date_naissance)
        adresse = request.POST.get('adresse', user_eleve_select.eleve.adresse).strip()

        if date_naissance :
            #Vérifier le format de la date
            try:
                    # si la convertion est réussie
                    date_naissance_nouveau_01 = datetime.strptime(date_naissance, '%d/%m/%Y') # date_naissance_nouveau_01 est crée juste pour tester le format de la date
            except ValueError:
                messages.error(request, "Format de date de naissance invalide. Utilisez jj/mm/aaaa")
                #date_naissance = user_prof_select.professeur.date_naissance
                teste = False
        if teste: # si tous les données sont valides
            # Mettre à jour les données du professeur 
            user_eleve_select.eleve.adresse = adresse
            user_eleve_select.eleve.numero_telephone = phone
            user_eleve_select.eleve.civilite = civilite
            user_eleve_select.eleve.set_date_naissance_from_str(date_naissance)
            user_eleve_select.eleve.save()

    # Modifier l'enregistrement du parent de l'élève sélectionné dans la table Parent
    if request.method == 'POST' and 'btn_enr_eleve_parent' in request.POST:
        parent= Parent.objects.filter(user = user_eleve_select).first()

        # récupérer les données du template
        if parent:
            civilite_parent = request.POST.get('civilite_parent', user_eleve_select.parent.civilite).strip()
            prenom_parent = request.POST.get('prenom_parent', user_eleve_select.parent.prenom_parent).strip()
            nom_parent = request.POST.get('nom_parent', user_eleve_select.parent.nom_parent).strip()
            telephone_parent = request.POST.get('telephone_parent', user_eleve_select.parent.telephone_parent).strip()
            email_parent = request.POST.get('email_parent', user_eleve_select.parent.email_parent).strip()
        else:
            civilite_parent = request.POST.get('civilite_parent', '').strip()
            prenom_parent = request.POST.get('prenom_parent', '').strip()
            nom_parent = request.POST.get('nom_parent', '').strip()
            telephone_parent = request.POST.get('telephone_parent', '').strip()
            email_parent = request.POST.get('email_parent', '').strip()


        #tester le format de l'email
        email_validator = EmailValidator() # Initialiser le validateur d'email
        if email_parent != "":
            # Validation de l'email_prof
            try:
                email_validator(email_parent)
            except ValidationError:
                messages.error(request, "Le format de l'email du parent est incorrecte.")
                teste = False
        
        if teste:  # Si toutes les données sont valides
            # Mettre à jour les données du parent
            if parent: 
                # Si un parent existe, mettre à jour ses informations
                user_eleve_select.parent.prenom_parent = prenom_parent
                user_eleve_select.parent.nom_parent = nom_parent
                user_eleve_select.parent.civilite = civilite_parent
                user_eleve_select.parent.telephone_parent = telephone_parent
                user_eleve_select.parent.email_parent = email_parent
                user_eleve_select.parent.save()
            else:
                # Si aucun parent n'existe, créer un nouveau parent
                parent = Parent.objects.create(
                    prenom_parent=prenom_parent,
                    nom_parent=nom_parent,
                    civilite=civilite_parent,
                    telephone_parent=telephone_parent,
                    email_parent=email_parent,
                    user=user_eleve_select  # Associer l'élève au parent
                )
                # Associer le parent créé à l'élève
                user_eleve_select.parent = parent
                user_eleve_select.save()

    # Gérer l'enregistrement des témoignages
    if request.method == 'POST' and 'btn_enr_temoignage' in request.POST:
        # Récupérer tous les témoignage de l'élève sélectionné
        temoignages = Temoignage.objects.filter(user_eleve_id=user_eleve_select.id)
        existe_temoignages = temoignages.exists()  # Vérifier si des temoignages existent

        # Obtenir les clés des témoignages dans le formulaire
        temoignage_keys = [key for key in request.POST.keys() if key.startswith('text_eleve_id_')]

        if existe_temoignages:
            if not temoignage_keys:  # Tous les témoignages ont été supprimés dans le template
                messages.info(request, f"Vous avez supprimé tous les témoignages. ({temoignages.count()})")
                # Supprimer les témoignages
                temoignages.delete()  # Suppression des enregistrements
            else:
                # Supprimer uniquement les témoignages non présents dans les clés du template
                temoignage_ids_in_template = {
                    int(key.split('_id_')[1])
                    for key in temoignage_keys
                    if '_id_' in key and key.split('_id_')[1].isdigit()
                }
                temoignage_ids_to_delete = temoignages.exclude(id__in=temoignage_ids_in_template)
                if temoignage_ids_to_delete.exists():
                    messages.info(request, f"{temoignage_ids_to_delete.count()} témoignage(s) supprimé(s).")
                    temoignage_ids_to_delete.delete()
                else:
                    messages.info(request, "Aucun changement dans les témougnage.")

    # Vérifier si la requête est POST et si le bouton 'btn_email' est soumis
    if request.method == 'POST' and 'btn_email' in request.POST:
        email_user = request.POST.get('email_user', request.user.email)
        email_prof = request.POST.get('email_eleve', user_eleve_select.email)
        sujet = request.POST.get('sujet', 'Sujet non défini')
        text_email = request.POST.get('text_email')
        if not text_email:
            messages.error(request, "Veuillez compléter le contenu de l'email avant de l'envoyer.")
            teste=False

        # Valider l'adresse e-mail du professeur
        try:
            validate_email(email_prof)
        except ValidationError:
            teste = False
            messages.error(request, "L'adresse e-mail de l'élève n'est pas valide.")

        # Valider l'adresse e-mail du email_user
        try:
            validate_email(email_prof)
        except ValidationError:
            teste = False
            messages.error(request, "L'adresse e-mail du user n'est pas valide.")

        destinations = [email_prof]

        if teste:
            try:
                # Envoie l'email à tous les destinataires
                send_mail(sujet, text_email, email_user, destinations, fail_silently=False)
                # Message de succès si l'email a été envoyé
                messages.success(request, "L'email a été envoyé avec succès.")
            except Exception as e:
                # Message d'erreur si l'envoi échoue
                messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")

            # Enregistre l'email dans la base de données
            Email_telecharge.objects.create(
                user=request.user,
                email_telecharge=email_prof,
                text_email=text_email,
                user_destinataire=user_eleve_select.id,
                sujet=sujet
            )
            messages.success(request, "Email enregistré")

    temoignages = Temoignage.objects.filter(user_eleve=user_eleve_select)

    context = {
        'user_eleves': user_eleves,
        'user_eleve_select': user_eleve_select,
        'temoignages': temoignages,
        'user_id': user_id,
    }
    # Rendre la page avec les données
    return render(request, 'pages/admin_compte_eleve.html', context)

# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_liste_email_recu(request):

    user_id = request.user.id # ID admin

    # Fonction interne pour récupérer les emails en fonction des critères de filtrage
    def get_emails(filter_criteria):
        emails = Email_telecharge.objects.filter(user_destinataire=user_id, **filter_criteria).order_by('-date_telechargement')
        return emails

    # Filtrage par défaut pour les nouveaux emails (emails avec suivi = null)
    emails = get_emails({})

    # Vérification du type de requête et application des filtres en fonction du bouton cliqué
    if request.method == 'POST':
        if 'btn_tous' in request.POST:
            # Filtrer pour tous les emails
            emails = get_emails({})
        elif 'btn_nouveau' in request.POST:
            # Filtrer pour les nouveaux emails (suivi = null)
            emails = get_emails({'suivi__isnull': True})
        elif 'btn_attente' in request.POST:
            # Filtrer pour les emails en attente (suivi = 'Réception confirmée')
            emails = get_emails({'suivi': 'Réception confirmée'})
        elif 'btn_repondu' in request.POST:
            # Filtrer pour les emails répondus (suivi = 'Répondu')
            emails = get_emails({'suivi': 'Répondu'})
        elif 'btn_ignore' in request.POST:
            # Filtrer pour les emails ignorés (suivi = 'Mis à côté')
            emails = get_emails({'suivi': 'Mis à côté'})

    # Contexte à passer au template
    context = {
        'emails': emails
    }
    
    # Rendu de la page avec les emails filtrés
    return render(request, 'pages/admin_liste_email_recu.html', context)

# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_detaille_email(request, email_id):
    user = request.user # admin
    email = Email_telecharge.objects.filter(id=email_id).first() # récupérer l'email
    
    

    context = {'email': email, 'email_id': email_id}
    
    # Initialiser le validateur d'email
    email_validator = EmailValidator()

    if 'btn_ignorer' in request.POST: # bouton Ignorer activé
        email.suivi = 'Mis à côté'
        email.date_suivi = date.today()
        email.save() 
        messages.success(request, "L'email est enregistré en tant qu'email ignoré.")
        return redirect('admin_liste_email_recu') # Rediriger vers compte admin

    if 'btn_confirmer' in request.POST: # bouton confirmer activé
        email_expediteur = user.email # émail de l'administrateur
        email_source = email.email_telecharge
        sujet = "Confirmation de réception"
        text_email = f"""
        J'ai bien reçu votre email
        Date de réception : {email.date_telechargement.strftime('%d/%m/%Y')}
        Sujet de l'email : {email.sujet}
        Contenu de l'email :
        {email.text_email}
        """
        destinations = ['prosib25@gmail.com', email_source]

        # Validation de l'email_prof
        try:
            email_validator(email_expediteur)
        except ValidationError:
            messages.error(request, "L'adresse email du professeur est invalide.")
            return render(request, 'pages/admin_detaille_email.html', context)

        # Validation des emails dans destinations
        for destination in destinations:
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                return render(request, 'pages/admin_detaille_email.html', context)

        try:
            send_mail(sujet, text_email, email_expediteur, destinations, fail_silently=False)
            messages.success(request, "L'email a été envoyé avec succès.")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
        
        if not  email.user: # dans le cas ou l'expéditeur n'est un client
            return redirect('admin_liste_email_recu') # car l'expéditeur de l'email n'a pas d'identifiant ID

        email_telecharge = Email_telecharge(
            user=user,
            email_telecharge=email_expediteur,
            text_email=text_email,
            user_destinataire=email.user.id,
            sujet=sujet
        )
        email_telecharge.save() # Enregistrement de l'email envoyé

        # mis à jour de l'email reçu
        email.suivi = 'Réception confirmée'
        email.date_suivi = date.today()
        email.reponse_email_id = email_telecharge.id
        email.save() # mis à jour de l'email reçu

        messages.success(request, "Email enregistré")
        return redirect('admin_liste_email_recu')

    # if 'btn_repondre' in request.POST:
    #     return redirect('admin_reponse_email', email_id=email_id) # Redirigze ver page  email_id est transmis à reponse_email
    
    if 'btn_historique' in request.POST: # bouton historique activé
        if email.reponse_email_id==None:
            messages.info(request, "Il n'y a pas de réponse à cet email")
            return render(request, 'pages/admin_detaille_email.html', context) # rediriger vers la même page

        # rediriger vers la même page mais en changeant l'argument
        # il faut élaborer une page spéciale pour afficher l'historique des emails
        return redirect(reverse('admin_detaille_email', args=[email.reponse_email_id])) # -	ça marche très bien
    
    
    if 'btn_voire_eleve' in request.POST: # bouton ajout élève activé
        return redirect('modifier_mes_eleve', mon_eleve_id=email_id) # Rediriger vers autre page

    return render(request, 'pages/admin_detaille_email.html', context) # Revenir à la même page, le context est nécessaire pout le template

# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_reponse_email(request, email_id): 
    email = Email_telecharge.objects.filter(id=email_id).first() # envoyé par le client
    user = request.user # admin
    text_email = f"""
        Suite à votre email :
        Date de réception : {email.date_telechargement.strftime('%d/%m/%Y')}
        Sujet de l'email : {email.sujet}
        Contenu de l'email :
        {email.text_email}
        ---------------------------
        En réponse à votre email, je vous adresse ce qui suit.
        De la part de: {user.first_name} {user.last_name}
        """
    sujet = "Suite à votre email"
    email_user = user.email
    context={'text_email': text_email, 'sujet': sujet, 'email_user': email_user}
    if 'btn_enr' in request.POST:
        
        text_email = request.POST.get('text_email', '').strip()
        sujet = request.POST.get('sujet', '').strip()
        email_user = request.POST.get('email_adresse', '').strip() # la priorité est à l'email reçu du POST
        if not email_user: # si l'email du POST est null ou vide
            email_user = user.email 

        # Validation de l'email_prof
        email_validator = EmailValidator() #inicialisation de l'objet EmailValidator
        try:
            email_validator(email_user)
        except ValidationError:
            messages.error(request, "L'adresse email du professeur est invalide.")
            context={'text_email': text_email, 'sujet': sujet, 'email_prof': email_user}
            return render(request, 'accounts/reponse_email.html', context) # revenir à la même page

        sujet = request.POST.get('sujet', '').strip() 
        if not sujet:  
            sujet = "Suite à votre email"
        
        text_email =  request.POST['text_email']
        user_destinataire = email.user.id
        email_destinataire = email.email_telecharge
        destinations = ['prosib25@gmail.com', email_destinataire]  

        # Validation des emails dans destinations
        for destination in destinations:
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                # même s'il y a erreur l'enregistrement continu car l'envoi de l'email n'est pas obligatoire

        try:
            send_mail(
                sujet,
                text_email,
                email_user,
                destinations,
                fail_silently=False,
            )
            messages.success(request, "La réponse à l'email a été envoyée avec succès.")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
        
        # enregistrement de l'email
        email_telecharge = Email_telecharge(
            user=user, 
            email_telecharge=email_user, 
            text_email=text_email, 
            user_destinataire=user_destinataire, 
            sujet=sujet
        )
        email_telecharge.save()
        # mise à jour de l'enregistrement de l'email envoyé par l'élève
        email_reponse_id = email_telecharge.id  
        email.suivi = 'Répondu'
        email.date_suivi = timezone.now()
        email.reponse_email_id = email_reponse_id
        email.save()  
        messages.success(request, "Email enregistré")
        return redirect('admin_liste_email_recu') # Rediriger vers autre page
    
    return render(request, 'pages/admin_reponse_email.html', context) # revenir sur la même page



# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_payment_en_attente_reglement(request):
    """
    Vue permettant d'afficher les paiements en attente de règlement par les professeurs.

    Fonctionnalités :
    - Filtrer les paiements selon une période donnée (dates de début et de fin).
    - Appliquer des filtres selon le statut du paiement (en attente, approuvé, annulé, etc.).
    - Associer chaque paiement à son professeur et à un éventuel accord de règlement.
    """

    # Format utilisé pour l'affichage et la conversion des dates
    date_format = "%d/%m/%Y"
    status_str=""

    # Récupération des dates minimales et maximales depuis la base de données
    dates = Payment.objects.filter(
        model='Demande_paiement',
        model_id__isnull=False,
        accord_reglement_id__isnull=True
    ).aggregate(min_date=Min('date_creation'), max_date=Max('date_creation'))

    # Définition des valeurs par défaut
    date_min = dates['min_date'] or (timezone.now().date() - timedelta(days=15))
    date_max = dates['max_date'] or timezone.now().date()

    # Récupération des valeurs envoyées par le formulaire POST avec fallback aux valeurs par défaut
    date_debut_str = request.POST.get('date_debut', date_min.strftime(date_format))
    date_fin_str = request.POST.get('date_fin', date_max.strftime(date_format))

    # Initialisation des variables date_debut et date_fin
    date_debut, date_fin = None, None

    try:
        # Conversion des dates en objets de type date
        date_debut = datetime.strptime(date_debut_str, date_format).date()
        date_fin = datetime.strptime(date_fin_str, date_format).date()

        # Vérification de la cohérence des dates
        if date_debut > date_fin:
            raise ValueError("La date de début doit être inférieure ou égale à la date de fin.")
    
    except ValueError as e:
        # Gestion des erreurs en cas de format de date invalide
        messages.error(request, f"Erreur de date : {e}")
        return render(request, 'pages/admin_payment_en_attente_reglement.html', {
            'paiements': [], 
            'professeurs': [], 
            'date_debut': date_debut, 
            'date_fin': date_fin
        })

    # Définition des critères de filtrage des paiements
    filters = {
        'model': 'Demande_paiement',  # Filtrer uniquement les paiements liés aux demandes de paiement
        'reglement_realise': False,  # Seuls les paiements en attente de règlement
        'date_creation__range': (date_debut, date_fin + timedelta(days=1))  # Filtre sur la période sélectionnée
    }

    # Correspondance des boutons de filtrage aux statuts de paiement
    status_filter = {
        'btn_en_ettente': 'En attente',   # Paiements en attente
        'btn_approuve': 'Approuvé',    # Paiements approuvés
        'btn_invalide': 'Invalide',     # Paiements invalidés
        'btn_annule': 'Annulé',      # Paiements annulés
    }

    # Application du filtre de statut en fonction du bouton cliqué
    for btn, status in status_filter.items():
        if btn in request.POST:
            filters['status'] = status
            status_str=status
            break

    # Filtrage des paiements contestés (réclamation)
    if 'btn_reclame' in request.POST:
        filters['approved'] = False  # Paiements contestés par l'élève
        status_str="Réclamé"

    # Récupération des paiements en fonction des filtres
    payments = Payment.objects.filter(**filters).order_by('-date_creation')

    # Initialisation des listes pour stocker les résultats
    paiements, professeurs = [], set()

    # Parcours des paiements récupérés pour associer les informations nécessaires
    for payment in payments:
        # Récupération de la demande de paiement associée
        demande_paiement = Demande_paiement.objects.filter(id=payment.model_id).first()
        if not demande_paiement: continue  # Ignorer les paiements sans demande associée

        professeur = demande_paiement.user  # Récupération du professeur lié au paiement
        accord_reglement = None

        # Vérification et récupération de l'accord de règlement associé
        if payment.accord_reglement_id:
            accord_reglement = AccordReglement.objects.filter(id=payment.accord_reglement_id).first()

        # Ajout des informations collectées à la liste des paiements
        paiements.append((payment, professeur, accord_reglement))
        professeurs.add(professeur)  # Utilisation d'un set() pour éviter les doublons

    # Préparation du contexte pour l'affichage dans le template
    context = {
        'paiements': paiements,
        'professeurs': list(professeurs),
        'date_debut': date_debut,
        'date_fin': date_fin,
        'status_str': status_str,
    }

    # Affichage de la page avec les paiements en attente de règlement
    return render(request, 'pages/admin_payment_en_attente_reglement.html', context)


# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_payment_accord_reglement(request, prof_id):
    """
    Vue permettant d'afficher et de gérer les paiements en attente d'accord de règlement 
    pour un professeur donné.

    Fonctionnalités :
    - Récupérer les paiements non encore régularisés (Statut != "Réalisé").
    - Permettre à l'administrateur de sélectionner les paiements à inclure dans un accord de règlement.
    - Assurer la validation de la date d’échéance avant d’ajouter les paiements à l’accord.
    """

    # Format de la date utilisé pour la conversion des dates saisies
    date_format = "%d/%m/%Y"

    # Récupération du professeur concerné
    professeur = get_object_or_404(Professeur, user_id=prof_id)

    # Récupération des demandes de paiement non réglées pour le professeur sélectionné
    demande_paiement_ids = Demande_paiement.objects.filter(
        user_id=prof_id, reglement_realise=False
    ).values_list('id', flat=True)

    # Récupération des paiements non encore accordés et non réalisés
    payments = Payment.objects.filter(
        accord_reglement_id=None,  # Aucun accord de règlement associé
        reglement_realise=False,  # Paiements non encore réglés
        model='Demande_paiement',
        model_id__in=demande_paiement_ids  # Filtrer uniquement les paiements du professeur sélectionné
    ).annotate(
        date_plus_15=F('date_creation') + timedelta(days=15)  # Champ calculé pour définir l'échéance par défaut
    ).order_by('-date_creation')

    # Contexte pour l'affichage des paiements
    context = {
        'professeur': professeur,
        'payments': payments,
    }

    # Vérification si le formulaire a été soumis pour accorder un règlement
    if 'btn_accord_reglement' in request.POST:
        # Récupération des paiements cochés dans le formulaire
        payment_keys = [key for key in request.POST.keys() if key.startswith('accord_')]

        # Vérification si au moins un paiement a été sélectionné
        if not payment_keys:
            messages.error(request, "Veuillez sélectionner au moins un paiement.")
            return render(request, 'pages/admin_payment_accord_reglement.html', context)

        payment_requests = []

        # Parcours des paiements sélectionnés pour récupérer leurs informations
        for payment_key in payment_keys:
            payment_id = payment_key.split('_')[1]  # Extraction de l'ID du paiement
            date_reglement_str = request.POST.get(f'date_echeance_{payment_id}')  # Date d’échéance

            # Vérification que la date d’échéance est renseignée
            if not date_reglement_str:
                continue

            # Récupération de l'objet Payment correspondant
            payment = payments.filter(id=payment_id).first()
            if payment:
                # Conversion de la date d'échéance en objet datetime
                date_reglement = datetime.strptime(date_reglement_str, date_format).date()

                # Vérification que la date de règlement est au moins 7 jours après la date de création du paiement
                if (payment.date_creation.date() + timedelta(days=7)) > date_reglement:
                    messages.info(
                        request,
                        f"La date de règlement ({date_reglement}) doit être au moins 7 jours après "
                        f"la date de création du paiement ({payment.date_creation.date()}).<br>"
                        "Ce paiement est donc ignoré."
                    )
                    continue  # Ignorer ce paiement

                # Ajout du paiement et de sa date d’échéance à la liste
                payment_requests.append((date_reglement_str, payment.id))

        # Vérification que des paiements valides ont bien été sélectionnés
        if not payment_requests:
            messages.error(request, "Veuillez définir une date d'échéance valide pour au moins un paiement.")
            return render(request, 'pages/admin_payment_accord_reglement.html', context)

        # Stockage des paiements validés dans la session avant redirection
        request.session['payment_requests'] = payment_requests

        return redirect('admin_accord_reglement', prof_id=prof_id)

    return render(request, 'pages/admin_payment_accord_reglement.html', context)


@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_accord_reglement(request, prof_id):
    """
    Enregistre les accords de règlement (statut en attente), relatifs aux paiements sélectionnés, 
    en les groupant par date d'échéance, pour le professeur 
    séclectionné, envoie un email pour chaque accord et enregistre 
    les emails envoyées
    en fin la mise à jour des paiements sélectionnés (accord_reglement_id=accord_reglement_id)
    pour différencier les paiements sans accord de règlement (accord_reglement_id=None)
    """
    date_format = "%d/%m/%Y" # format de la date
    msg = "" # pour grouper les messages info dans un message final
    # Récupérer le professeur ou renvoyer une erreur 404 s'il n'existe pas
    professeur = get_object_or_404(Professeur, user_id=prof_id)
    # récupérer date_reglement_str,payment_id de la session
    payment_requests = request.session.get('payment_requests')
    if not payment_requests:
        messages.info(request, "Il n'y apas de règlement à enregistrer")
        return redirect('admin_payment_accord_reglement', prof_id=prof_id)
    date_requests=set() # pour grouper les dates
    totaux = [] # pour calculer date, totaux_payement, totaux_versement par date de groupement
    
    # la date_versement est la même que la date_request
    payments=[] # pour la liste des paiements des élèves: date_versement, payment, user_eleve
    textes = [] # textes des emails envoyés
    for date_reglement_str,payment_id in payment_requests: # étier les données de la session
        payment = Payment.objects.filter(id=payment_id).first()
        # c'est une requette qui lie la table Demande_paiement avec Eleve avec User
        demande_paiement = Demande_paiement.objects.select_related('eleve__user').filter(id=payment.model_id).first()
        if not demande_paiement: continue  # Ignorer les paiements sans demande associée ()
        user_eleve = demande_paiement.eleve.user

        try:
                date_versement = datetime.strptime(date_reglement_str, date_format).date()
                payments.append((date_versement, payment, user_eleve))
                date_request=date_versement # pour les différencier dans le templae
                date_requests.add(date_request) # groupement des date de règlement (versement)
                
        except ValueError:
            continue

    for date in date_requests: # groupement des dates de règlements
        totaux_payement=0
        for date_versement, payment, user_eleve in payments: # la date de versement est la même que date de règlement
            if date==date_versement: 
                totaux_payement += payment.amount
        totaux_versement = (totaux_payement * 2 ) / 3
        totaux.append((date, totaux_payement, totaux_versement))
        # à suivre 26/02/25
    if 'btn_accord_enregistrement' in request.POST:
        # envoyer l'email
        user = request.user # admin
        email_user = user.email
        email_destinataire = professeur.user.email
        destinations = ['prosib25@gmail.com', email_destinataire]
        
        # Validation des emails dans destinations
        for destination in destinations:
            email_validator = EmailValidator() #inicialisation de l'objet EmailValidator
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                # même s'il y a erreur l'enregistrement continu car l'envoi de l'email n'est pas obligatoire
        
        # mise en forme du text_email et du sujet de l'email
        for date_request in date_requests:
            texte = f"\nRèglement prévu le:\t\t{date_request.strftime('%d/%m/%Y')}\n\nListe des paiements des élèves:\nElève\t\t\t\t\tDate paiement\tPaiement\n"
            for date_versement, payment, user_eleve in payments:
                if date_versement==date_request:
                    texte += f"{user_eleve.first_name} {user_eleve.last_name}\t\t\t\t{payment.date_creation.strftime('%d/%m/%Y')}\t\t{payment.amount:.2f}€\n"
            
            texte_totaux =""
            for date, totaux_payement, totaux_versement in totaux:
                if date == date_request:
                    texte_totaux = f"\nMontant payé\t\tMontant à règler\n{totaux_payement:.2f}€\t\t\t\t\t{totaux_versement:.2f}€\nStatut accord de règlement: En attente"
                    texte_fin= texte + texte_totaux
                    sujet = f"Accord de règlement de: {totaux_payement:.2f}€, pour le: {date}"
                    textes.append((date,texte_fin ))
                
            #envoie de l'email
            text_email = texte_fin
            try:
                send_mail(
                    sujet,
                    text_email,
                    email_user,
                    destinations,
                    fail_silently=False,
                )
                msg += str(f"L'email a été envoyée avec succès relatif à l'accord de règlement du {date_request}.\n")
                # messages.success(request, "L'email a été envoyée avec succès.")
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
            
            # enregistrement de l'email
            email_telecharge = Email_telecharge(
                user=user, 
                email_telecharge=email_user, 
                text_email=text_email, 
                user_destinataire=professeur.user.id,
                sujet=sujet
            )
            email_telecharge.save()
            msg += str(f"L'email a été enregistré avec succès relatif à l'accord de règlement du {date_request}.\n")
            # messages.success(request, "L'email a été enregistré avec succès.")

            # Enregistrement des accords de règlements
            for date, totaux_payement, totaux_versement in totaux:
                if date == date_request:
                    accord_reglement = AccordReglement(admin_user=user, professeur=professeur, total_amount=totaux_versement, email_id=email_telecharge.id, status="En attente", due_date=date, )
                    accord_reglement.save()
                    
                    
                    # Enregistrement des détailles des accords de règlements
                    for date_versement, payment, user_eleve in payments:
                        if date_versement == date_request: # car les accords de règlements sont groupés par date de règlement
                            detaille_accord_reglement = DetailAccordReglement(
                                accord=accord_reglement, 
                                payment=payment, 
                                professor_share=(payment.amount * 2) / 3, 
                                description="Elève: " + user_eleve.first_name + " " + user_eleve.last_name +
                                            ", Date paiement: " + payment.date_creation.strftime('%d/%m/%Y') +
                                            ", Montant payé: " + str(payment.amount) + "€"
                            )
                            detaille_accord_reglement.save()
                            payment.accord_reglement_id=accord_reglement.id # mise à jour de l'enregistrement payment
                            payment.save()
                            # Mise à jour Demande_paiement (accord_reglement_id)
                            demande_paiements = Demande_paiement.objects.filter(payment_id=payment.id)
                            for demande_paiement in demande_paiements:
                                demande_paiement.accord_reglement_id=accord_reglement.id
                                demande_paiement.save()
                                msg += "\n Mise à jour Demande_paiement (accord_reglement_id)"

                            msg += str(f"L'accord de règlement a été enregistré avec succès du {date_versement}.\n\n")
        messages.success(request, msg.replace("\n", "<br>") )
        # vider payment_requests de la session
        request.session.pop('payment_requests', None)
        return redirect('admin_payment_accord_reglement', prof_id=prof_id)

    # Contexte à passer au template
    context = {
        'professeur': professeur,
        'payments': payments,
        'date_requests': date_requests,
        'totaux': totaux,
        'textes':textes,
    }

    # Rendu de la page avec les données filtrées
    return render(request, 'pages/admin_accord_reglement.html', context)


# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_reglement(request):
    """
    affiche les règlements effectués par l'administrateur 
    pour une période donnée, permet de passer à la mise à 
    jour des enregistrements sélectionnés et
    de visualiser les détaillesdes accord de règlements
    """
    
    teste = True # pour controler les validations
    date_format = "%d/%m/%Y" # Format date

    # Récupération des dates minimales et maximales depuis la base de données
    dates = AccordReglement.objects.filter(
        ~Q(status='Réalisé'),  # Exclure les enregistrements avec status='Réalisé'
        transfere_id__isnull=True,
        date_trensfere__isnull=True
    ).aggregate(
        min_date=Min('due_date'),
        max_date=Max('due_date')
    )

    # Définition des valeurs par défaut
    date_min = dates['min_date'] or (timezone.now().date() - timedelta(days=15))
    date_max = dates['max_date'] or timezone.now().date()

    # Récupération des valeurs envoyées par le formulaire POST avec fallback aux valeurs par défaut
    date_debut_str = request.POST.get('date_debut', date_min.strftime(date_format))
    date_fin_str = request.POST.get('date_fin', date_max.strftime(date_format))

    # # début et fin de période de tri [date_debut_str , date_fin_str]
    # date_fin_str = request.POST.get('date_fin', timezone.now().date().strftime(date_format))
    # date_debut_str = request.POST.get('date_debut', (timezone.now().date() - timedelta(days=15)).strftime(date_format))
    statut=""
    date_now = timezone.now().date()
    # Validation du format des dates
    try:
        date_debut = datetime.strptime(date_debut_str, date_format).date()
    except ValueError:
        messages.error(request, f"Format de la date de début de période invalide: {date_debut_str}. Utilisez jj/mm/aaaa.")
        teste = False
        date_debut = None

    try:
        date_fin = datetime.strptime(date_fin_str, date_format).date()
    except ValueError:
        messages.error(request, f"Format de la date de fin de période invalide: {date_fin_str}. Utilisez jj/mm/aaaa.")
        teste = False
        date_fin = None

    # Vérification que la date de début est bien avant la date de fin
    if teste:
        if date_debut > date_fin:
            messages.error(request, "La date de début doit être inférieure ou égale à la date de fin de période.")
            teste = False

    # Fonction interne pour récupérer les paiements en attente de règlement
    def get_reglements(date_debut, date_fin, filter_criteria=None):
        if filter_criteria is None:
            filter_criteria = {}

        return AccordReglement.objects.filter(
            due_date__range=(date_debut , date_fin + timedelta(days=1)),
            **filter_criteria
        ).order_by('due_date') # [date_debut , date_fin]

    # Récupérer tous les accords de reglements
    accord_reglements = get_reglements(date_debut, date_fin)

    # Vérification du type de requête et application des filtres en fonction du bouton cliqué
    
    if 'btn_tous' in request.POST:
        # Filtrer pour tous les emails
        accord_reglements = get_reglements(date_debut, date_fin)
    elif 'btn_en_ettente' in request.POST:
        # Filtrer pour les paiements en attente
        accord_reglements = get_reglements(date_debut, date_fin, {'status': 'En attente'})
        statut = "En attente"
    elif 'btn_en_cours' in request.POST:
        # Filtrer pour les paiements approuvés
        accord_reglements = get_reglements(date_debut, date_fin, {'status': 'En cours'})
        statut = "En cours"
    elif 'btn_invalide' in request.POST:
        # Filtrer pour les paiements invalides
        accord_reglements = get_reglements(date_debut, date_fin, {'status': 'Invalide'})
        statut = "Invalide"
    elif 'btn_annule' in request.POST:
        # Filtrer pour les paiements annulés
        accord_reglements = get_reglements(date_debut, date_fin, {'status': 'Annulé'})
        statut = "Annulé"
    elif 'btn_realiser' in request.POST:
        # Filtrer pour les paiements réclamés par les élèves
        accord_reglements = get_reglements(date_debut, date_fin, {'status': 'Réalisé'})
        statut = "Réalisé"

    accord_reglement_approveds = []
    for accord_reglement in accord_reglements:
        payments = Payment.objects.filter(id__in=DetailAccordReglement.objects.filter(accord=accord_reglement).values_list('payment_id', flat=True))
        # si un des paiement est non approuvé par l'élève alors approved = False
        approved =True
        for payment in payments:
            if not payment.approved: 
                approved = False
                break
        accord_reglement_approveds.append((accord_reglement , approved))

    
    context = {
        'accord_reglement_approveds': accord_reglement_approveds,
        'date_fin':date_fin,
        'date_debut':date_debut,
        'statut': statut,
        'date_now':date_now
    }

    if 'btn_enr' in request.POST:
        # Récupérer les règlements cochés
        reglement_keys = [key for key in request.POST.keys() if key.startswith('checkbox_reglement_id')]
        # Pour sélectionner un enregistrement il faut le cocher et définir la date du règlement et modifier le statut et autres conditions (voire suite)
        if not reglement_keys: # pas de règlement sélectionné
            messages.error(request, "Il faut au moins cocher un règlement")
            return render(request, 'pages/admin_reglement.html', context)

        reglement_requests = []
        # récupérter les données des paiements sélectionnés
        for reglement_keys in reglement_keys:
            i = int(reglement_keys.split('checkbox_reglement_id')[1]) # récupérer ID du règlement
            date_operation_reglement_str = request.POST.get(f'date_operation_reglement_id{i}') # récupérer la date de l'opération de règlement
            if not date_operation_reglement_str:
                continue # si la date est null tout l'enregistrement est ignorée
            # Validation du format des dates
            try:
                date_operation_reglement = datetime.strptime(date_operation_reglement_str, date_format).date()
            except ValueError:
                continue # si le format de la date est incorrecte tout l'enregistrement est ignorée
            
            # voire dans le template les conditions logiques 
            # entre accord_reglement.status et la valeur du  nouv_status_accord

            nouv_status_accord = request.POST.get(f'nouv_status_accord_id{i}') # récupérer le nouv_status de l'opération de règlement
            
            if nouv_status_accord == 'Non défini':
                continue # si nouv_status_accord == 'Non défini' tout l'enregistrement est ignorée
            
            # Récupérer l'objet accord_reglement correspondant si la date est définie 
            accord_reglement = accord_reglements.filter(id=i).first()
            
            # Récupérer les paiements liés à l'accord de règlement
            payments = Payment.objects.filter(id__in=DetailAccordReglement.objects.filter(accord=accord_reglement).values_list('payment_id', flat=True))
            # si un des paiement est non approuvé par l'élève alors approved = False
            approved =True
            for payment in payments:
                if not payment.approved: 
                    approved = False
                    break
            reglement_requests.append((accord_reglement.id, approved, date_operation_reglement_str, nouv_status_accord ))
        # si aucune reglement_requests n'est récupéré
        if not reglement_requests:
            messages.error(request, "Pas d'enregistrement à modifier")
            return render(request, 'pages/admin_reglement.html', context)
        
        request.session['reglement_requests']= reglement_requests
        return redirect('admin_reglement_email')

    # Rendu de la page avec les emails filtrés
    return render(request, 'pages/admin_reglement.html', context)

# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_reglement_email(request):
    date_format = "%d/%m/%Y" # Format date
    reglement_requests = request.session.get('reglement_requests')
    
    accord_reglement_modifs=[]
    for id, approved, date_operation_reglement_str, nouv_status_accord in reglement_requests:
        accord_reglement = AccordReglement.objects.get(id=id)
        date_operation_reglement = datetime.strptime(date_operation_reglement_str, date_format).date()
        
        # mise en forme du text_email et du sujet de l'email
        sujet = f"Votre accord de règlement pour le: {accord_reglement.due_date.strftime('%d/%m/%Y')} d'un montant de: {accord_reglement.total_amount:.2f}€ est "
        if nouv_status_accord=="En cours": 
            sujet +="en cours"
            text_email = f"Un transfère bancaire le {date_operation_reglement.strftime('%d/%m/%Y')} d'un montant de {accord_reglement.total_amount:.2f}€ , conformément à votre accord de règlement pour l'échéance du {accord_reglement.due_date.strftime('%d/%m/%Y')} , dans l'attente de la confirmation de la banque. Nous restons à votre disposition pour toute information complémentaire et vous remercions de votre confiance."
        elif nouv_status_accord=="Réalisé": 
            sujet +="réalisé"
            text_email = f"Une transaction d'un montant de {accord_reglement.total_amount:.2f}€ a été créditée sur votre compte, conformément à votre accord de règlement pour l'échéance du {accord_reglement.due_date.strftime('%d/%m/%Y')}. Nous restons à votre disposition pour toute information complémentaire et vous remercions de votre confiance."
        elif nouv_status_accord=="Annulé": 
            sujet +="annulé"
            text_email = f"Nous regrettons de vous informer que votre accord de règlement pour le {accord_reglement.due_date.strftime('%d/%m/%Y')}, d'un montant de {accord_reglement.total_amount:.2f}€, a été annulé. \n(Pour plus de détaille voire texte explicatif).\n Nous vous prions de nous excuser pour ce désagrément et restons à votre disposition pour toute information complémentaire. Nous vous remercions de votre compréhension et de votre confiance."
        elif nouv_status_accord=="Invalide": 
            sujet +="non validé"
            text_email = f"Nous regrettons de vous informer que votre accord de règlement pour le {accord_reglement.due_date.strftime('%d/%m/%Y')}, d'un montant de {accord_reglement.total_amount:.2f}€, n'a pas été validé en raison d'un incident survenu lors de l'initiation de la transaction bancaire.  \n(Pour plus de détaille voire texte explicatif).\n Nous vous prions de nous excuser pour ce désagrément et restons à votre disposition pour toute information complémentaire. Nous vous remercions de votre compréhension et de votre confiance."


        accord_reglement_modifs.append((accord_reglement, date_operation_reglement, nouv_status_accord, approved, text_email, sujet ))

    context={
        'accord_reglement_modifs':accord_reglement_modifs,
    }
    teste = False
    if "btn_accord_enregistrement" in request.POST:
        for accord_reglement, date_operation_reglement, nouv_status_accord, approved, text_email, sujet in accord_reglement_modifs:
            # Récupérer les accords de règlement
            reglement_keys = [key for key in request.POST.keys() if key.startswith('sujet_')]
            if not reglement_keys: # pas de règlement sélectionné (teste non nécessaire)
                messages.error(request, "Il y a pas d'accord de règlement à modifier")
                return redirect('admin_reglement')
            reglement_requests = []
            # récupérter les données des accords de règlement
            k = len(reglement_keys) # pour tester si tous les enregistrement des accords de règlement, sélectionnés, ont été modifier
            l=0 # pour ,tester s'il y a eu des changement dans les enregistrement des accords de règlement
            for reglement_key in reglement_keys:
                i = int(reglement_key.split('sujet_')[1]) # récupérer ID de l'accord de règlement
                if accord_reglement.id !=i : continue # Pour ne prondre en considération que i=accord_reglement.id( Très important)
                if accord_reglement.status==nouv_status_accord: continue # ignorer s'il n'y a pas de changement de statut
                # messages.info(request, f'ancien statut: {accord_reglement.status}; nouveau statut: {nouv_status_accord}')
                l +=1
                text_plus_email = request.POST.get(f'text_plus_email_{i}', "") # récupérer le texte d'explication en plus s'il existe, si non ""
                email_user = accord_reglement.admin_user.email
                email_prof = accord_reglement.professeur.user.email
                sujet = sujet
                text_email = text_email + "\n" + text_plus_email
                teste = True

                # Valider l'adresse e-mail du email_user
                try:
                    validate_email(email_user)
                except ValidationError:
                    teste=False
                    messages.error(request, f"L'adresse e-mail du user n'est pas valide. emailm {email_user} ")

                destinations = ['prosib25@gmail.com', email_prof]
                # Validation des emails dans destinations
                for destination in destinations:
                    email_validator = EmailValidator()
                    try:
                        email_validator(destination)
                    except ValidationError:
                        teste=False
                        messages.error(request, f"L'adresse email du prof est invalide. Email: {destination}")
                        
                if teste:
                    try:
                        # Envoie l'email à tous les destinataires
                        send_mail(sujet, text_email, email_user, destinations, fail_silently=False)
                        # Message de succès si l'email a été envoyé
                        messages.success(request, "L'email a été envoyé avec succès.")
                    except Exception as e:
                        # Message d'erreur si l'envoi échoue
                        messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")
                
                    # Enregistre l'email dans la base de données
                    email_telecharge = Email_telecharge(
                        user=request.user,
                        email_telecharge=request.user.email,
                        sujet=sujet,
                        text_email=text_email,
                        user_destinataire=accord_reglement.professeur.user.id,
                    )
                    email_telecharge.save()
                    messages.success(request, "Email enregistré")
                    if nouv_status_accord!="Réalisé":
                        # Mise à jour de l'accord de règlement
                        accord_reglement.email_id=email_telecharge.id
                        accord_reglement.status=nouv_status_accord
                        accord_reglement.save()
                        messages.success(request, "Mise à jour de l'accord de règlement")
            
                    else:
                        # récupérer date de l'opération et ID de l'opération
                        date_operation_str = request.POST.get(f'date_operation_{i}', "")
                        date_operation = datetime.strptime(date_operation_str, '%d/%m/%Y').date()
                        operation_id = request.POST.get(f'operation_{i}', "")

                        # Mise à jour de l'accord de règlement
                        accord_reglement.email_id=email_telecharge.id
                        accord_reglement.status=nouv_status_accord
                        accord_reglement.transfere_id = operation_id
                        accord_reglement.date_trensfere = date_operation # Il faut que la date soit > à 7 jour de la date max des paiements liés à laccord
                        accord_reglement.save()
                        messages.success(request, "Mise à jour de l'accord de règlement avec un statut: réalisé")

                        # Mise à jour Demande_paiement ( un accord de règlement peut contenir plusieur demande de paiement)
                        demande_paiements = Demande_paiement.objects.filter(accord_reglement_id=accord_reglement.id)
                        for demande_paiement in demande_paiements:
                            demande_paiement.reglement_realise = True
                            demande_paiement.save()
                        messages.success(request, "Mise à jour Demande_paiement")

                        # Mise à jour Payment (à réviser)
                        # Récupérer tous les détails des accords de règlement liés à l'accord donné
                        detail_accord_reglements = DetailAccordReglement.objects.select_related('payment').filter(accord=accord_reglement)

                        # Récupérer tous les IDs des paiements associés
                        payment_ids = detail_accord_reglements.values_list('payment_id', flat=True)

                        # Mettre à jour en une seule requête les paiements concernés
                        Payment.objects.filter(id__in=payment_ids).update(accord_reglement_id=accord_reglement.id, reglement_realise=1)
                        messages.success(request, "Mise à jour payment")
                        # Supprimer reglement_requests de la session après l'enregistrement
                        del request.session['reglement_requests'] # à réviser
                        request.session.modified = True  # Force la mise à jour de la session, à réviser avec Salma
            if l==0: 
                messages.info(request, "Aucun changement dans les enregistrements des accords de règlement")
                teste=False
            if l<k: messages.info(request, f"Il y a {k-l} enregistrement(s) ignoré(s).")
        if teste: return redirect('admin_reglement')

    return render(request, 'pages/admin_reglement_email.html', context)