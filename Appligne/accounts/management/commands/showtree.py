import os
from django.core.management.base import BaseCommand
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

def add_page_number(canvas, doc):
    """Ajoute le numéro de page en bas de chaque page"""
    page_num = canvas.getPageNumber()
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(20*cm, 1*cm, f"Page {page_num}")

class MyDocTemplate(SimpleDocTemplate):
    """DocTemplate pour TOC cliquable et signets PDF"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bookmark_id = 0

    def afterFlowable(self, flowable):
        """Crée des signets PDF pour les paragraphes avec outlineLevel"""
        if isinstance(flowable, Paragraph) and hasattr(flowable, "outlineLevel"):
            text = flowable.getPlainText()
            level = int(flowable.outlineLevel)
            key = f"bookmark_{self._bookmark_id}"
            self._bookmark_id += 1
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=False)
            self.notify("TOCEntry", (level, text, self.page))

class Command(BaseCommand):
    help = "Affiche l'arborescence du projet Django et l'exporte en TXT ou PDF avec sommaire cliquable"

    def add_arguments(self, parser):
        parser.add_argument("--level", type=int, default=2, 
                           help="Profondeur d'affichage (par défaut 2)")
        parser.add_argument("--output", type=str, default="arborescence", 
                           help="Nom du fichier de sortie (sans extension)")
        parser.add_argument("--format", type=str, choices=["txt","pdf"], default="pdf", 
                           help="Format de sortie : txt ou pdf (par défaut pdf)")

    def handle(self, *args, **options):
        root_dir = os.getcwd()
        level = options["level"]
        output_file = f"{options['output']}.{options['format']}"
        file_format = options["format"]

        # Filtres pour une meilleure lisibilité
        ignore_dirs = {'__pycache__', '.git', '.vscode', '.idea', 
                      'node_modules', 'venv', 'env', 'static', 'media', 'migrations'}
        ignore_ext = {'.pyc', '.pyo', '.db', '.sqlite3', '.log', '.tmp'}

        # Construire l'arborescence filtrée
        tree = []
        for root, dirs, files in os.walk(root_dir):
            # Filtrer les dossiers à ignorer
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            depth = root[len(root_dir):].count(os.sep)
            if depth > level:
                continue
                
            tree.append((depth, os.path.basename(root) or root_dir, True))
            
            # Ajouter les fichiers filtrés
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in ignore_ext:
                    tree.append((depth+1, f, False))

        # Export TXT
        if file_format == "txt":
            with open(output_file, "w", encoding="utf-8") as f:
                for depth, name, is_dir in tree:
                    indent = " " * 4 * depth
                    f.write(f"{indent}{name}/\n" if is_dir else f"{indent}{name}\n")
            self.stdout.write(self.style.SUCCESS(f"✅ Arborescence TXT enregistrée dans {output_file}"))
            return

        # Export PDF avec sommaire cliquable
        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]
        folder_style = ParagraphStyle(
            "FolderStyle", 
            parent=styles["Normal"], 
            textColor=colors.darkblue, 
            fontName="Helvetica-Bold"
        )
        title_style = styles["Title"]
        
        # Styles hiérarchiques pour le sommaire
        toc_styles = [
            ParagraphStyle("TOCLevel0", parent=styles["Normal"], 
                          leftIndent=0, spaceAfter=5, fontSize=12, 
                          fontName="Helvetica-Bold", textColor=colors.darkblue),
            ParagraphStyle("TOCLevel1", parent=styles["Normal"], 
                          leftIndent=20, spaceAfter=3, fontSize=10, 
                          fontName="Helvetica-Bold", textColor=colors.navy),
            ParagraphStyle("TOCLevel2", parent=styles["Normal"], 
                          leftIndent=40, spaceAfter=2, fontSize=9, 
                          textColor=colors.darkcyan),
        ]

        story = []
        # Titre du document
        story.append(Paragraph("📂 Arborescence du projet Django", title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # En-tête du sommaire
        story.append(Paragraph("<b>📑 Sommaire</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.3*cm))

        # Préparer les signets pour le contenu
        content_story = []
        for idx, (depth, name, is_dir) in enumerate(tree):
            indent = "&nbsp;" * 4 * depth
            if is_dir:
                bookmark_name = f"bookmark_{idx}"
                # Contenu avec ancre
                p = Paragraph(f'<a name="{bookmark_name}"/>{indent}📁 {name}/', folder_style)
                p.outlineLevel = str(depth)
                content_story.append(p)
                
                # Entrée cliquable dans le sommaire
                if depth < len(toc_styles):
                    toc_style = toc_styles[depth]
                else:
                    toc_style = toc_styles[-1]
                    
                story.append(Paragraph(f'<link href="#{bookmark_name}">📁 {name}/</link>', toc_style))
            else:
                content_story.append(Paragraph(f"{indent}📄 {name}", normal_style))
            
            content_story.append(Spacer(1, 0.1*cm))

        # Séparer le sommaire du contenu
        story.append(PageBreak())
        story.extend(content_story)

        # Générer le PDF
        doc = MyDocTemplate(output_file, pagesize=A4)
        doc.multiBuild(story, onFirstPage=add_page_number, onLaterPages=add_page_number)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Arborescence PDF générée avec succès : {output_file}\n"
            f"   - Sommaire cliquable avec hiérarchie visuelle\n"
            f"   - {len([item for item in tree if item[2]])} dossiers\n"
            f"   - {len([item for item in tree if not item[2]])} fichiers"
        ))

"""
Les commandes:
python manage.py showtree
python manage.py showtree --output mon_projet
python manage.py showtree --level 3
python manage.py showtree --format txt
python manage.py showtree --output structure_clean --level 2 --format txt
python manage.py showtree --output equipe_version --level 2 --format pdf

"""