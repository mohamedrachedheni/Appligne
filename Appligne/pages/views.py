
from accounts.models import Prof_zone, Departement, Matiere, Niveau, Region
from accounts.models import  Email_telecharge, Prix_heure, Prof_mat_niv, Historique_prof
from eleves.models import Temoignage
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import OuterRef, Subquery, DecimalField
from django.core.validators import  EmailValidator
from django.core.exceptions import  ValidationError
from django.core.paginator import Paginator
from django.core.mail import send_mail

# Create your views here.



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
        
    if request.method == 'POST' and 'btn_rechercher' in request.POST: # bouton recherche activé
        # annuler les données précédentes dans la session
        # Supprimer les données spécifiques de la session
        if 'radio_name' in request.session:
            del request.session['radio_name']
        if 'radio_name_text' in request.session:
            del request.session['radio_name_text']
        if 'matiere_defaut' in request.session:
            del request.session['matiere_defaut']
        if 'niveau_defaut' in request.session:
            del request.session['niveau_defaut']
        if 'region_defaut' in request.session:
            del request.session['region_defaut']
        if 'departement_defaut' in request.session:
            del request.session['departement_defaut']
        # mettre à jour les données de la session pour une nouvelle recherche    
        if request.POST.get('a_domicile', None):
            request.session['radio_name'] = "a_domicile"
            request.session['radio_name_text'] = "Cours à domicile" # pour le filtre de Prix_heure
        if request.POST.get('webcam', None):
            request.session['radio_name'] = "webcam"
            request.session['radio_name_text'] = "Cours par webcam"
        if request.POST.get('stage', None):
            request.session['radio_name'] = "stage"
            request.session['radio_name_text'] = "Stage pendant les vacances"
        if request.POST.get('stage_webcam', None):
            request.session['radio_name'] = "stage_webcam"
            request.session['radio_name_text'] = "Stage par webcam"

        # Stocker les filtres dans la session pour persistance
        request.session['matiere_defaut'] = request.POST['matiere']
        request.session['niveau_defaut'] = request.POST['niveau']
        request.session['region_defaut'] = request.POST['region']
        request.session['departement_defaut'] = request.POST['departement']
        return redirect('liste_prof')

    return render(request, 'pages/index.html', context)

def liste_prof(request):
     # Récupérer ou définir les valeurs par défaut des filtres de recherche à partir de POST ou de la session
    # donner la priorité au request puis à la session puis à la valeur par défaut
    radio_name = request.POST.get('radio_name', request.session.get('radio_name', "a_domicile"))
    radio_name_text = request.POST.get('radio_name_text', request.session.get('radio_name_text', "Cours à domicile"))
    matiere_defaut = request.POST.get('matiere', request.session.get('matiere_defaut', "Maths"))
    niveau_defaut = request.POST.get('niveau', request.session.get('niveau_defaut', "Terminale Générale"))
    region_defaut = request.POST.get('region', request.session.get('region_defaut', "ILE-DE-FRANCE"))
    departement_defaut = request.POST.get('departement', request.session.get('departement_defaut', "PARIS"))
    tri = 'evaluation_decroissante'

    # Récupérer les filtres possibles pour les matières, niveaux, régions et départements
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)

    if 'region' in request.POST and not 'btn_rechercher' in request.POST: # si la page et actiée par input name='region' seulement sans recherche
        departement_defaut = Departement.objects.filter(region__region=region_defaut).first() # le premier de la liste des départements pour le champ input*
    messages.info(request, f"departement_defaut = {departement_defaut} ") # jusque là c'est bien
    

    # Gérer les formats de cours sélectionnés dans le cas request.POST avec ou sans recherche
    # ces testes sont obligatoire si non erreur de résultat, c'est la valeur session qui passe
    if request.POST.get('a_domicile'):
        radio_name = "a_domicile"
        radio_name_text = "Cours à domicile"
    elif request.POST.get('webcam'):
        radio_name = "webcam"
        radio_name_text = "Cours par webcam"
    elif request.POST.get('stage'):
        radio_name = "stage"
        radio_name_text = "Stage pendant les vacances"
    elif request.POST.get('stage_webcam'): # si on utilise else dans le dernier cas le résultat est faux, c'est la valeut "stage_webcam" qui passe dans le cas not request.POST
        radio_name = "stage_webcam"
        radio_name_text = "Stage par webcam"

    # Sous-requête pour récupérer le prix par heure en fonction des filtres
    prix_heure_subquery = Prix_heure.objects.filter(
        user=OuterRef('pk'),
        prof_mat_niv__matiere__matiere=matiere_defaut,
        prof_mat_niv__niveau__niveau=niveau_defaut,
        format=radio_name_text
    ).values('prix_heure')

    ordre_tri = '-historique_prof__moyenne_point_cumule' if tri == 'evaluation_decroissante' else '-annotated_prix_heure'
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
    user = get_object_or_404(User, id=id_user)

   # Récupérer les témoignages
    temoignages = Temoignage.objects.filter(user_prof=user).distinct()

    # Pagination : diviser la liste des professeurs par pages de 4 éléments
    elements_par_page = 2
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
    elements_par_page_prof = 4
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
    # Sélectionnez le premier utilisateur qui est superuser, staff et actif
    # par defaux pour eviter erreur de la base de donnée user-id can not be null
    # car le visiteur n'a pas de compt user
    # user = User.objects.filter(is_superuser=True, is_staff=True, is_active=True).first()
    if request.method == 'POST' and 'btn_enr' in request.POST:
        email = request.POST.get('email_user')
        text_email = request.POST.get('text_email')
        if text_email:
            # messages.error(request, "Teste 01 ")
            if not email:
                messages.error(request, "Vous devez indiquer votre email ")
                return render(request, 'pages/nous_contacter.html')
            # Sélectionner le premier enregistrement des superusers qui est dans ce cas le destinataire de l'Email
            user_destinataire = User.objects.filter(is_staff=1, is_active=1, is_superuser=1).first()
            user_destinataire_id = user_destinataire.id
            
            # traitement de l'envoie de l'email
            # Validation de l'email_prof
            email_validator = EmailValidator()
            try:
                email_validator(email)
            except ValidationError:
                messages.error(request, "L'adresse email est invalide.")
                return render(request, 'pages/nous_contacter.html')
            
            # si le sujet de l'email n'est pas défini dans le GET alors sujet='Sujet non défini'
            sujet = request.POST.get('sujet', 'Sujet non défini').strip()  # Obtient la valeur de 'sujet' ou une chaîne vide
            # on peut ajouter d'autres destinations: destinations = ['prosib25@gmail.com', 'autre_adresse_email']
            destinations = ['prosib25@gmail.com']
            # Validation des emails dans destinations
            for destination in destinations:
                try:
                    email_validator(destination)
                except ValidationError:
                    messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                    return render(request, 'pages/nous_contacter.html')
            try:
                send_mail(
                    sujet,
                    text_email,
                    email,
                    destinations,
                    fail_silently=False,
                )
                # ajouter un teste pour voir si tous les enregistrement relatifs au professeur sous achevés
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email: {str(e)}")
            
            messages.success(request, "L'email a été envoyé avec succès. ")
            email_telecharge = Email_telecharge( email_telecharge=email, text_email=text_email, user_destinataire=user_destinataire_id, sujet=sujet)
            email_telecharge.save()
            messages.success(request, "Email enregistré")
    return render(request, 'pages/nous_contacter.html')
