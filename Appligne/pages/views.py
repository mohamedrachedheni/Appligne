
from accounts.models import Prof_zone, Departement, Matiere, Niveau, Region, Professeur, Format_cour, Pro_fichier, Diplome_cathegorie
from accounts.models import Diplome, Experience, Prof_doc_telecharge, Pays, Experience_cathegorie, Mes_eleves,Detail_demande_paiement, Horaire, Cours
from accounts.models import  Email_telecharge, Prix_heure, Prof_mat_niv, Historique_prof, Commune, Payment, Demande_paiement, DetailAccordReglement, AccordReglement, DetailAccordRemboursement, AccordRemboursement
from eleves.models import Temoignage, Parent, Eleve
from .models import Reclamation, ReclamationCategorie, PieceJointeReclamation, MessageReclamation
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
from .forms import PieceJointeReclamationForm # c'est un fichier que j'ai créé à l'aide de GPT pour éxécuter les validation du model PieceJointeReclamation
from collections import defaultdict
from .utils import decrypt_id, encrypt_id
import logging
# Configuration du logger avec le nom du module actuel
logger = logging.getLogger(__name__)

# Enregistrement des logs
    # logger.debug("Page visitée")
    # logger.info("Action utilisateur")
    # logger.warning("Attention à un truc")
    # logger.error("Une erreur est survenue") 

from .models import FAQ 


# Create your views here.

# créer une méthode utilitaire :
def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


def index(request):
    # Paramètres de recherche par défaut
    radio_name = "a_domicile"
    matiere_defaut = "Maths"
    niveau_defaut = "Terminale Générale"
    region_defaut = "ILE-DE-FRANCE"
    departement_defaut = "PARIS"

    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)

    # Témoignages triés
    temoignage_tris = []
    eleve_temoignage = set()
    prof_temoignage = set()
    temoignages = Temoignage.objects.filter(evaluation_eleve__gte=4)
    for temoignage in temoignages:
        if temoignage.user_eleve not in eleve_temoignage and temoignage.user_prof not in prof_temoignage:
            eleve_temoignage.add(temoignage.user_eleve)
            prof_temoignage.add(temoignage.user_prof)
            temoignage_tris.append(temoignage)
            if len(temoignage_tris) > 3:
                break

    # --------- LOGIQUE DES FAQ ----------
    # Déterminer le rôle utilisateur
    if hasattr(request.user, 'eleve'):
        role = 'eleve'
    elif hasattr(request.user, 'professeur'):
        role = 'prof'
    elif request.user.is_staff:
        role = 'staff'
    else:
        role = 'visiteur'

    filtre_role = request.GET.get('role')
    if filtre_role is not None:
        role = filtre_role

    keyword = request.GET.get('keyword', '').strip()

    faqs = FAQ.objects.filter(actif=True)
    if role :
        faqs = faqs.filter(public_cible=role)
    if keyword:
        faqs = faqs.filter(
            Q(question__icontains=keyword) |
            Q(reponse__icontains=keyword)
        )

    paginator = Paginator(faqs.order_by('ordre'), 5)  # 5 FAQs par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render(request, 'pages/faq_items.html', {'page_obj': page_obj}).content.decode('utf-8')
        pagination_html = render(request, 'pages/faq_pagination.html', {'page_obj': page_obj}).content.decode('utf-8')
        return JsonResponse({'html': html, 'pagination': pagination_html})

    # --------- FIN LOGIQUE DES FAQ ----------

    # Si requête AJAX par formulaire (région)
    if 'region' in request.POST:
        matiere_defaut = request.POST['matiere']
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']

        if request.POST.get('a_domicile'):
            radio_name = "a_domicile"
        if request.POST.get('webcam'):
            radio_name = "webcam"
        if request.POST.get('stage'):
            radio_name = "stage"
        if request.POST.get('stage_webcam'):
            radio_name = "stage_webcam"

        departements = Departement.objects.filter(region__region=region_defaut)
        departement_defaut = departements.first()

    if request.method == 'POST' and 'btn_rechercher' in request.POST:
        for key in ['radio_name', 'radio_name_text', 'matiere_defaut', 'niveau_defaut', 'region_defaut', 'departement_defaut']:
            request.session.pop(key, None)

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

        request.session['matiere_defaut'] = request.POST.get('matiere', 'Non spécifié')
        request.session['niveau_defaut'] = request.POST.get('niveau', 'Non spécifié')
        request.session['region_defaut'] = request.POST.get('region', 'Non spécifié')
        request.session['departement_defaut'] = request.POST.get('departement', 'Non spécifié')
        return redirect('liste_prof')

    # Contexte général
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
        'page_obj': page_obj,  # Ajouté ici
    }

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
    # user = User.objects.filter( is_staff=True, is_active=True).first()
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
        user_destinataire = User.objects.filter( is_active=1, is_staff=1).first() # à gérer le cas de plusieur staff plus tard
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
    # Vérifier si l'utilisateur a un profil de staff associé
    if  not user.is_staff:
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
    user_id = request.user.id

    # Dictionnaire des boutons et critères associés
    filtre_suivi = {
        'btn_tous': {},
        'btn_nouveau': {'suivi__isnull': True},
        'btn_attente': {'suivi': 'Réception confirmée'},
        'btn_repondu': {'suivi': 'Répondu'},
        'btn_ignore': {'suivi': 'Mis à côté'},
    }

    # Fonction pour filtrer les emails + crypter les IDs
    def get_list_email(filter_criteria):
        emails = Email_telecharge.objects.filter(user_destinataire=user_id, **filter_criteria).order_by('-date_telechargement')
        return [(email, encrypt_id(email.id)) for email in emails]

    # Par défaut : tous les emails
    list_email = get_list_email({})

    if request.method == 'POST':
        # Cherche quel bouton de filtre est cliqué
        for btn, criteria in filtre_suivi.items():
            if btn in request.POST:
                list_email = get_list_email(criteria)
                break  # on sort dès qu'on trouve le bouton cliqué

        # Gestion des boutons de détails
        email_ids = [key.split('btn_detaille_email_')[1] for key in request.POST if key.startswith('btn_detaille_email_')]
        if email_ids:
            
            if len(email_ids) == 1:
                request.session['email_id'] = decrypt_id(email_ids[0])
                return redirect('admin_detaille_email')
            else:
                messages.error(request, "Erreur système, veuillez contacter le support technique.")
                return redirect('compte_administrateur')


    return render(request, 'pages/admin_liste_email_recu.html', {'list_email': list_email})


# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_detaille_email(request):
    user = request.user # admin
    email_id = request.session.get('email_id')
    email = Email_telecharge.objects.filter(id=email_id).first() # récupérer l'email

    email_id_cript = encrypt_id(email_id)
    context = {'email': email, 'email_id': email_id_cript}
    
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
        request.session['email_id'] = email.reponse_email_id
        return redirect('admin_detaille_email') # -	ça marche très bien
    
    
    if 'btn_voire_eleve' in request.POST: # bouton ajout élève activé
        return redirect('modifier_mes_eleve', mon_eleve_id=email_id) # Rediriger vers autre page
    # Gestion des boutons btn_repondre_email_
    email_ids = [key.split('btn_repondre_email_')[1] for key in request.POST if key.startswith('btn_repondre_email_')]
    if email_ids:
        
        if len(email_ids) == 1:
            request.session['email_id'] = decrypt_id(email_ids[0])
            return redirect('admin_reponse_email')
        else:
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')

    return render(request, 'pages/admin_detaille_email.html', context) # Revenir à la même page, le context est nécessaire pout le template

# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_reponse_email(request):
    email_id = request.session.get('email_id')
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
        model='demande_paiement',
        model_id__isnull=False, # ID de la demande de paiement liée au paiement
        accord_reglement_id__isnull=True # Il n'y a pas encore d'accord de règlement
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
        filters['reclamation__isnull'] = False  # Paiements contestés par l'élève
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

    # Extraction de l'ID du paiement choisi dans le formulaire
    paiement_ids = [key.split('btn_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_paiement_id')]
    # Vérification du nombre d'IDs extraits
    if paiement_ids:
        if len(paiement_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['payment_id'] = paiement_ids[0]
            return redirect('admin_payment_demande_paiement')
        elif len(paiement_ids) !=1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')

    # Extraction de l'ID du règlement choisi dans le formulaire
    accord_ids = [key.split('btn_detaille_reglement_id')[1] for key in request.POST.keys() if key.startswith('btn_detaille_reglement_id')]
    if accord_ids:
        # Vérification du nombre d'IDs extraits
        if len(accord_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['accord_id'] = int(accord_ids[0])
            return redirect('admin_reglement_detaille')

        elif len(accord_ids) != 1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')
    
    # Extraction de l'ID du professeur choisi dans le formulaire
    prof_ids = [key.split('btn_détaille_')[1] for key in request.POST.keys() if key.startswith('btn_détaille_')]
    if prof_ids:
        # Vérification du nombre d'IDs extraits
        if len(prof_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['prof_id'] = int(prof_ids[0])
            return redirect('admin_payment_accord_reglement')

        elif len(prof_ids) != 1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')

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
def admin_payment_accord_reglement(request):
    """
    Vue permettant d'afficher et de gérer les paiements en attente d'accord de règlement 
    pour un professeur donné.

    Fonctionnalités :
    - Récupérer les paiements non encore régularisés (Statut != "Réalisé").
    - Permettre à l'administrateur de sélectionner les paiements à inclure dans un accord de règlement.
    - Assurer la validation de la date d’échéance avant d'ajouter les paiements à l’accord.
    """
    # récupérer les paramètres de session
    prof_id = request.session.get('prof_id')

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
        model='demande_paiement',
        model_id__in=demande_paiement_ids  # Filtrer uniquement les paiements du professeur sélectionné
    ).annotate(
        date_plus_15=F('date_creation') + timedelta(days=15)  # Champ calculé pour définir l'échéance par défaut
    ).order_by('-date_creation')

    # Contexte pour l'affichage des paiements
    context = {
        'professeur': professeur,
        'payments': payments,
    }

    # Extraction de l'ID du paiement choisi dans le formulaire
    paiement_ids = [key.split('btn_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_paiement_id')]
    # Vérification du nombre d'IDs extraits
    if paiement_ids:
        if len(paiement_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['payment_id'] = paiement_ids[0]
            return redirect('admin_payment_demande_paiement')
        elif len(paiement_ids) !=1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')

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
                payment_requests.append((date_reglement_str, payment.id)) # à cripter les ID

        # Vérification que des paiements valides ont bien été sélectionnés
        if not payment_requests:
            messages.error(request, "Veuillez définir une date d'échéance valide pour au moins un paiement.")
            return render(request, 'pages/admin_payment_accord_reglement.html', context)

        # Stockage des paiements validés dans la session avant redirection
        request.session['payment_requests'] = payment_requests

        return redirect('admin_accord_reglement')

    return render(request, 'pages/admin_payment_accord_reglement.html', context)


@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_accord_reglement(request):
    """
    Enregistre les accords de règlement (statut en attente), relatifs aux paiements sélectionnés, 
    en les groupant par date d'échéance, pour le professeur 
    séclectionné, envoie un email pour chaque accord et enregistre 
    les emails envoyées
    en fin la mise à jour des paiements sélectionnés (accord_reglement_id=accord_reglement_id)
    pour différencier les paiements sans accord de règlement (accord_reglement_id=None)
    """

    # récupérer date_reglement_str,payment_id de la session
    payment_requests = request.session.get('payment_requests')
    prof_id = request.session.get('prof_id')

    date_format = "%d/%m/%Y" # format de la date
    msg = "" # pour grouper les messages info dans un message final
    # Récupérer le professeur ou renvoyer une erreur 404 s'il n'existe pas
    professeur = get_object_or_404(Professeur, user_id=prof_id)
    # # récupérer date_reglement_str,payment_id de la session
    # payment_requests = request.session.get('payment_requests')
    if not payment_requests:
        messages.info(request, "Il n'y apas de règlement à enregistrer")
        return redirect('admin_payment_accord_reglement')
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
        return redirect('admin_payment_accord_reglement')

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
            if payment.reclamation: 
                approved = False
                break
        accord_reglement_approveds.append((accord_reglement , approved))
    
    # Extraction de l'ID du règlement choisi dans le formulaire
    accord_ids = [key.split('btn_detaille_reglement_id')[1] for key in request.POST.keys() if key.startswith('btn_detaille_reglement_id')]
    if accord_ids:
        # Vérification du nombre d'IDs extraits
        if len(accord_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['accord_id'] = int(accord_ids[0])
            return redirect('admin_reglement_detaille')

        elif len(accord_ids) != 1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')




    
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
                if payment.reclamation: 
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
        # Condition nécessaire de l'activation du template
        if not reglement_requests:
            messages.info(request, "Il n'y a pas de règlement à enregistrer")
            return redirect('compte_administrateur')
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
                        request.session['reglement_requests']=None # à réviser
                        request.session.modified = True  # Force la mise à jour de la session, à réviser avec Salma
            if l==0: 
                messages.info(request, "Aucun nouvel accord de règlement n'a été sélectionné.")
                teste=False
            if l<k: messages.info(request, f"Il y a {k-l} enregistrement(s) ignoré(s).")
        if teste: return redirect('admin_reglement')

    return render(request, 'pages/admin_reglement_email.html', context)


# @user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_reglement_detaille(request):
    """
    Vue permettant d'afficher les détails d'un accord de règlement.

    - Seuls les utilisateurs staff et actifs peuvent accéder à cette page.
    - Récupère l'accord de règlement ainsi que ses détails associés.
    - Optimise les requêtes en utilisant `select_related` et `values_list`.
    """

    # Récupération sécurisée de l'accord de règlement ou renvoi d'une erreur 404
    accord_id = request.session.get('accord_id')
    
    # Condition nécessaire de l'activation du template
    if not accord_id:
        messages.info(request, "Il n'y a pas de règlement à enregistrer")
        return redirect('compte_administrateur')
    
    accord_reglement = get_object_or_404(AccordReglement, id=accord_id)
    
    # Récupération optimisée de l'email 
    email = Email_telecharge.objects.filter(id=accord_reglement.email_id).only('sujet', 'text_email').first()
    texte_email = f"Sujet: {email.sujet}\nContenu: {email.text_email}" if email else "Pas de message"
    
    # Récupération optimisée des détails de l'accord, avec accès direct aux attributs nécessaires
    detaille = list(
        DetailAccordReglement.objects
        .filter(accord=accord_reglement)
        .select_related('payment')  # Optimisation pour éviter des requêtes supplémentaires
        .values_list('payment__id', 'description', 'professor_share', 'payment__reclamation_id')
    )

    if 'btn_detaille_reglement' in request.POST:
        # Stockage l'ID de l'accord de règlement dans la session avant redirection
        request.session['accord_id'] = accord_id
        return redirect('admin_reglement_modifier')
    
    # Extraction de l'ID du paiement choisi dans le formulaire
    paiement_ids = [key.split('btn_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_paiement_id')]
    # Vérification du nombre d'IDs extraits
    if paiement_ids:
        if len(paiement_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            professeur = Professeur.objects.filter(user=request.user).first() # Si le user est un professeur
            if professeur:
                paiement = Payment.objects.filter(id=paiement_ids[0]).first() # il faut que le paiement est pour le professeur
                if paiement and not Demande_paiement.objects.filter(id=paiement.model_id, user=professeur.user).exists(): # Si non il y a eu une manipulation des données du template
                    messages.error(request, f"le paiement sélectionné n'est pas attrubuté au professeur, paiement_id= {paiement_ids[0]}")
                    return redirect('compte_prof')
                
            request.session['payment_id'] = paiement_ids[0]
            return redirect('admin_payment_demande_paiement')
        elif len(paiement_ids) !=1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')


    # Passage des données au template
    context = {
        'accord_reglement': accord_reglement,
        'texte_email': texte_email,
        'detaille': detaille,
    }
    
    return render(request, 'pages/admin_reglement_detaille.html', context)


def is_admin_active(user):
    """
    Vérifie si l'utilisateur est un administrateur actif.
    """
    return user.is_staff and user.is_active

# @user_passes_test(is_admin_active, login_url='/login/')
def admin_payment_demande_paiement(request):
    """
    Vue d'administration permettant d'afficher les détails du paiement d'un élève,
    liés à une demande de paiement faite par un professeur.
    Accessible uniquement aux administrateurs actifs.
    """

    # Récupération sécurisée de l'accord de règlement ou renvoi d'une erreur 404
    payment_id = request.session.get('payment_id')
    
    # Condition nécessaire de l'activation du template
    if not payment_id:
        messages.info(request, "Il n'y a pas de paiement")
        return redirect('compte_administrateur')
    
    # Récupération du paiement lié à une demande de paiement
    payment = get_object_or_404(Payment, id=payment_id, model="demande_paiement")
    
    # Récupération de la demande de paiement associée
    demande_paiement = get_object_or_404(Demande_paiement, id=payment.model_id)
    
    # Récupération des détails de la demande de paiement avec les cours et horaires associés
    details_paiement = Detail_demande_paiement.objects.select_related('cours', 'horaire').filter(demande_paiement=demande_paiement)
    
    # Récupération des e-mails associés en une seule requête
    email_ids = filter(None, [demande_paiement.email, demande_paiement.email_eleve])  # Filtrer les valeurs nulles
    emails = {email.id: email for email in Email_telecharge.objects.filter(id__in=email_ids)}
    
    # Construction des contenus d'e-mails
    def format_email(email_id):
        email = emails.get(email_id)
        return f"Sujet: {email.sujet}\nContenu: {email.text_email}" if email else "Pas de message"
    
    texte_email_prof = format_email(demande_paiement.email)
    texte_email_eleve = format_email(demande_paiement.email_eleve)
    
    # Extraction des horaires et des cours associés
    horaires = [(detail.cours, detail.horaire) for detail in details_paiement]
    
    # Récupération unique des cours
    cours_set = {detail.cours for detail in details_paiement}
    
    # Récupération des prix publics pour chaque cours
    cours_prix_publics = []
    for cours in cours_set:
        matiere_obj = Matiere.objects.filter(matiere=cours.matiere).first()
        niveau_obj = Niveau.objects.filter(niveau=cours.niveau).first()
        
        prof_mat_niv = Prof_mat_niv.objects.filter(
            user=demande_paiement.user, 
            matiere=matiere_obj, 
            niveau=niveau_obj
        ).first()
        
        prix_public = Prix_heure.objects.filter(user=demande_paiement.user, prof_mat_niv=prof_mat_niv).values_list('prix_heure', flat=True).first() if prof_mat_niv else None
        
        cours_prix_publics.append((cours, prix_public))
    
    # Passer à la création d'une nouvelle réclamation
    if 'btn_nouvelle_reclamation' in request.POST:
        request.session['reclamation_payment_id'] = payment_id
        return redirect('nouvelle_reclamation')
    
    # Voire lae détaille de la réclamation
    if 'btn_reclamation' in request.POST:
        if payment.reclamation.id:
            request.session['reclamation_id'] = payment.reclamation.id
            return redirect('reclamation')
        else: messages.error(request, "Il n'y a pas de réclamation liée au paiement")

    # Passage des données au template
    context = {
        'payment': payment,
        'demande_paiement': demande_paiement,
        'texte_email_prof': texte_email_prof,
        'texte_email_eleve': texte_email_eleve,
        'horaires': horaires,
        'cours_prix_publics': cours_prix_publics,
    }
    
    return render(request, 'pages/admin_payment_demande_paiement.html', context)


@user_passes_test(is_admin_active, login_url='/login/')
def admin_reglement_modifier(request):
    """
    Vue d'administration permettant d'afficher les détails du réglement d'un professeur,
    de modifier l'enregistrement.
    Accessible uniquement aux administrateurs actifs.
    """

    
    # Récupération sécurisée de l'accord de règlement ou renvoi d'une erreur 404
    accord_id = request.session.get('accord_id')

    # Condition nécessaire de l'activation du template
    if not accord_id:
        messages.info(request, "Il n'y a pas de règlement à enregistrer")
        return redirect('compte_administrateur')
    
    date_format = "%d/%m/%Y" # Format date
    # Récupération sécurisée de l'accord de règlement ou renvoi d'une erreur 404
    accord_reglement = get_object_or_404(AccordReglement, id=accord_id)
    
    # Récupération optimisée de l'email 
    email = Email_telecharge.objects.filter(id=accord_reglement.email_id).only('sujet', 'text_email').first()
    texte_email = f"Sujet: {email.sujet}\nContenu: {email.text_email}" if email else "Pas de message"
    
    # Récupération optimisée des détails de l'accord, avec accès direct aux attributs nécessaires
    detailles = list(
        DetailAccordReglement.objects
        .filter(accord=accord_reglement)
        .select_related('payment')  # Optimisation pour éviter des requêtes supplémentaires
        .values_list('payment__id', 'description', 'professor_share', 'payment__reclamation_id')
    )

    # sauvegarder les anciens paiement liés à l'accord de règlement
    ancien_payment_accords=[]
    # for detaille in detailles: # à corriger sans for:
    ancien_payment_accords = [detail[0] for detail in detailles] # Récupérer les ID des anciens payment

    # Récupérer les paiement réalisés et non affectés à des accords de règlement
    paiements_sans_accord=[]
    # Récupération du professeur concerné
    prof = AccordReglement.objects.filter(id=accord_id).first().professeur.user

    # Récupération des demandes de paiement non réglées pour le professeur sélectionné
    demande_paiements = Demande_paiement.objects.filter(
        user=prof, reglement_realise=False, payment_id__isnull=False # il faut que le paiement est realisé mais le règlement non
    )
    for demande_paiement in demande_paiements:
        # Récupération des paiements non encore accordés et non réalisés
        payment = Payment.objects.filter(
            accord_reglement_id=None,  # Aucun accord de règlement associé
            reglement_realise=False,  # Paiements non encore réglés
            model='demande_paiement',
            model_id=demande_paiement.id  # Filtrer uniquement les paiements du professeur sélectionné
        ).first()
        if not payment: continue
        description="Elève: " + demande_paiement.eleve.user.first_name + " " + demande_paiement.eleve.user.last_name + ", Date paiement: " + payment.date_creation.strftime('%d/%m/%Y') + ", Montant payé: " + str(payment.amount) + "€" if payment else ""
        professor_share=(payment.amount * 2) / 3 if payment else 0
        paiements_sans_accord.append((payment.id if payment else 0, description, professor_share, payment.reclamation if payment else ""))

    # Passage des données au template
    context = {
        'accord_reglement': accord_reglement,
        'texte_email': texte_email,
        'detailles': detailles,
        'paiements_sans_accord': paiements_sans_accord,
        'date_now':timezone.now().date(), # valeur par défaut pour date transfère
    }

    # Vérification si le formulaire a été soumis pour accorder un règlement
    if 'btn_enr' in request.POST:
        # Récupération des paiements cochés dans le formulaire
        payment_keys = [key for key in request.POST.keys() if key.startswith('accord_')]

        # Vérification si au moins un paiement a été sélectionné
        if not payment_keys:
            messages.error(request, "Veuillez sélectionner au moins un paiement.")
            # # Stockage l'ID de l'accord de règlement dans la session avant redirection
            # request.session['accord_id'] = accord_id
            return render(request, 'pages/admin_reglement_modifier.html', context)

        payment_modifier = []

        # Parcours des paiements sélectionnés pour récupérer leurs informations
        for payment_key in payment_keys:
            payment_id = payment_key.split('_')[1]  # Extraction de l'ID du paiement
            date_reglement_str = request.POST.get('date_echeance')  # Date d’échéance

            # Vérification que la date d’échéance est renseignée
            if not date_reglement_str:
                messages.error(request, "Veuillez bien définir l'échéance du règlement.")
                # # Stockage l'ID de l'accord de règlement dans la session avant redirection
                # request.session['accord_id'] = accord_id
                return render(request, 'pages/admin_reglement_modifier.html', context)
            # Teste format date
            # Validation du format des dates
            try:
                date_operation_reglement = datetime.strptime(date_reglement_str, date_format).date()
            except ValueError:
                messages.error(request, "Format de la date d'échéance non valide.")
                return render(request, 'pages/admin_remboursement_modifier.html', context)


            # Récupération de l'objet Payment correspondant
            paiement = Payment.objects.filter(id=payment_id).first()
            if paiement:
                # Conversion de la date d'échéance en objet datetime
                date_reglement = datetime.strptime(date_reglement_str, date_format).date()

                # Vérification que la date de règlement est au moins 7 jours après la date de création du paiement
                if (paiement.date_creation.date() + timedelta(days=7)) > date_reglement:
                    date_min = paiement.date_creation.date() + timedelta(days=8)
                    messages.info(
                        request,
                        f"La date de règlement ({date_reglement}) doit être au moins 7 jours après "
                        f"la date de création du paiement ({paiement.date_creation.date()}).<br>"
                        "Modifiez la date de l'échéance de règlement. <br>"
                        f"La date minimum est: {date_min}"
                    )
                    # # Stockage l'ID de l'accord de règlement dans la session avant redirection
                    # request.session['accord_id'] = accord_id
                    return render(request, 'pages/admin_reglement_modifier.html', context)

                # Ajout du paiement et de sa date d’échéance à la liste
                payment_modifier.append(( paiement.id))

        # Vérification que des paiements valides ont bien été sélectionnés
        if not payment_modifier:
            messages.error(request, "Veuillez définir une date d'échéance valide pour au moins un paiement.")
            # # Stockage l'ID de l'accord de règlement dans la session avant redirection
            # request.session['accord_id'] = accord_id
            return render(request, 'pages/admin_reglement_modifier.html', context)

        # Stockage des paiements validés dans la session avant redirection
        request.session['payment_modifier'] = payment_modifier

        # Stockage de la date de règlement dans la session avant redirection
        request.session['date_reglement_str'] = date_reglement_str

        # Stockage l'ID du professeur dans la session avant redirection
        request.session['prof_id'] = prof.id

        # Stockage l'ID de l'accord de règlement dans la session avant redirection
        request.session['accord_id'] = accord_id

        # Stockage le statut de l'accord de règlement dans la session avant redirection
        request.session['status'] = request.POST.get('status', '')

        # Stockage le statut de l'accord de règlement dans la session avant redirection
        request.session['ancien_payment_accords'] = ancien_payment_accords

        # Stockage la date de transfère dans la session avant redirection 
        request.session['date_trensfere'] = request.POST.get('date_trensfere', '')

        # Stockage l'ID de transfère dans la session avant redirection 
        request.session['transfere_id'] = request.POST.get('transfere_id', '')

        return redirect('admin_accord_reglement_modifier')

    return render(request, 'pages/admin_reglement_modifier.html', context)


@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_accord_reglement_modifier(request):
    """
    Modifier les accords de règlement pour le professeur 
    (même si le statut est réalisé pour que l'intervention de 
    l'administrateur soit sans limite),
    envoie un email pour le professeur et l'enregistrer
    en fin la mise à jour des paiements selon le statut initial et final
    """
    
    date_format = "%d/%m/%Y" # format de la date
    msg = "" # pour grouper les messages info dans un message final
    
    # Récupérer des paramètres de la session
    payment_requests = request.session.get('payment_modifier')
    date_reglement_str = request.session.get('date_reglement_str')
    accord_id = request.session.get('accord_id')
    prof_id = request.session.get('prof_id')
    status = request.session.get('status')
    date_trensfere = request.session.get('date_trensfere')
    transfere_id = request.session.get('transfere_id')
    ancien_payment_accords = request.session.get('ancien_payment_accords')

    # Condition nécessaire de l'activation du template
    if not accord_id:
        messages.info(request, "Il n'y a pas de règlement à enregistrer")
        return redirect('compte_administrateur')

    # Récupérer le professeur ou renvoyer une erreur 404 s'il n'existe pas
    professeur = get_object_or_404(Professeur, user_id=prof_id)

    # Récupérer l'ancien l'accord de règlement ou renvoyer une erreur 404 s'il n'existe pas
    accord_reglement = get_object_or_404(AccordReglement, id=accord_id)
    
    # Récupérer la date de règlement
    try:
        date_reglement = datetime.strptime(date_reglement_str, date_format).date()
    except ValueError:
            messages.info(request, f"Le format date de règlement: {date_reglement_str} n'est pas valide le format doit être jj/mm/aaaa")
            # Stockage l'ID de l'accord de règlement dans la session avant redirection
            request.session['accord_id'] = accord_id
            return redirect('admin_reglement_modifier')
    
    if not payment_requests:
        messages.info(request, "Il n'y a pas de règlement à enregistrer")
        return redirect('admin_payment_accord_reglement')
    
    payments=[] # pour la liste des paiements des élèves: date_versement, payment, user_eleve

    for payment_id in payment_requests: # étier les données de la session
        payment = Payment.objects.filter(id=payment_id).first()
        # c'est une requette qui lie la table Demande_paiement avec Eleve avec User
        demande_paiement = Demande_paiement.objects.select_related('eleve__user').filter(id=payment.model_id).first()
        if not demande_paiement: continue  # Ignorer les paiements sans demande associée (non nécessaire mais par prudence car à chaque paiement correspond un demande préalable)
        user_eleve = demande_paiement.eleve.user # pour le template
        payments.append(( payment, user_eleve))  # pour le template et le calcul des totaux

    totaux_payement=0
    for  payment, user_eleve in payments:
        totaux_payement += payment.amount
    totaux_versement = (totaux_payement * 2 ) / 3
    

    # préparer l'envoie de l'email
    user = request.user # admin
    email_user = user.email # email admin
    email_destinataire = professeur.user.email # email destinatère (professeur)
    destinations = ['prosib25@gmail.com', email_destinataire] # 'prosib25@gmail.com'à enlever dans le site production
    
    # Validation des emails dans destinations
    for destination in destinations:
        email_validator = EmailValidator() #inicialisation de l'objet EmailValidator
        try:
            email_validator(destination)
        except ValidationError:
            messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
            # même s'il y a erreur l'enregistrement continu car l'envoi de l'email n'est pas obligatoire
    
    # mise en forme du text_email et du sujet de l'email
    texte = f"\nRèglement prévu le:\t\t{date_reglement.strftime('%d/%m/%Y')}\n\nListe des paiements des élèves:\nElève:\t\t\t\t\tDate paiement\t\t\t\t\tPaiement\n"
    for  payment, user_eleve in payments:
        texte += f"{user_eleve.first_name} {user_eleve.last_name}\t\t\t\t\t{payment.date_creation.strftime('%d/%m/%Y')}\t\t\t\t\t{payment.amount:.2f}€\n"
    texte_totaux = f"\nMontant payé\t\tMontant à règler\n{totaux_payement:.2f}€\t\t\t\t\t{totaux_versement:.2f}€\nStatut accord de règlement: En attente"
    texte_fin= texte + texte_totaux
    sujet = f"Accord de règlement de: {totaux_payement:.2f}€, pour le: {date_reglement}"

    if 'btn_accord_enregistrement' in request.POST:  
        #envoie de l'email
        text_email_plus = request.POST.get('text_email_plus','')
        text_email = f"{texte_fin}\n\n{text_email_plus}"

        # Validation des emails dans destinations
        for destination in destinations:
            email_validator = EmailValidator() #inicialisation de l'objet EmailValidator
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
            msg += str(f"L'email a été envoyée avec succès relatif à l'accord de règlement du {date_reglement}.\n")
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
        msg += str(f"L'email a été enregistré avec succès relatif à l'accord de règlement du {date_reglement}.\n")


        # Mise à jour de accord de règlement
        accord_reglement.admin_user=request.user
        accord_reglement.total_amount=totaux_versement
        accord_reglement.email_id=email_telecharge.id
        accord_reglement.status=status
        accord_reglement.due_date=date_reglement
        if status == "Réalisé":
            accord_reglement.date_trensfere=datetime.strptime(date_trensfere, date_format).date()
            accord_reglement.transfere_id=transfere_id
        accord_reglement.save()
        msg += str(f"Mise à jour de accord de règlement du {date_reglement}.\n")
        
        # Avant la suppression des anciens détailles des accords de règlements 
        # il faux mettre à jour les enregisrements de Payment et Demande_paiement liés au ancien détaille de règlement
        # comme s'il n'y a pas eu d'accord de règlement
        for payment_id in ancien_payment_accords:
            payment_ancien = Payment.objects.filter(id=payment_id).first()
            if payment_ancien:
                payment_ancien.accord_reglement_id=None
                payment_ancien.reglement_realise=False
                payment_ancien.save()
                msg += str(f"Mettre à jour les anciens enregisrements de Payment.\n")
            # De même pour Demande_paiement
            demande_paiement_ancien = Demande_paiement.objects.filter(payment_id=payment_id).first()
            if demande_paiement_ancien:
                demande_paiement_ancien.accord_reglement_id=None
                demande_paiement_ancien.reglement_realise=False
                demande_paiement_ancien.save()
                msg += str(f"Mettre à jour les anciens enregisrements de Demande_paiement.\n")


        # Mise à jour des détailles des accords de règlements
        # Suppression des anciens détailles des accords de règlements
        DetailAccordReglement.objects.filter(accord=accord_id).delete()
        msg += str(f"Suppression des anciens détailles des accords de règlements.\n")

        # Ajout des nouveaux détailles des accords de règlements
        for  payment, user_eleve in payments:
            detaille_accord_reglement = DetailAccordReglement(
                accord=accord_reglement, 
                payment=payment, 
                professor_share=(payment.amount * 2) / 3, 
                description="Elève: " + user_eleve.first_name + " " + user_eleve.last_name +
                            ", Date paiement: " + payment.date_creation.strftime('%d/%m/%Y') +
                            ", Montant payé: " + str(payment.amount) + "€"
            )
            detaille_accord_reglement.save()
            msg += str(f"Ajout des nouveaux détailles des accords de règlements id={detaille_accord_reglement.id}.\n")

            # Mise à jour de l'enregistrement payment
            payment.accord_reglement_id=accord_reglement.id
            if status == "Réalisé": payment.reglement_realise=True
            payment.save()
            msg += str(f"Mise à jour de l'enregistrement payment id={payment.id}.\n")

            # Mise à jour Demande_paiement (pour chaque payment il y à une seule demande de paiement)
            demande_paiement = Demande_paiement.objects.filter(payment_id=payment.id).first()
            demande_paiement.accord_reglement_id=accord_reglement.id
            if status == "Réalisé": demande_paiement.reglement_realise=True
            demande_paiement.save()
            msg += f" Mise à jour Demande_paiement (accord_reglement_id = {demande_paiement.id})\n"

            msg += str(f"L'accord de règlement a été enregistré avec succès du {demande_paiement}.\n")
        messages.success(request, msg.replace("\n", "<br>") )

        # Vider les paramètres de la session
        keys_to_delete = [
            'payment_modifier', 'date_reglement_str', 'accord_id', 'prof_id', 
            'status', 'date_trensfere', 'transfere_id', 'ancien_payment_accords'
        ]

        for key in keys_to_delete:
            if key in request.session:
                del request.session[key]

        return redirect('compte_administrateur')

    # Contexte à passer au template
    context = {
        'professeur': professeur,
        'payments': payments,
        'totaux_payement':totaux_payement,
        'totaux_versement':totaux_versement,
        'texte_fin':texte_fin,
        'date_reglement': date_reglement,
        'status':status,
        'accord_reglement':accord_reglement, # Ancien statut de l'accord de règlement
        'transfere_id':transfere_id,
        'date_trensfere':date_trensfere,
    }

    # Rendu de la page avec les données filtrées
    return render(request, 'pages/admin_accord_reglement_modifier.html', context)




def reclamation(request):
    """
    Vue pour d'administration, professeur et élève permettant 
    d'afficher les détails de la réclamation,
    l'historique des messages, d'ajouter un nouveau message, 
    ou de modifier le statut, la priorité et la 
    cathégorie de la réclamation selon le type d'utilisateur
    """
    user = request.user

    reclamation_id = request.session.get('reclamation_id')
    if not reclamation_id: 
        return redirect('compte_administrateur')
    
    if not reclamation_id:
        messages.info(request, "Il n'y a pas de réclamation")
        if  hasattr(user, 'eleve'):return redirect('compte_eleve')
        elif  hasattr(user, 'professeur'):return redirect('compte_prof')
        else: return redirect('compte_administrateur')
    
    reclamation = get_object_or_404(Reclamation.objects.select_related('user'), id=reclamation_id)
    # Marquer le dernier message comme lu
    message_reclamation = MessageReclamation.objects.filter(reclamation=reclamation).last()
    if message_reclamation.user != request.user: # si le user du dernier message est différent du user actuel(à développer plus tard s'il y à plusieur super_user)
        message_reclamation.lu=True
        message_reclamation.save()
    
    # Récupération des messages et des pièces jointes en une seule requête optimisée
    messages_reclamation = MessageReclamation.objects.filter(
        reclamation=reclamation
    ).select_related('user').prefetch_related('pieces_jointes').order_by('date_creation')
    
    # Génération directe du contexte avec les messages et leurs pièces jointes
    messages_pieces = [(msg, msg.pieces_jointes.all()) for msg in messages_reclamation]
    
    if 'btn_modif' in request.POST:
        reclamation_categorie_id = int(request.POST.get('reclamation_categorie'))
        try:
            reclamation_categorie = ReclamationCategorie.objects.get(id=reclamation_categorie_id)
        except ReclamationCategorie.DoesNotExist:
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            if  hasattr(user, 'eleve'):return redirect('compte_eleve')
            elif  hasattr(user, 'professeur'):return redirect('compte_prof')
            else: return redirect('compte_administrateur')

        priorite = request.POST.get('priorite')
        statut = request.POST.get('statut')
        reclamation.categorie = reclamation_categorie
        if priorite: reclamation.priorite = priorite # dans le cas si le user est un admin le champ est activé
        if statut: reclamation.statut = statut # dans le cas si le user est un admin le champ est activé
        reclamation.save()
    
    if 'btn_enr' in request.POST:
        user = request.user
        titre = request.POST.get('titre', "").strip()
        message = request.POST.get('message', "").strip()
        if titre and message:
            # Création du  message de réponse
            message_reclamation = MessageReclamation.objects.create(
                user=user,
                reclamation=reclamation,
                titre=titre,
                message=message
            )

            # Gestion des fichiers
            fichiers_list = request.FILES.getlist('fichiers_list')
            for fichier in fichiers_list:
                form = PieceJointeReclamationForm(files={'fichier': fichier})
                if form.is_valid():
                    piece_jointe = form.save(commit=False)
                    piece_jointe.message_reclamation = message_reclamation
                    piece_jointe.save()
                else:
                    messages.error(request, f"Erreur avec le fichier {fichier.name}: {form.errors['fichier']}")

            messages.success(request, 'Message enregistré.')
            if  hasattr(user, 'eleve'):return redirect('compte_eleve')
            elif  hasattr(user, 'professeur'):return redirect('compte_prof')
            else: return redirect('compte_administrateur')

        else:
            messages.error(request, "Vous devez remplir les champs titre et message.")

        

    categories = ReclamationCategorie.objects.all()

    context = {
        'categories': categories,
        'messages_pieces': messages_pieces,
        'reclamation': reclamation,
    }
    return render(request, 'pages/reclamation.html', context)



def nouvelle_reclamation(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')

    user = request.user
    titre = request.POST.get('titre', "").strip()
    message = request.POST.get('message', "").strip()
    categorie_nom = request.POST.get('categorie', "").strip()

    if 'btn_enr' in request.POST:
        if titre and message and categorie_nom:
            # Vérifier si la catégorie existe
            categorie = ReclamationCategorie.objects.filter(nom=categorie_nom).first()
            if not categorie:
                messages.error(request, "La catégorie sélectionnée est invalide.")
                return redirect('nouvelle_reclamation')

            # Création de la réclamation
            reclamation = Reclamation.objects.create(
                user=user,
                categorie=categorie,
                statut='en_attente',
                priorite='moyenne'
            )

            # Création du premier message de réclamation
            message_reclamation = MessageReclamation.objects.create(
                user=user,
                reclamation=reclamation,
                titre=titre,
                message=message
            )

            # Gestion des fichiers
            fichiers_list = request.FILES.getlist('fichiers_list')
            for fichier in fichiers_list:
                form = PieceJointeReclamationForm(files={'fichier': fichier})
                if form.is_valid():
                    piece_jointe = form.save(commit=False)
                    piece_jointe.message_reclamation = message_reclamation
                    piece_jointe.save()
                else:
                    messages.error(request, f"Erreur avec le fichier {fichier.name}: {form.errors['fichier']}")

            # Si la réclamation et liée à un paiement
            # Récupération sécurisée du paiement si 
            # le user est un élève qui veut ajouter une 
            # réclamation à partir un paiement prés déterminé
            if  hasattr(user, 'eleve'):
                payment_id = request.session.get('reclamation_payment_id')
                if payment_id:
                    payment = Payment.objects.get(id=payment_id)
                    if not payment: messages.error(request, "Il n'y a pas de paiement lié à la reclamation")
                    else: 
                        payment.reclamation=reclamation
                        payment.save()
                        messages.success(request, 'Le paiement est mis à jour.')

            messages.success(request, 'Réclamation enregistrée.')
            if  hasattr(user, 'eleve'): return redirect('compte_eleve')
            if  hasattr(user, 'professeur'): return redirect('compte_prof')

        else:
            messages.error(request, "Vous devez remplir les champs obligatoires.")

    categories = ReclamationCategorie.objects.all()
    context = {
        'categories': categories,
        'titre': titre,
        'message': message,
        'categorie': categorie_nom,
    }
    return render(request, 'pages/nouvelle_reclamation.html', context)


def reclamations(request):
    """
    Afficher toutes les réclamations de la période 
    liées à l'élève (et / ou) au professeur selon 
    le user (élève, professeur, admin)
    """
    
    
    # messages.info(request, f'key = {Fernet.generate_key()}')
    # Récupérer le user
    user = request.user
    if not user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    
    
    date_format = "%d/%m/%Y"
    status_str = ""

    # Récupération des dates minimales et maximales depuis la base de données
    dates = Reclamation.objects.exclude(statut__in=['resolue', 'fermee']).aggregate(
        min_date=Min('date_creation'), 
        max_date=Max('date_creation')
    )

    # Valeurs par défaut si aucune réclamation n'existe
    date_min = dates['min_date'] or (timezone.now().date() - timedelta(days=15))
    date_max = dates['max_date'] or timezone.now().date()

    # Récupération des dates depuis le formulaire ou valeurs par défaut
    date_debut_str = request.POST.get('date_debut', date_min.strftime(date_format))
    date_fin_str = request.POST.get('date_fin', date_max.strftime(date_format))

    try:
        date_debut = datetime.strptime(date_debut_str, date_format).date()
        date_fin = datetime.strptime(date_fin_str, date_format).date()

        if date_debut > date_fin:
            raise ValueError("La date de début doit être inférieure ou égale à la date de fin.")
    
    except ValueError as e:
        messages.error(request, f"Erreur de date : {e}")
        return render(request, 'pages/reclamations.html', {
            'reclamations': [],  
            'date_debut': date_debut, 
            'date_fin': date_fin
        })

    # Définition des filtres
    filters = { 
        'date_creation__range': (date_debut, date_fin + timedelta(days=1))
    }

    # Correspondance des boutons de filtrage aux statuts des réclamations
    status_filter = {
        'btn_en_attente': 'en_attente',
        'btn_en_cours': 'en_cours',
        'btn_resolue': 'resolue',
        'btn_fermee': 'fermee',
    }

    # Application du filtre en fonction du bouton cliqué
    for btn, status in status_filter.items():
        if btn in request.POST:
            filters['statut'] = status
            status_str = status
            break

    # Filtrer les réclamations ayant le prmier message non lu
    # le tri des non lues est fait dans le template
    if 'btn_non_lu' in request.POST:
        status_str = "non_lu"

    if  hasattr(user, 'eleve') or hasattr(user, 'professeur'):filters['user'] = user  # Ajout du filtre utilisateur pour élève ou professeur

    # Récupération des réclamations (le tri ne distingue pas les messages lu et non lu c'est dans le template que la séparation est faite)
    reclamations = Reclamation.objects.filter(**filters).order_by('-priorite','-date_creation')
    reclamation_list = []
    for reclamation in reclamations:
        reclamation_list.append((reclamation, encrypt_id(reclamation.id))) # cripter ID de la réclamation
        
    if request.POST:
        # Extraction de l'ID de la réclamation choisi dans le formulaire
        reclamation_keys = [key for key in request.POST.keys() if key.startswith('btn_reclamation_id')]
        reclamation_key = [key.split('btn_reclamation_id')[1] for key in reclamation_keys][0]
        

        # Vérification du nombre d'IDs extraits
        if reclamation_key:
                request.session['reclamation_id'] = decrypt_id(reclamation_key) # décripter ID de la réclamation
                return redirect('reclamation')
        else:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            if  hasattr(user, 'eleve'):return redirect('compte_eleve')
            elif  hasattr(user, 'professeur'):return redirect('compte_prof')
            else: return redirect('compte_administrateur')

    # Rendu de la page avec le contexte
    context = {
        'reclamation_list': reclamation_list,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'status_str': status_str,
    }
    return render(request, 'pages/reclamations.html', context)




from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q

def admin_faq(request):
    if hasattr(request.user, 'eleve'):
        role = 'eleve'
    elif hasattr(request.user, 'professeur'):
        role = 'prof'
    elif request.user.is_staff:
        role = 'staff'
    else:
        role = 'visiteur'

    filtre_role = request.GET.get('role')
    if filtre_role is not None:
        role = filtre_role

    keyword = request.GET.get('keyword', '').strip()

    faqs = FAQ.objects.filter(actif=True)
    if role :
        faqs = faqs.filter(public_cible=role)
    if keyword:
        faqs = faqs.filter(
            Q(question__icontains=keyword) |
            Q(reponse__icontains=keyword)
        )

    paginator = Paginator(faqs.order_by('ordre'), 5)  # 5 FAQs par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render(request, 'pages/faq_items.html', {'page_obj': page_obj}).content.decode('utf-8')
        pagination_html = render(request, 'pages/faq_pagination.html', {'page_obj': page_obj}).content.decode('utf-8')
        return JsonResponse({'html': html, 'pagination': pagination_html})

    return render(request, 'pages/admin_faq.html', {
        'page_obj': page_obj,
    })


# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_payment_eleve_remboursement(request):
    """
    Vue permettant d'afficher les paiements d'élèves pas encore payés aux profs.
    et qui ne sont pas sujet d'un rembourcement précédent
    Fonctionnalités :
    - Filtrer les paiements selon une période donnée (dates de début et de fin).
    - Appliquer des filtres selon le statut du paiement (en attente, approuvé, annulé, etc.).
    - Associer chaque paiement à son élève .
    - permettre de passer au remboursement après sélection des paiements consernés
    - seul les paiement approuvé et réclamés peuvent être sélectionner
    """

    # Format utilisé pour l'affichage et la conversion des dates
    date_format = "%d/%m/%Y"
    status_str=""

    # Récupération des dates minimales et maximales depuis la base de données
    dates = Payment.objects.filter(
        model='demande_paiement',
        model_id__isnull=False, # ID de la demande de paiement liée au paiement
        reglement_realise=False, # Même si l'accord de règlement existe il doit être non réalisé
        accord_remboursement_id__isnull=True, # Il n'y a pas d'accord de remboursement lié au paiement
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
        return render(request, 'pages/admin_payment_eleve_remboursement.html', {
            'paiements': [], 
            'eleves': [], 
            'date_debut': date_debut, 
            'date_fin': date_fin
        })

    # Définition des critères de filtrage des paiements
    # Dictionnaire des fitres obligatoires
    filters = {
        'model': 'Demande_paiement',  # Filtrer uniquement les paiements liés aux demandes de paiement
        'model_id__isnull': False, # il faut que ID de la Demande de paiement soit défini
        'reglement_realise': False,  # Seuls les paiements en attente de règlement
        'accord_remboursement_id__isnull': True,  # Seuls les paiements non liés à un rembourcement
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
    # filtre optionnel selon le cas qui j'ajoute au dictionnaire des filtres obligatoires
    for btn, status in status_filter.items():
        if btn in request.POST:
            filters['status'] = status
            status_str=status # pour afficher dans le template le role du bouton activé
            break

    # Filtrage des paiements contestés (réclamation) filtre optionnel selon le cas qui j'ajoute au dictionnaire des filtres obligatoires
    if 'btn_reclame' in request.POST:
        filters['reclamation__isnull'] = False  # Paiements contestés par l'élève
        status_str="Réclamé"

    # Récupération des paiements en fonction des filtres
    # **filters est une opération de décompression (ou unpacking) 
    # du dictionnaire. Cela permet de passer chaque paire clé/valeur 
    # du dictionnaire comme des arguments nommés dans un filtre
    payments = Payment.objects.filter(**filters).order_by('-date_creation')

    # Initialisation des listes pour stocker les résultats
    paiements, eleves = [], set()

    # Parcours des paiements récupérés pour associer les informations nécessaires
    for payment in payments:
        # Récupération de la demande de paiement associée (à chaque paiement correspond une seule demande de paiement)
        demande_paiement = Demande_paiement.objects.filter(id=payment.model_id).first()
        if not demande_paiement: continue  # Ignorer les paiements sans demande associée

        professeur = demande_paiement.user  # Récupération du professeur lié au paiement
        eleve = demande_paiement.eleve.user # récupérer le user de l'élève
        accord_reglement = None
        accord_reglement_id = 0

        # Vérification et récupération de l'accord de règlement associé
        if payment.accord_reglement_id:
            accord_reglement = AccordReglement.objects.filter(id=payment.accord_reglement_id).first()
            if not accord_reglement: continue
            accord_reglement_id = accord_reglement.id

        # Ajout des informations collectées à la liste des paiements
        paiements.append((payment, encrypt_id(payment.id), eleve, professeur, accord_reglement, encrypt_id(accord_reglement_id)))
        eleves.add(eleve )  # Utilisation d'un set() pour éviter les doublons
    
    # liste eleve ID elve sans doublon pour l'élève car  eleves.add(eleve, encrypt_id(eleve)) est faux puisque
    #  encrypt_id(eleve) change à chaque foix donc les tuples sont unique mais eleve va être répéter
    # en d'autre termes même si l'eleve se répète la valeur : encrypt_id(eleve) ne se répète pas
    # d'ou le code : eleves.add(eleve, encrypt_id(eleve)) donne des répétition d'eleve
    liste_eleve_id =[]
    for eleve in list(eleves):
        liste_eleve_id.append((eleve, encrypt_id(eleve.id)))
    
        
    # Extraction de l'ID du paiement choisi dans le formulaire
    paiement_ids = [key.split('btn_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_paiement_id')]
    # Vérification du nombre d'IDs extraits
    if paiement_ids:
        if len(paiement_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['payment_id'] = decrypt_id(paiement_ids[0])
            return redirect('admin_payment_demande_paiement')
        elif len(paiement_ids) !=1:  # Plusieurs IDs trouvés, erreur système
            logger.error("Il devrait exister un seul ID pour le paiement")
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_administrateur')

    # Extraction de l'ID du règlement choisi dans le formulaire
    accord_ids = [key.split('btn_detaille_reglement_id')[1] for key in request.POST.keys() if key.startswith('btn_detaille_reglement_id')]
    if accord_ids:
        # Vérification du nombre d'IDs extraits
        if len(accord_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['accord_id'] = decrypt_id((accord_ids[0]))
            return redirect('admin_reglement_detaille')
          
    # Extraction l'ID d'élève à partir des boutons du formulaire
    eleve_ids = [
        key.removeprefix('btn_détaille_') 
        for key in request.POST 
        if key.startswith('btn_détaille_')
    ]

    # Vérification qu'un seul ID a été soumis
    if len(eleve_ids) == 1: # else est ignoré
        eleve_id_encrypted = eleve_ids[0]
        # eleve_id = decrypt_id(eleve_id_encrypted) if eleve_id_encrypted else None
        request.session['eleve_id'] = eleve_id_encrypted
        # messages.info(request, f"eleve_id_encrypted = {eleve_id_encrypted}  -- eleve_id = {eleve_id} ")

        # Extraction des IDs de paiements cochés pour cet élève
        # on utilise checkbox_eleve_id{eleve_id} pour ne prendre que les paiement cochés du même éléve
        # voire template:name="checkbox_eleve_id{{eleve_id}}_payment_id{{ payment_id }}"
        prefix_checkbox = f'checkbox_eleve_id{eleve_id_encrypted}_payment_id'
        liste_payment_remboursement = [
            key.removeprefix(prefix_checkbox) 
            for key in request.POST 
            if key.startswith(prefix_checkbox)
        ]

        # Stockage en session
        request.session['liste_payment_rembourcement'] = liste_payment_remboursement

        # Redirection vers la vue suivante
        return redirect('admin_payment_accord_remboursement')

    

    # Préparation du contexte pour l'affichage dans le template
    context = {
        'paiements': paiements,
        'eleves': liste_eleve_id,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'status_str': status_str,
    }

    # Affichage de la page avec les paiements en attente de règlement
    return render(request, 'pages/admin_payment_eleve_remboursement.html', context)

from django.contrib.admin.views.decorators import staff_member_required

# J'ai remplacé LE décorateur lambda par @staff_member_required pour plus de clarté.
@staff_member_required(login_url='/login/')
def admin_payment_accord_remboursement(request):
    """
    Vue d'administration permettant de gérer les remboursements liés à un élève :
    - Affiche les paiements sélectionnés.
    - Prépare les montants et dates de remboursement.
    """

    # --- Récupération et déchiffrement de l'ID de l'élève ---
    eleve_id_encrypted = request.session.get('eleve_id')
    try:
        eleve_id = decrypt_id(eleve_id_encrypted)
    except Exception as e:
        logger.error(f"Erreur de déchiffrement de l'ID élève : {e}")
        messages.error(request, "Erreur système : impossible de lire l'identifiant de l'élève.")
        return redirect('compte_administrateur')

    # --- Récupération de l'élève ---
    eleve = get_object_or_404(Eleve, user_id=eleve_id)

    # --- Récupération des paiements à rembourser depuis la session ---
    liste_payment_encrypted = request.session.get('liste_payment_rembourcement', [])
    try:
        payment_ids = [decrypt_id(pid) for pid in liste_payment_encrypted if pid]
    except Exception as e:
        logger.error(f"Erreur de déchiffrement d'ID de paiement : {e}")
        messages.error(request, "Erreur système : identifiant de paiement invalide.")
        return redirect('compte_administrateur')

    # --- Requête des paiements à afficher ---
    payments = Payment.objects.filter(id__in=payment_ids).annotate(
        date_plus_15=F('date_creation') + timedelta(days=15)
    ).order_by('-date_creation')

    if not payments.exists():
        logger.error("Aucun paiement valide trouvé après déchiffrement.")
        messages.error(request, "Aucun paiement valide n'a pu être trouvé.")
        return redirect('compte_administrateur')

    # --- Format de date et liste pour affichage ---
    date_format = "%d/%m/%Y"
    liste_payments = [
        (
            payment,
            encrypt_id(payment.id),
            (payment.date_creation + timedelta(days=15)).date().strftime(date_format),
            payment.amount
        )
        for payment in payments
    ]

    # --- Contexte à transmettre au template ---
    context = {
        'liste_payments': liste_payments,
        'eleve': eleve,
    }

    # Extraction de l'ID du paiement choisi dans le formulaire is btn_paiement_id activé
    paiement_ids = [key.split('btn_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_paiement_id')]
    # Vérification du nombre d'IDs extraits
    if paiement_ids:
        if len(paiement_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            decripted_paiement_id = decrypt_id(paiement_ids[0])
            if decripted_paiement_id:
                request.session['payment_id'] = decripted_paiement_id
                return redirect('admin_payment_demande_paiement')
        
        logger.error("La valeur de ID du paiement n'a pas pu être décripter, erreur système")
        messages.error(request, "La valeur de ID du paiement n'a pas pu être décripter, erreur système")
        return redirect('compte_administrateur')
        

    # Vérification si le formulaire a été soumis pour accorder un remboursement
    if 'btn_accord_remboursement' in request.POST:
        # Récupération des IDs non décryptés des paiements depuis les clés du formulaire
        uncrypted_paiement_ids = [
            key.split('date_payment_')[1]
            for key in request.POST.keys()
            if key.startswith('date_payment_')
        ]
        # On parcourt tous les IDs récupérés
        liste_payments = [] # réinitialisation de la liste
        for payment in payments:
            default_date = (payment.date_creation + timedelta(days=15)).date()
            montant_remboursement_str = ""
            for paiement_id_encripted in uncrypted_paiement_ids:
                paiement_id_decripted = decrypt_id(paiement_id_encripted)
                # On compare l'ID du paiement courant avec l'ID déchiffré du formulaire
                if payment.id == paiement_id_decripted:
                    # Si c'est bien le paiement correspondant, on récupère la date de remboursement saisie dans le formulaire
                    # Sinon, on garde la date par défaut
                    date_rebours = request.POST.get(
                        f'date_remboursement_{paiement_id_encripted}',
                        default_date.strftime(date_format)
                    )
                    
                    # Récupération brute du champ
                    montant_remboursement_str = request.POST.get(f'remboursement_{paiement_id_encripted}', '')

                    # Suppression du symbole "€" et des espaces autour (si présents)
                    montant_remboursement_str = montant_remboursement_str.replace('€', '').strip()
                    
                    # On ajoute les infos à la liste : l'objet payment, l'ID chiffré, et la date (saisie ou par défaut)
                    liste_payments.append((payment, encrypt_id(payment.id), date_rebours, Decimal(montant_remboursement_str)))

        context['liste_payments'] = liste_payments  # mettre à jour le contexte pour le template

        liste_remboursement = []
        for uncrypted_id in uncrypted_paiement_ids:
            try:
                paiement_id = decrypt_id(uncrypted_id)
                paiement = Payment.objects.filter(id=paiement_id).first()
                

                if not paiement or not paiement.date_creation or not paiement.amount:
                    messages.error(request, "Aucun paiement trouvé. Une erreur système s’est produite. Veuillez contacter le développeur.")
                    logger.error("Aucun paiement trouvé. Une erreur système s’est produite. Veuillez contacter le développeur.")
                    return redirect('compte_administrateur')

                # Récupération des champs du formulaire pour ce paiement
                date_remboursement_str = request.POST.get(f'date_remboursement_{uncrypted_id}')
                
                # Récupération brute du champ
                montant_remboursement_str = request.POST.get(f'remboursement_{uncrypted_id}', '')

                # Suppression du symbole "€" et des espaces autour (si présents)
                montant_remboursement_str = montant_remboursement_str.replace('€', '').strip()
                
                try:
                    montant_decimal = Decimal(montant_remboursement_str)
                except InvalidOperation:
                    messages.error(request, f"Le montant '{montant_remboursement_str}' est invalide. Veuillez entrer un montant correct.")
                    logger.error(f"Le montant '{montant_remboursement_str}' est invalide. Veuillez entrer un montant correct.")
                    return render(request, 'pages/admin_payment_accord_remboursement.html', context)

                if montant_decimal > paiement.amount:
                    messages.error(request, f"Le montant du remboursement ({montant_decimal}) ne peut pas dépasser le montant initial payé ({paiement.amount}).")
                    logger.error(f"Le montant du remboursement ({montant_decimal}) ne peut pas dépasser le montant initial payé ({paiement.amount}).")
                    return render(request, 'pages/admin_payment_accord_remboursement.html', context)


                if not date_remboursement_str or not montant_remboursement_str:
                    messages.error(request, "Il faut définir la date de remboursement et le montant à rembourser.")
                    logger.error("Il faut définir la date de remboursement et le montant à rembourser.")
                    return render(request, 'pages/admin_payment_accord_remboursement.html', context)


                try:
                    # Conversion de la date de remboursement
                    date_remboursement = datetime.strptime(date_remboursement_str, date_format).date()

                    # Vérification de la cohérence des dates
                    if date_remboursement < paiement.date_creation.date():
                        raise ValueError(f"La date de remboursement ({date_remboursement_str}) doit être postérieure ou égale à la date du paiement.")

                except ValueError as e:
                    messages.error(request, f"Erreur de date : {e}")
                    return render(request, 'pages/admin_payment_accord_remboursement.html', context)

                # les conditions requises pour  valider un remboursement lié à un paiement
                if paiement.status !='Approuvé' or paiement.reglement_realise  or paiement.accord_remboursement_id:
                    messages.error(request, f"Erreur système : un  paiement, ou plus, ne remplit pas les conditions requises pour être validé.\n paiement.status = {paiement.status},\n paiement.reglement_realise = {paiement.reglement_realise}\n paiement.accord_remboursement_id = {paiement.accord_remboursement_id}")
                    logger.error(f"Erreur système : un  paiement, ou plus, ne remplit pas les conditions requises pour être validé.\n paiement.status = {paiement.status},\n paiement.reglement_realise = {paiement.reglement_realise}\n paiement.accord_remboursement_id = {paiement.accord_remboursement_id}")
                    return redirect('compte_administrateur')
                if DetailAccordRemboursement.objects.filter(payment=paiement).exists():
                    messages.error(request, f"Erreur système : un paiement, ou plus existe dans la table DetailAccordRemboursement = {DetailAccordRemboursement.objects.filter(payment=paiement).first()}")
                    logger.error(f"Erreur système : un paiement, ou plus existe dans la table DetailAccordRemboursement = {DetailAccordRemboursement.objects.filter(payment=paiement).first()}")
                    return redirect('compte_administrateur')
                accord=DetailAccordReglement.objects.filter(payment=paiement).first()
                if accord and AccordReglement.objects.filter(id=accord.id, status='Réalisé').exists():
                    messages.error(request, f"Erreur système : un paiement est déjà lié à un accord de règlement réalisé. ID= {AccordReglement.objects.first(accord=accord, status='Réalisé').first} ")
                    logger.error(f"Erreur système : un paiement est déjà lié à un accord de règlement réalisé. ID= {AccordReglement.objects.first(accord=accord, status='Réalisé').first} ")
                    return redirect('compte_administrateur')
                # Tous les conditions sont validées
                liste_remboursement.append((encrypt_id(paiement_id), date_remboursement_str, montant_remboursement_str))

            except Exception as e:
                messages.error(request, f"Une erreur inattendue s’est produite, ou l'ID du paiement n'a pas pu être décripter : {e}")
                logger.error(f"Une erreur inattendue s’est produite, ou l'ID du paiement n'a pas pu être décripter : {e}")
                return redirect('compte_administrateur')
            
        # Stockage en session
        request.session['liste_remboursement'] = liste_remboursement
        return redirect('admin_accord_remboursement')

    return render(request, 'pages/admin_payment_accord_remboursement.html', context)




@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_accord_remboursement(request):
    """
    Vue Django permettant :
    - De récupérer les remboursements sélectionnés pour un élève.
    - De regrouper les paiements par date de remboursement.
    - D'envoyer les emails d'accord de remboursement.
    - D'enregistrer l'accord et de mettre à jour les paiements.
    """

    textes = []  # Stocke les textes des emails envoyés

    # --- 1. Récupération et déchiffrement sécurisé de l'ID élève ---
    eleve_id_encrypted = request.session.get('eleve_id')
    if not eleve_id_encrypted:
        messages.error(request, "Aucun élève sélectionné.")
        return redirect('admin_payment_accord_remboursement')

    try:
        eleve_id = decrypt_id(eleve_id_encrypted)
    except Exception as e:
        logger.error(f"Erreur de déchiffrement de l'ID élève : {e}")
        messages.error(request, "Erreur système : impossible de lire l'identifiant de l'élève.")
        return redirect('admin_payment_accord_remboursement')

    # --- 2. Récupération de l'élève ---
    eleve = get_object_or_404(Eleve, user_id=eleve_id)

    # --- 3. Récupération et vérification de la liste des paiements à rembourser ---
    liste_remboursement = request.session.get('liste_remboursement', [])
    if not liste_remboursement:
        messages.info(request, "Il n'y a pas de remboursement à enregistrer.")
        return redirect('admin_payment_accord_remboursement')

    # --- 4. Traitement et regroupement des paiements par date ---
    regroupement_par_date = defaultdict(list)
    payments_list = []

    for paiement_id_enc, date_remboursement_str, montant_remboursement_str in liste_remboursement:
        try:
            paiement_id = decrypt_id(paiement_id_enc)
        except Exception as e:
            logger.error(f"Erreur de déchiffrement d'un ID de paiement : {e}")
            continue  # Ignore cet enregistrement et passe au suivant

        payment = Payment.objects.filter(id=paiement_id).first()
        if payment:
            montant_remboursement = Decimal(montant_remboursement_str)
            payments_list.append((date_remboursement_str, payment, montant_remboursement))
            regroupement_par_date[date_remboursement_str].append((payment, montant_remboursement))
        else:
            logger.warning(f"Paiement introuvable pour l'ID : {paiement_id}")

    # --- 5. Calcul des totaux par date de remboursement ---
    totaux = []
    for date_str, paiements in regroupement_par_date.items():
        total_remboursement = sum(remboursement for _, remboursement in paiements)
        total_paiement = sum(payment.amount for payment, _ in paiements)
        totaux.append((date_str, total_paiement, total_remboursement))

    if 'btn_accord_enregistrement' in request.POST:
        # --- 6. Initialisation de l'envoi d'email ---
        user = request.user  # Admin connecté
        email_user = user.email
        email_destinataire = eleve.user.email
        destinations = ['prosib25@gmail.com', email_destinataire]

        # --- 7. Validation des adresses email ---
        email_validator = EmailValidator()
        for destination in destinations:
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                # Remarque : on continue malgré l'erreur, l'envoi n'est pas bloquant.

        # --- 8. Parcours des dates pour création du texte et envoi des emails ---
        for date_request in regroupement_par_date.keys():
            msg = ""  # Message d'information par date
            # Construction du texte de l'email
            texte = (
                f"\nRemboursement prévu le :\t{date_request}\n\n"
                f"Liste des paiements de l'élève à rembourser :\n"
                f"Date paiement\tPaiement\n"
            )

            # Ajouter les paiements correspondant à cette date
            for date_versement, payment, amount in payments_list:
                if date_versement == date_request:
                    texte += f"{payment.date_creation.strftime('%d/%m/%Y')}\t\t{payment.amount:.2f}€\n"

            # Ajout des totaux pour la date
            texte_totaux = ""
            for date, total_paiement, total_remboursement in totaux:
                if date == date_request:
                    texte_totaux = (
                        f"\nMontant payé\t\tMontant à rembourser\n"
                        f"{total_paiement:.2f}€\t\t\t\t{total_remboursement:.2f}€\n"
                        f"Statut accord de remboursement : En attente"
                    )
                    sujet = f"Accord de remboursement de {total_remboursement:.2f}€, prévu le {date}"
                    break  # On a trouvé, pas besoin de continuer

            # Texte final de l'email
            texte_fin = texte + texte_totaux
            textes.append((date_request, texte_fin))

            # --- 9. Envoi de l'email ---
            try:
                send_mail(
                    sujet,
                    texte_fin,
                    email_user,
                    destinations,
                    fail_silently=False,
                )
                msg += f"L'email a été envoyé avec succès pour l'accord de remboursement du {date_request}.\n"
            except Exception as e:
                messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")

            # --- 10. Enregistrement de l'email envoyé ---
            try:
                email_enregistre = Email_telecharge(
                    user=user,
                    email_telecharge=email_user,
                    text_email=texte_fin,
                    user_destinataire=eleve.user.id,
                    sujet=sujet
                )
                email_enregistre.save()
                msg += f"L'email a été enregistré avec succès pour l'accord de remboursement du {date_request}.\n"
            except Exception as e:
                logger.error(f"Erreur lors de l'enregistrement de l'email : {e}")
                messages.error(request, "Erreur lors de l'enregistrement de l'email.")
            

            # Enregistrement des accords de rembourcement
            for date, totaux_payement, totaux_remboursement in totaux:
                if date == date_request:
                    try:
                        due_date = datetime.strptime(date_request, "%d/%m/%Y").date()
                        accord_remboursement = AccordRemboursement(
                            admin_user=user, 
                            eleve=eleve, 
                            total_amount=Decimal(totaux_remboursement), 
                            email_id=email_enregistre.id, # On relie à l'email sauvegardé
                            status="pending", 
                            due_date=due_date )
                        accord_remboursement.save()

                        # Enregistrement des détailles des accords de remboursement
                        for date_versement, payment, amount in payments_list:
                            if date_versement == date_request: # car les accords de remboursements sont groupés par date de règlement
                                detaille_accord_remboursement = DetailAccordRemboursement(
                                    accord=accord_remboursement, 
                                    payment=payment, 
                                    refunded_amount=amount, 
                                    description=(
                                        f"Date paiement : {payment.date_creation.strftime('%d/%m/%Y')}, "
                                        f"Montant payé : {payment.amount:.2f}€"
                                    )
                                )
                                detaille_accord_remboursement.save()

                                # mise à jour de l'enregistrement payment
                                payment.accord_remboursement_id=accord_remboursement.id 
                                payment.save()
                                
                                # je n'est pas besoin de créer des champs dans la table Demande_paiement
                                # pour lier les rembousements aux demande de paiement car pour chaque 
                                # demande de paiement correspond un seul paiement et les paiement sont déjà liés aux remboursements

                        msg += str(f"L'accord de remboursement a été enregistré avec succès du {date_versement}.\n\n")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'enregistrement de l'accord de remboursement : {e}")
                        messages.error(request, "Erreur lors de l'enregistrement de l'accord de remboursement.")
                            
            # afficher l'ensmble des messages pour chaque accord de remboursement
            messages.success(request, msg.replace("\n", "<br>") )

        # vider les variables  de la session
        request.session.pop('liste_remboursement', None)
        request.session.pop('eleve_id', None)
        request.session.pop('liste_payment_rembourcement', None)
        return redirect('admin_payment_eleve_remboursement')

    context = {
        'eleve': eleve,
        'date_requests': regroupement_par_date.keys(),
        'totaux': totaux,
        'payments_list': payments_list,
    }
    return render(request, 'pages/admin_accord_remboursement.html', context)


# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_remboursement(request):
    """
    affiche les remboursements effectués par l'administrateur 
    pour une période donnée, permet de passer à la mise à 
    jour des enregistrements sélectionnés et
    de visualiser les détaillesdes accord de remboursements
    """
    
    teste = True # pour controler les validations
    date_format = "%d/%m/%Y" # Format date

    # Récupération des dates minimales et maximales depuis la base de données
    dates = AccordRemboursement.objects.filter(
        ~Q(status='completed'),  # Exclure les enregistrements avec status='Réalisé'
        transfere_id__isnull=True,
        date_trensfere__isnull=True
    ).aggregate(
        min_date=Min('due_date'),
        max_date=Max('due_date')
    )

    # Définition des valeurs par défaut avec la priorité des valeurs (min_date, max_date )
    date_min = dates['min_date'] or (timezone.now().date() - timedelta(days=15))
    date_max = dates['max_date'] or timezone.now().date()

    # Récupération des valeurs envoyées par le formulaire POST avec fallback aux valeurs par défaut
    date_debut_str = request.POST.get('date_debut', date_min.strftime(date_format))
    date_fin_str = request.POST.get('date_fin', date_max.strftime(date_format))


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

    # Fonction interne pour récupérer les remboursement
    def get_remboursements(date_debut, date_fin, filter_criteria=None):
        if filter_criteria is None:
            filter_criteria = {}

        return AccordRemboursement.objects.filter(
            due_date__range=(date_debut , date_fin + timedelta(days=1)),
            **filter_criteria
        ).order_by('due_date') # [date_debut , date_fin]

    # Récupérer tous les accords de remboursements
    accord_remboursements = get_remboursements(date_debut, date_fin)
    # messages.info(request, f"accord_remboursements = {(accord_remboursements).count()}")

    # Vérification du type de requête et application des filtres en fonction du bouton cliqué
    if 'btn_tous' in request.POST:
        # Filtrer pour tous les emails
        accord_remboursements = get_remboursements(date_debut, date_fin)
        # messages.info(request, f"accord_remboursements = {(accord_remboursements).count()}")
    elif 'btn_en_ettente' in request.POST:
        # Filtrer pour les remboursement en attente
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'pending'})
        statut = "En attente"
    elif 'btn_en_cours' in request.POST:
        # Filtrer pour les remboursement en cours
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'in_progress'})
        statut = "En cours"
    elif 'btn_invalide' in request.POST:
        # Filtrer pour les remboursements invalides
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'invalid'})
        statut = "Invalide"
    elif 'btn_annule' in request.POST:
        # Filtrer pour les paiements annulés
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'canceled'})
        statut = "Annulé"
    elif 'btn_realiser' in request.POST:
        # Filtrer pour les paiements réclamés par les élèves
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'completed'})
        statut = "Réalisé"

    accord_remboursement_approveds = []
    for accord_remboursement in accord_remboursements:
        accord_id_uncrypted = encrypt_id(accord_remboursement.id)
        accord_remboursement_approveds.append((accord_remboursement , accord_id_uncrypted))
    
    context = {
        'accord_remboursement_approveds': accord_remboursement_approveds,
        'date_fin':date_fin,
        'date_debut':date_debut,
        'statut': statut,
        'date_now':date_now
    }

    if request.POST :
        # Extraction de l'ID du règlement choisi dans le formulaire
        accord_ids_uncrypted = [key.split('btn_detaille_remboursement_id')[1] for key in request.POST.keys() if key.startswith('btn_detaille_remboursement_id')]
        if accord_ids_uncrypted:
            if accord_ids_uncrypted and len(accord_ids_uncrypted) == 1:
                request.session['accord_remboursement_id'] = accord_ids_uncrypted[0]
                return redirect('admin_remboursement_detaille')

    if 'btn_enr' in request.POST:
        # Récupérer les remboursements cochés
        remboursement_keys = [key for key in request.POST.keys() if key.startswith('checkbox_remboursement_id')]
        # Pour sélectionner un enregistrement il faut le cocher et définir la date du règlement et modifier le statut et autres conditions (voire suite)
        if not remboursement_keys: # pas de règlement sélectionné
            messages.error(request, "Il faut au moins cocher un remboursement")
            return render(request, 'pages/admin_remboursement.html', context)

        remboursement_requests = []
        # récupérter les données des paiements sélectionnés
        for remboursement_key in remboursement_keys:
            uncrypted_id = (remboursement_key.split('checkbox_remboursement_id')[1]) # récupérer ID du remboursement
            decrypted_id = decrypt_id(uncrypted_id)
            # messages.info(request, f"decrypted_id = {decrypted_id}")
            date_operation_remboursement_str = request.POST.get(f'date_operation_remboursement_id{uncrypted_id}') # récupérer la date de l'opération de règlement
            # messages.info(request, f"date_operation_remboursement_str = {date_operation_remboursement_str}")
            if not date_operation_remboursement_str:
                continue # si la date est null tout l'enregistrement est ignorée
            # Validation du format des dates
            try:
                date_operation_reglement = datetime.strptime(date_operation_remboursement_str, date_format).date()
            except ValueError:
                continue # si le format de la date est incorrecte tout l'enregistrement est ignorée
            
            # voire dans le template les conditions logiques 
            # entre accord_remboursement.status et la valeur du  nouv_status_accord

            nouv_status_accord = request.POST.get(f'nouv_status_accord_id{uncrypted_id}') # récupérer le nouv_status de l'opération de remboursement
            # messages.info(request, f"nouv_status_accord = {nouv_status_accord}") 
            
            if nouv_status_accord == 'Non défini':
                continue # si nouv_status_accord == 'Non défini' tout l'enregistrement est ignorée
            
            # Récupérer l'objet accord_remboursement correspondant si la date est définie 
            accord_remboursement = accord_remboursements.filter(id=decrypted_id).first()
            # messages.info(request, f"accord_remboursement_id = {accord_remboursement.id}") 
            # Récupérer les paiements liés à l'accord de règlement
            payments = Payment.objects.filter(id__in=DetailAccordRemboursement.objects.filter(accord=accord_remboursement).values_list('payment_id', flat=True))
            # messages.info(request, f"payments_first = {payments.first().id}")
            # si un des paiement est non approuvé par l'élève alors approved = False
            approved =True
            for payment in payments:
                if payment.reclamation: 
                    approved = False
                    break
            # messages.info(request, f"approved = {approved}")
            remboursement_requests.append((accord_remboursement.id, approved, date_operation_remboursement_str, nouv_status_accord ))

        # si aucune remboursement_requests n'est récupéré
        if not remboursement_requests:
            messages.error(request, "Pas d'enregistrement à modifier")
            return render(request, 'pages/admin_remboursement.html', context)
        
        request.session['remboursement_requests']= remboursement_requests
        return redirect('admin_remboursement_email')

    # Rendu de la page avec les emails filtrés
    return render(request, 'pages/admin_remboursement.html', context)

# @user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_remboursement_detaille(request):
    """
    Vue permettant d'afficher les détails d'un accord de remboursement.

    - Seuls les utilisateurs staff et actifs peuvent accéder à cette page.
    - Récupère l'accord de remboursement ainsi que ses détails associés.
    - Optimise les requêtes en utilisant `select_related` et `values_list`.
    """

    # 1. Récupération sécurisée de l'accord de règlement ou renvoi d'une erreur 404
    accord_id_uncrypted = request.session.get('accord_remboursement_id')
    accord_id_decrypted = decrypt_id(accord_id_uncrypted)
    if not accord_id_decrypted:
        messages.info(request, "L'ID de l'accord de remboursement n'a pas pu être décripter")
        return redirect('compte_administrateur')
    
    
    
    # 2. Gérer proprement les erreurs de base de données
    try:
        accord_remboursement = get_object_or_404(AccordRemboursement, id=accord_id_decrypted)
    except AccordRemboursement.DoesNotExist:
        logger.error(f"AccordRemboursement introuvable pour id={accord_id_decrypted}")
        return redirect('admin_remboursement')
    
    # 3. Récupération optimisée de l'email 
    email = Email_telecharge.objects.filter(id=accord_remboursement.email_id).only('sujet', 'text_email').first()
    texte_email = f"Sujet: {email.sujet}\nContenu: {email.text_email}" if email else "Pas de message"
    
    # 4. On récupère les données sans encrypt
    details_raw = DetailAccordRemboursement.objects.filter(
        accord=accord_remboursement
    ).select_related('payment').values_list(
        'payment__id', 'description', 'refunded_amount', 'payment__reclamation_id'
    )

    # 5. Ensuite on chiffre payment__id en Python
    details = [
        (
            encrypt_id(payment_id),  # On chiffre ici
            description,
            refunded_amount,
            reclamation_id
        )
        for payment_id, description, refunded_amount, reclamation_id in details_raw
    ]


    if 'btn_detaille_remboursement' in request.POST: # reste à terminer
        # Stockage l'ID de l'accord de règlement dans la session avant redirection
        request.session['accord_id'] = accord_id_decrypted
        return redirect('admin_remboursement_modifier')
    
    if request.POST: # achevé
        # Extraction de l'ID du paiement choisi dans le formulaire
        paiement_ids_uncrypted = [key.split('btn_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_paiement_id')]
        # Vérification du nombre d'IDs extraits
        if paiement_ids_uncrypted:
            if len(paiement_ids_uncrypted) == 1:  # Un seul ID trouvé, on le stocke en session
                eleve = Eleve.objects.filter(user=request.user).first() # Si le user est un élève
                if eleve:
                    paiement = Payment.objects.filter(id=decrypt_id(paiement_ids_uncrypted[0])).first() # il faut que le paiement est pour le professeur
                    if paiement and not Demande_paiement.objects.filter(id=paiement.model_id, user=eleve.user).exists(): # Si non il y a eu une manipulation des données du template
                        messages.error(request, f"le paiement sélectionné n'est pas attrubuté au professeur, paiement_id= {decrypt_id(paiement_ids_uncrypted[0])}")
                        return redirect('compte_prof')
                    
                request.session['payment_id'] = decrypt_id(paiement_ids_uncrypted[0])
                return redirect('admin_payment_demande_paiement')

    # Passage des données au template
    context = {
        'accord_remboursement': accord_remboursement,
        'texte_email': texte_email,
        'details': details,
    }
    
    return render(request, 'pages/admin_remboursement_detaille.html', context)


# Vérification des permissions : seul un administrateur actif peut accéder à cette vue
@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_remboursement_email(request):
    """
    Vue permettant d'afficher les détails d'un accord de remboursement.
    - Ajouter un texte explicatif, une date d'opération, un ID d'opération.
    - Récupère l'accord de remboursement ainsi que ses détails associés.
    - Envoie d'e-mail, enregistrement de l'e-mail, mise à jour du remboursement, mise à jour du paiement.
    - Affiche un message récapitulatif de l'enregistrement.
    """
    date_format = "%d/%m/%Y"  # Format de la date
    remboursement_requests = request.session.get('remboursement_requests')  # Les remboursements à modifier
    
    # 1. S'assurer qu'il existe des demandes de remboursement à traiter
    if not remboursement_requests:
        messages.info(request, "Il n'y a pas de remboursement à enregistrer.")
        logger.error(f"Une erreur est survenue: request.session.get('remboursement_requests')= {request.session.get('remboursement_requests')}")
        return redirect('compte_administrateur')
    
    accord_remboursement_modifs = []  # Données destinées au template

    for id, approved, date_operation_remboursement_str, nouv_status_accord in remboursement_requests:
        
        # 2. Gérer proprement les erreurs de base de données
        try:
            accord_remboursement = AccordRemboursement.objects.get(id=id)
        except AccordRemboursement.DoesNotExist:
            logger.error(f"AccordRemboursement introuvable pour id={id}")
            return redirect('admin_remboursement')

        date_operation_remboursement = datetime.strptime(date_operation_remboursement_str, date_format).date()
        
        # Mise en forme du texte de l'e-mail et du sujet
        text_email = ""
        sujet = f"Votre accord de remboursement pour le {accord_remboursement.due_date.strftime('%d/%m/%Y')} d'un montant de {accord_remboursement.total_amount:.2f}€ est "
        
        if nouv_status_accord == "in_progress":
            sujet += "en cours"
            text_email = (
                f"Un transfert bancaire le {date_operation_remboursement.strftime('%d/%m/%Y')} d'un montant de "
                f"{accord_remboursement.total_amount:.2f}€, conformément à votre accord de remboursement pour "
                f"l'échéance du {accord_remboursement.due_date.strftime('%d/%m/%Y')}, est en attente de confirmation "
                f"par la banque. Nous restons à votre disposition pour toute information complémentaire et vous "
                f"remercions de votre confiance."
            )
        elif nouv_status_accord == "completed":
            sujet += "réalisé"
            text_email = (
                f"Une transaction d'un montant de {accord_remboursement.total_amount:.2f}€ a été créditée sur votre "
                f"compte, conformément à votre accord de remboursement pour l'échéance du "
                f"{accord_remboursement.due_date.strftime('%d/%m/%Y')}. Nous restons à votre disposition pour toute "
                f"information complémentaire et vous remercions de votre confiance."
            )
        elif nouv_status_accord == "canceled":
            sujet += "annulé"
            text_email = (
                f"Nous regrettons de vous informer que votre accord de remboursement pour le "
                f"{accord_remboursement.due_date.strftime('%d/%m/%Y')}, d'un montant de "
                f"{accord_remboursement.total_amount:.2f}€, a été annulé.\n(Pour plus de détails, voir le texte explicatif.)\n"
                f"Nous vous prions de nous excuser pour ce désagrément et restons à votre disposition pour toute "
                f"information complémentaire. Nous vous remercions de votre compréhension et de votre confiance."
            )
        elif nouv_status_accord == "invalid":
            sujet += "non validé"
            text_email = (
                f"Nous regrettons de vous informer que votre accord de remboursement pour le "
                f"{accord_remboursement.due_date.strftime('%d/%m/%Y')}, d'un montant de "
                f"{accord_remboursement.total_amount:.2f}€, n'a pas été validé en raison d'un incident survenu lors "
                f"de l'initiation de la transaction bancaire.\n(Pour plus de détails, voir le texte explicatif.)\n"
                f"Nous vous prions de nous excuser pour ce désagrément et restons à votre disposition pour toute "
                f"information complémentaire. Nous vous remercions de votre compréhension et de votre confiance."
            )

        accord_remboursement_modifs.append((
            encrypt_id(id), accord_remboursement, date_operation_remboursement,
            nouv_status_accord, approved, sujet, text_email
        ))

    context = {
        'accord_remboursement_modifs': accord_remboursement_modifs,
    }

    if 'btn_accord_enregistrement' in request.POST:
        # 1. Extraire les IDs sélectionnés depuis les clés POST nommées 'sujet_<enc_id>'
        selected_enc_ids = [key.split('_', 1)[1] for key in request.POST if key.startswith('sujet_')]

        if not selected_enc_ids:
            messages.error(request, "Aucun accord de remboursement sélectionné.")
            logger.error(f"Erreur: [key.split('_', 1)[1] for key in request.POST if key.startswith('sujet_')] = {[key.split('_', 1)[1] for key in request.POST if key.startswith('sujet_')]}")
            return redirect('admin_remboursement')

        # 2. Préparer un mapping pour accéder rapidement aux modifications par ID
        modifs_dict = {
            decrypt_id(id): (accord, date_op, new_status, approved, subject, text)
            for id, accord, date_op, new_status, approved, subject, text in accord_remboursement_modifs
        }  # Utilisation de decrypt_id car le cryptage change à chaque soumission

        total_selected = len(selected_enc_ids)
        processed = 0

        # 3. Parcourir chaque ID encodé sélectionné
        for enc_id in selected_enc_ids:

            # En cas de corruption de POST, ça plantera.
            try:
                real_id = decrypt_id(enc_id)
            except Exception as e:
                logger.error(f"Erreur lors du decrypt_id de {enc_id}: {e}")
                return redirect('compte_administrateur')
            
            # c'est un cas d'erreur qui ne doit pas éxister mais il ne bloc pas
            if real_id not in modifs_dict:
                logger.error(f"enc_id = {enc_id} not in modifs_dict = {modifs_dict}, c'est un cas d'erreur qui ne doit pas éxister mais il ne bloc pas")
                continue  
            
            # Récupération des données associées à l'accord
            accord, date_op, new_status, approved, subject, base_text = modifs_dict[real_id]

            # 4. Ignorer si le statut n'a pas changé
            if accord.status == new_status:
                logger.error(f"Statut inchangé pour l'accord ID : ancien_tatut = {accord.status} new_status = {new_status}, c'est un cas d'erreur qui ne doit pas éxister")
                continue # c'est un cas d'erreur qui ne doit pas éxister

            processed += 1
            msg = ""  # Message de succès

            # 5. Construire le contenu de l'e-mail
            extra_text = request.POST.get(f'text_plus_email_{enc_id}', '')
            email_body = f"{base_text}\n{extra_text}"
            sender = accord.admin_user.email
            recipient_list = ['prosib25@gmail.com', accord.eleve.user.email]

            # 6. Valider les adresses e-mail
            try:
                validate_email(sender)
            except ValidationError:
                messages.error(request, f"E-mail expéditeur invalide : {sender}")
                logger.error(f"email non valide: {sender}")
                # Erreur ignorée volontairement

            invalid_dest = False
            for dest in recipient_list:
                try:
                    EmailValidator()(dest)
                except ValidationError:
                    messages.error(request, f"E-mail destinataire invalide : {dest}")
                    logger.error(f"email non valide: dest = {dest}")
                    invalid_dest = True

            # 7. Envoyer l'e-mail si tous les destinataires sont valides
            if not invalid_dest:
                try:
                    send_mail(subject, email_body, sender, recipient_list, fail_silently=False)
                    msg += "L'e-mail a été envoyé avec succès.\n"
                except Exception as e:
                    messages.error(request, f"Erreur lors de l'envoi de l'e-mail : {e}")
                    logger.error(f"Erreur lors de l'envoi de l'e-mail : {e}")
                    # Erreur ignorée volontairement

            # 8. Enregistrer l'e-mail en base de données
            mail_record = Email_telecharge.objects.create(
                user=request.user,
                email_telecharge=sender,
                sujet=subject[:255],  # Limiter à 255 caractères
                text_email=email_body,
                user_destinataire=accord.eleve.user.id,
            )
            msg += "E-mail enregistré en base.\n"

            # 9. Mettre à jour l'accord de remboursement
            accord.email_id = mail_record.id
            accord.status = new_status

            # 10. Si accord réalisé, ajouter les transferts et mettre à jour les paiements liés
            if new_status == 'completed':
                messages.info(request, f"new_status = {new_status}")
                date_str = request.POST.get(f'date_operation_{enc_id}', '')
                messages.info(request, f"date_str = {date_str} ")
                try:
                    accord.date_trensfere = datetime.strptime(date_str, '%d/%m/%Y').date()
                    messages.info(request, f"accord.date_transfere = {datetime.strptime(date_str, '%d/%m/%Y').date()} ")
                except ValueError:
                    logger.warning(f"accord.date_transfere: datetime.strptime(date_str, '%d/%m/%Y').date() = {datetime.strptime(date_str, '%d/%m/%Y').date()}")
                    accord.date_trensfere = date.today()  # Date actuelle si la date saisie est invalide
                    messages.info(request, f"date_str = {date.today()} ")

                accord.transfere_id = request.POST.get(f'operation_{enc_id}', '')

                # Mise à jour des paiements associés
                payment_ids = (
                    DetailAccordRemboursement.objects
                    .filter(accord=accord)
                    .values_list('payment_id', flat=True)
                )
                Payment.objects.filter(id__in=payment_ids).update(
                    accord_remboursement_id=accord.id,
                    remboursement_realise=1
                )
                msg += "Mise à jour des paiements effectuée.\n"

            accord.save()
            msg += "Accord de remboursement mis à jour."
            messages.success(request, msg)
            
        # Gestion de la session après traitement
        request.session.pop('remboursement_requests', None)

        # 11. Bilan des traitements
        if processed == 0:
            messages.info(request, "Aucun accord modifié.")
        elif processed < total_selected:
            ignored = total_selected - processed
            messages.info(request, f"{ignored} accord(s) ignoré(s) (statut inchangé ou erreur).")
            logger.error(f"{ignored} accord(s) ignoré(s) (statut inchangé ou erreur). sur {total_selected} remboursement(s) en total")

        return redirect('admin_payment_eleve_remboursement')

    return render(request, 'pages/admin_remboursement_email.html', context)

@user_passes_test(is_admin_active, login_url='/login/')
def admin_remboursement_modifier(request):
    """
    Vue d'administration permettant d'afficher les détails du réglement d'un professeur,
    de modifier l'enregistrement.
    Accessible uniquement aux administrateurs actifs.
    """

    date_format = "%d/%m/%Y" # Format date

    # Récupération sécurisée de l'accord de règlement ou renvoi d'une erreur 404
    accord_id = request.session.get('accord_id')

    # 1. Condition nécessaire de l'activation du template
    if not accord_id:
        messages.error(request, "Il n'y a pas de remboursement à modifier")
        return redirect('compte_administrateur')
    


    # 2. Gérer proprement les erreurs de base de données
    accord_remboursement = AccordRemboursement.objects.filter(id=accord_id).first()
    if not accord_remboursement:
        logger.error(f"AccordRemboursement introuvable pour id={accord_id}")
        return redirect('admin_remboursement')
    
    
    
    # 3. Récupération optimisée de l'email pour le template
    email = Email_telecharge.objects.filter(id=accord_remboursement.email_id).only('sujet', 'text_email').first()
    texte_email = f"Sujet: {email.sujet}\nContenu: {email.text_email}" if email else "Pas de message"
    
    # 4. Récupération optimisée des détails de l'accord, avec accès direct aux attributs nécessaires pour le template
    detailles_data = list(
        DetailAccordRemboursement.objects
        .filter(accord=accord_remboursement)
        .select_related('payment')  # Optimisation pour éviter des requêtes supplémentaires
        .values_list('payment__id', 'description', 'refunded_amount', 'payment__reclamation_id')
    )

    # 4.1 Extraction des données pertinentes : seulement l'ID du paiement et la description
    detailles = [(encrypt_id(payment_id), description, refunded_amount) for payment_id, description, refunded_amount, _ in detailles_data]


    # 5. récupérer les paiement liés à l'accord de remboursement pour le template admin_accord_remboursement_modifier
    ancien_payment_accords = [detail[0] for detail in detailles]

    # 6. Récupérer les paiement réalisés et non affectés à des accords de règlement réalisé ou à des remboursements
    paiements_sans_accord=[]
    # Récupération de l"élève concerné
    eleve = AccordRemboursement.objects.filter(id=accord_id).first().eleve

    # Récupération des demandes de paiement non réglées pour l'élève sélectionné
    demande_paiements = Demande_paiement.objects.filter(
        eleve=eleve,
        reglement_realise=False,
        payment_id__isnull=False
    )
    for demande_paiement in demande_paiements:
        # Récupération des paiements non encore accordés et non réalisés
        payment = Payment.objects.filter(
            accord_remboursement_id=None,  # Aucun accord de règlement associé
            remboursement_realise=False, # le remboursement n'est pas realisé pour plus de sécurité
            reglement_realise=False,  # Paiements non encore réglés
            reclamation__isnull=False, # Un remboursement n’est possible que pour les paiements réclamés par les élèves.
            model='demande_paiement',
            model_id=demande_paiement.id  # Filtrer uniquement les paiements du professeur sélectionné
        ).first()
        if not payment: continue
        description="Elève: " + demande_paiement.eleve.user.first_name + " " + demande_paiement.eleve.user.last_name + ", Date paiement: " + payment.date_creation.strftime('%d/%m/%Y') + ", Montant payé: " + str(payment.amount) + "€" if payment else ""
        refunded_amount=payment.amount  if payment else 0
        paiements_sans_accord.append((encrypt_id(payment.id) if payment else 0, description, refunded_amount, payment.reclamation if payment else ""))
    

    # Vérification si le formulaire a été soumis pour accorder un remboursement
    if 'btn_enr' in request.POST: # la modification de l'accord de remboursement est activée

        # Récupération des paiements cochés dans le formulaire (anciens ou / et nouvaux)
        encrypted_payment_keys = [key.split('accord_')[1] for key in request.POST.keys() if key.startswith('accord_')]

        

        # Vérification si au moins un paiement a été sélectionné
        if not encrypted_payment_keys:
            messages.error(request, "Veuillez sélectionner au moins un paiement.")
            return redirect('admin_remboursement_modifier')
        
        # récupérer la date de remboursement
        date_remboursement_str = request.POST.get('date_echeance')  # Date d’échéance
        # Conversion de la date de remboursement en objet datetime si possible
        try:
            date_remboursement = datetime.strptime(date_remboursement_str, date_format).date()
        except ValueError:
            messages.error(request, "le format de la date de remboursement est incorrecte")
            return redirect('admin_remboursement_modifier')

        
        
        payment_modifier = []
        for key in encrypted_payment_keys:
            
            # valider la non corruption du criptage
            try:
                decrypted_key = decrypt_id(key)
            except Exception as e:
                logger.error(f"Erreur lors du decrypt_id de {key}: {e}")
                return redirect('compte_administrateur')
            
            # éxtraire le paiement correspondant
            paiement = Payment.objects.filter(id=decrypted_key).first()
            if not paiement:
                return redirect('admin_remboursement_modifier')

            # Vérification que la date de règlement est au moins 7 jours après la date de création du paiement
            if (paiement.date_creation.date() + timedelta(days=7)) > date_remboursement:
                date_min = paiement.date_creation.date() + timedelta(days=8)
                messages.info(
                    request,
                    f"La date de remboursement ({date_remboursement}) doit être au moins 7 jours après "
                    f"la date de création du paiement ({paiement.date_creation.date()}).<br>"
                    "Modifiez la date de remboursement. <br>"
                    f"La date minimum est: {date_min}"
                )
                return redirect('admin_remboursement_modifier')

            # éxtraire le remboursement correspondant
            refunded_amount = request.POST.get(f'refunded_amount_{key}', '')

            # Suppression du symbole "€" et des espaces autour (si présents)
            refunded_amount_str = refunded_amount.replace('€', '').replace(',', '.').strip()

            # validation du format du montant de remboursement
            try:
                montant_decimal = Decimal(refunded_amount_str)
            except InvalidOperation:
                messages.error(request, f"Le montant: {refunded_amount_str} est invalide. Veuillez entrer un montant correct.")
                logger.error(f"Le montant {refunded_amount_str} est invalide. Veuillez entrer un montant correct.")
                return redirect('admin_remboursement_modifier')

            # vaidation du montant de remboursement
            if montant_decimal > paiement.amount:
                messages.error(request, f"Le montant du remboursement ({montant_decimal}) ne peut pas dépasser le montant initial payé ({paiement.amount}).")
                logger.error(f"Le montant du remboursement ({montant_decimal}) ne peut pas dépasser le montant initial payé ({paiement.amount}).")
                return redirect('admin_remboursement_modifier')
            
            payment_modifier.append((paiement.id , refunded_amount_str ))
        


        # Stockage des paiements validés dans la session avant redirection
        request.session['payment_modifier'] = payment_modifier

        # Stockage de la date de règlement dans la session avant redirection
        request.session['date_remboursement_str'] = date_remboursement_str

        # Stockage l'ID de l'élève dans la session avant redirection
        request.session['eleve_id'] = eleve.id

        # Stockage l'ID de l'accord de règlement dans la session avant redirection
        request.session['accord_id'] = accord_id

        # Stockage le statut de l'accord de règlement dans la session avant redirection
        request.session['status'] = request.POST.get('status', '')

        # Stockage le statut de l'accord de règlement dans la session avant redirection (pour mettre à jour les paiements)
        request.session['ancien_payment_accords'] = ancien_payment_accords

        # Stockage la date de transfère dans la session avant redirection 
        request.session['date_trensfere'] = request.POST.get('date_trensfere', '')

        # Stockage l'ID de transfère dans la session avant redirection 
        request.session['transfere_id'] = request.POST.get('transfere_id', '')

        return redirect('admin_accord_remboursement_modifier')

    # Passage des données au template
    context = {
        'accord_remboursement': accord_remboursement,
        'texte_email': texte_email,
        'detailles': detailles,
        'paiements_sans_accord': paiements_sans_accord,
        'date_now':timezone.now().date(), # valeur par défaut pour date transfère
    }


    return render(request, 'pages/admin_remboursement_modifier.html', context)




@user_passes_test(lambda u: u.is_staff and u.is_active, login_url='/login/')
def admin_accord_remboursement_modifier(request):
    """
    Modifier les accords de règlement pour le professeur 
    (même si le statut est réalisé pour que l'intervention de 
    l'administrateur soit sans limite),
    envoie un email pour le professeur et l'enregistrer
    en fin la mise à jour des paiements selon le statut initial et final
    """
    
    date_format = "%d/%m/%Y" # format de la date
    msg = "" # pour grouper les messages info dans un message final
    
    # Récupérer des paramètres de la session
    payment_requests = request.session.get('payment_modifier')
    date_remboursement_str = request.session.get('date_remboursement_str')
    accord_id = request.session.get('accord_id')
    eleve_id = request.session.get('eleve_id')
    status = request.session.get('status')
    status_mapping = {
        'pending': "En attente",
        'in_progress': "En cours",
        'completed': "Réalisé",
        'invalid': "Invalide",
    }

    status_label = status_mapping.get(status, "Annulé") #par défaut c'est Annulé

    date_trensfere = request.session.get('date_trensfere')
    transfere_id = request.session.get('transfere_id')
    ancien_payment_accords = request.session.get('ancien_payment_accords')

    # Condition nécessaire de l'activation du template
    if not accord_id:
        messages.error(request, "Il n'y a pas de règlement à enregistrer")
        return redirect('compte_administrateur')

    # Récupérer l'élève ou renvoyer une erreur 404 s'il n'existe pas
    eleve = get_object_or_404(Eleve, id=eleve_id)

    # Récupérer l'ancien l'accord de règlement ou renvoyer une erreur 404 s'il n'existe pas
    accord_remboursement = get_object_or_404(AccordRemboursement, id=accord_id)
    
    # Récupérer la date de règlement
    try:
        date_remboursement = datetime.strptime(date_remboursement_str, date_format).date()
    except ValueError:
            messages.error(request, f"Le format date de règlement: {date_remboursement_str} n'est pas valide le format doit être jj/mm/aaaa")
            
            # Stockage l'ID de l'accord de règlement dans la session avant redirection
            request.session['accord_id'] = accord_id
            return redirect('admin_reglement_modifier')
    
    if not payment_requests:
        messages.error(request, "Il n'y a pas de règlement à enregistrer")
        return redirect('admin_payment_accord_reglement')
    
    payments=[] # pour la liste des paiements des élèves: date_versement, payment, user_eleve

    for payment_id, refunded_amount_str in payment_requests: # étier les données de la session
        payment = Payment.objects.filter(id=payment_id).first()
        # # c'est une requette qui lie la table Demande_paiement avec Eleve avec User
        # demande_paiement = Demande_paiement.objects.select_related('eleve__user').filter(id=payment.model_id).first()
        # if not demande_paiement: continue  # Ignorer les paiements sans demande associée (non nécessaire mais par prudence car à chaque paiement correspond un demande préalable)
        # user_eleve = demande_paiement.eleve.user # pour le template
        user_eleve = eleve.user # l'élève existe déjà dans le request
        payments.append(( payment, user_eleve, refunded_amount_str))  # pour le template et le calcul des totaux

    totaux_payement=0
    totaux_versement=0
    for  payment, user_eleve, refunded_amount_str in payments:
        totaux_payement += payment.amount
        totaux_versement += Decimal(refunded_amount_str)
    

    # préparer l'envoie de l'email
    user = request.user # admin
    email_user = user.email # email admin
    email_destinataire = eleve.user.email # email destinatère (professeur)
    destinations = ['prosib25@gmail.com', email_destinataire] # 'prosib25@gmail.com'à enlever dans le site production
    
    # Validation des emails dans destinations
    for destination in destinations:
        email_validator = EmailValidator() #inicialisation de l'objet EmailValidator
        try:
            email_validator(destination)
        except ValidationError:
            messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
            # même s'il y a erreur l'enregistrement continu car l'envoi de l'email n'est pas obligatoire
    
    # mise en forme du text_email et du sujet de l'email
    texte = f"\nRèglement prévu le:\t\t{date_remboursement.strftime('%d/%m/%Y')}\t\tEléve: {eleve.user.first_name} {eleve.user.last_name}\n\nListe des paiements des élèves:\nDate paiement\t\t\t\tPaiement\t\t\tRemboursement\n"
    for  payment, user_eleve, refunded_amount_str in payments:
        texte += f"{payment.date_creation.strftime('%d/%m/%Y')}\t\t\t\t\t{payment.amount:.2f}€\t\t\t\t\t{refunded_amount_str}\n"
    texte_totaux = (
        f"\nMontant payé           Montant à régler\n"
        f"{totaux_payement:.2f}€                     {totaux_versement:.2f}€\n"
        f"Statut accord de règlement : <strong>{status_label}</strong>"
    )

    if status_label=="Réalisé": texte_totaux += f"  --  Nouvelle date de transfère: {date_trensfere}  -- Nouveau ID de transfère: {transfere_id}"
    texte_fin= texte + texte_totaux
    sujet = f"Accord de remboursement de: {totaux_payement:.2f}€, pour le: {date_remboursement}"

    if 'btn_accord_enregistrement' in request.POST:  # à terminer 04/05/2025
        #envoie de l'email
        text_email_plus = request.POST.get('text_email_plus','')
        text_email = f"{texte_fin}\n\n{text_email_plus}"

        # Validation des emails dans destinations
        for destination in destinations:
            email_validator = EmailValidator() #inicialisation de l'objet EmailValidator
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
            msg += str(f"L'email a été envoyée avec succès relatif à l'accord de règlement du {date_remboursement}.\n")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
        
        # enregistrement de l'email
        email_telecharge = Email_telecharge(
            user=user, 
            email_telecharge=email_user, 
            text_email=text_email, 
            user_destinataire=eleve.user.id,
            sujet=sujet
        )
        email_telecharge.save()
        msg += str(f"L'email a été enregistré avec succès relatif à l'accord de règlement du {date_remboursement}.\n")


        # Mise à jour de accord de règlement
        accord_remboursement.admin_user=request.user
        accord_remboursement.total_amount=totaux_versement
        accord_remboursement.email_id=email_telecharge.id
        accord_remboursement.status=status
        accord_remboursement.due_date=date_remboursement
        if status=="completed":
            accord_remboursement.date_trensfere=datetime.strptime(date_trensfere, date_format).date()
            accord_remboursement.transfere_id=transfere_id
        # cas du status Réaliser n'est pas traiter même dans le cas de règlement?
        accord_remboursement.save()
        msg += str(f"Mise à jour de accord de remboursement du {date_remboursement}.\n")
        
        # Avant la suppression des anciens détailles des accords de règlements 
        # il faux mettre à jour les enregisrements de Payment liés au ancien détaille de remboursement
        # comme s'il n'y a pas eu d'accord de remboursement
        for payment_id in ancien_payment_accords:
            payment_ancien = Payment.objects.filter(id=decrypt_id(payment_id)).first()
            if payment_ancien:
                payment_ancien.accord_remboursement_id=None
                payment_ancien.remboursement_realise=False
                payment_ancien.save()
                msg += str(f"Mettre à jour les anciens enregisrements de Payment.\n")

        # Mise à jour des détailles des accords de remboyrsements
        # Suppression des anciens détailles des accords de remboursement
        DetailAccordRemboursement.objects.filter(accord=accord_id).delete()
        msg += str(f"Suppression des anciens détailles des accords de remboursements.\n")

        # Ajout des nouveaux détailles des accords de règlements
        for  payment, user_eleve, refunded_amount in payments:
            detaille_accord_remboursement = DetailAccordRemboursement(
                accord=accord_remboursement, 
                payment=payment, 
                refunded_amount=Decimal(refunded_amount) , 
                description="Elève: " + user_eleve.first_name + " " + user_eleve.last_name +
                            ", Date paiement: " + payment.date_creation.strftime('%d/%m/%Y') +
                            ", Montant payé: " + str(payment.amount) + "€"
            )
            detaille_accord_remboursement.save()
            msg += str(f"Ajout des nouveaux détailles des accords de remboursement id={detaille_accord_remboursement.id}.\n")

            # Mise à jour de l'enregistrement payment
            payment.accord_reglement_id=accord_remboursement.id
            if status == "completed": payment.remboursement_realise=True
            payment.save()
            msg += str(f"Mise à jour de l'enregistrement payment id={payment.id}.\n")

        messages.success(request, msg.replace("\n", "<br>") )

        # Vider les paramètres de la session
        keys_to_delete = [
            'payment_modifier', 'date_remboursement_str', 'accord_id', 'prof_id', 
            'status', 'date_trensfere', 'transfere_id', 'ancien_payment_accords'
        ]

        for key in keys_to_delete:
            if key in request.session:
                del request.session[key]

        return redirect('compte_administrateur')

    # Contexte à passer au template
    context = {
        'eleve': eleve,
        'payments': payments,
        'totaux_payement': totaux_payement,
        'totaux_versement': totaux_versement,
        'texte_fin': texte_fin,
        'date_remboursement': date_remboursement,
        'status': status_label,
        'accord_remboursement': accord_remboursement,
        'transfere_id': transfere_id,
        'date_trensfere': date_trensfere,
    }

    # Rendu de la page avec les données filtrées
    return render(request, 'pages/admin_accord_remboursement_modifier.html', context)