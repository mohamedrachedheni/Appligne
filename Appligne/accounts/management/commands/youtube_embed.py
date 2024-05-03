# from googleapiclient.discovery import build
# from decouple import config

# # Récupération du mot de passe email depuis le fichier .env
# API_KEY = config('API_KEY')

# # Clé d'API YouTube, veuillez remplacer 'YOUR_API_KEY' par votre propre clé d'API
# api_key = API_KEY

# # Créer une instance de l'API YouTube Data
# youtube = build('youtube', 'v3', developerKey=api_key)

# def get_embed_code(video_id):
#     # Appel à l'API pour récupérer les détails de la vidéo
#     request = youtube.videos().list(
#         part='player',
#         id=video_id
#     )
#     response = request.execute()
    
#     # Extrait le code d'intégration de la réponse
#     embed_code = response['items'][0]['player']['embedHtml']
    
#     return embed_code

# # Utilisation de la fonction pour récupérer le code d'intégration d'une vidéo spécifique
# # video_id = '3jDV3XVZ6JM'  # ID de la vidéo YouTube
# # embed_code = get_embed_code(video_id)
# # print(embed_code)
