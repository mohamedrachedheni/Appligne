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
    help = "Affiche TOUTE l'arborescence du projet Django (sans filtrage) et l'exporte en PDF"

    def add_arguments(self, parser):
        parser.add_argument("--level", type=int, default=3, 
                           help="Profondeur d'affichage (par défaut 3)")
        parser.add_argument("--output", type=str, default="arborescence_complete", 
                           help="Nom du fichier de sortie (sans extension)")
        parser.add_argument("--format", type=str, choices=["txt","pdf"], default="pdf", 
                           help="Format de sortie : txt ou pdf (par défaut pdf)")

    def handle(self, *args, **options):
        root_dir = os.getcwd()
        level = options["level"]
        output_file = f"{options['output']}.{options['format']}"
        file_format = options["format"]

        # CONSTRUIRE L'ARBORESCENCE COMPLÈTE SANS AUCUN FILTRAGE
        tree = []
        for root, dirs, files in os.walk(root_dir):
            # NE PAS FILTRER LES DOSSIERS - TOUT INCLURE
            # On laisse dirs intact pour inclure tous les dossiers
            
            depth = root[len(root_dir):].count(os.sep)
            if depth > level:
                continue
                
            tree.append((depth, os.path.basename(root) or root_dir, True))
            
            # AJOUTER TOUS LES FICHIERS SANS FILTRAGE
            for f in files:
                tree.append((depth+1, f, False))

        # Export TXT
        if file_format == "txt":
            with open(output_file, "w", encoding="utf-8") as f:
                for depth, name, is_dir in tree:
                    indent = " " * 4 * depth
                    f.write(f"{indent}{name}/\n" if is_dir else f"{indent}{name}\n")
            self.stdout.write(self.style.SUCCESS(f"✅ Arborescence TXT complète enregistrée dans {output_file}"))
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
        hidden_style = ParagraphStyle(
            "HiddenStyle",
            parent=styles["Normal"],
            textColor=colors.gray,
            fontName="Helvetica-Oblique"
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
            ParagraphStyle("TOCLevel3", parent=styles["Normal"], 
                          leftIndent=60, spaceAfter=1, fontSize=8, 
                          textColor=colors.darkgreen),
        ]

        story = []
        # Titre du document
        story.append(Paragraph("📂 Arborescence COMPLÈTE du projet Django", title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Information
        story.append(Paragraph("<i>Tous les fichiers et dossiers sont affichés sans aucun filtrage</i>", styles["Italic"]))
        story.append(Spacer(1, 0.2*cm))
        
        # En-tête du sommaire
        story.append(Paragraph("<b>📑 Sommaire</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.3*cm))

        # Préparer les signets pour le contenu
        content_story = []
        for idx, (depth, name, is_dir) in enumerate(tree):
            indent = "&nbsp;" * 4 * depth
            is_hidden = name.startswith('.')
            
            if is_dir:
                bookmark_name = f"bookmark_{idx}"
                # Contenu avec ancre
                if is_hidden:
                    p = Paragraph(f'<a name="{bookmark_name}"/>{indent}📁 <font color="gray">{name}/</font>', hidden_style)
                else:
                    p = Paragraph(f'<a name="{bookmark_name}"/>{indent}📁 {name}/', folder_style)
                
                p.outlineLevel = str(depth)
                content_story.append(p)
                
                # Entrée cliquable dans le sommaire
                if depth < len(toc_styles):
                    toc_style = toc_styles[depth]
                else:
                    toc_style = toc_styles[-1]
                
                if is_hidden:
                    story.append(Paragraph(f'<link href="#{bookmark_name}">📁 <font color="gray">{name}/</font></link>', toc_style))
                else:
                    story.append(Paragraph(f'<link href="#{bookmark_name}">📁 {name}/</link>', toc_style))
            else:
                if is_hidden:
                    content_story.append(Paragraph(f'{indent}📄 <font color="gray">{name}</font>', hidden_style))
                else:
                    content_story.append(Paragraph(f"{indent}📄 {name}", normal_style))
            
            content_story.append(Spacer(1, 0.1*cm))

        # Séparer le sommaire du contenu
        story.append(PageBreak())
        story.extend(content_story)

        # Générer le PDF
        try:
            doc = MyDocTemplate(output_file, pagesize=A4)
            doc.multiBuild(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
            
            # Vérifier que le fichier a été créé
            if os.path.exists(output_file):
                # Statistiques
                dossier_count = sum(1 for item in tree if item[2])
                fichier_count = sum(1 for item in tree if not item[2])
                hidden_count = sum(1 for item in tree if item[1].startswith('.'))
                
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Arborescence PDF COMPLÈTE générée avec succès : {output_file}\n"
                    f"   - {dossier_count} dossiers\n"
                    f"   - {fichier_count} fichiers\n"
                    f"   - {hidden_count} éléments cachés\n"
                    f"   - Profondeur maximale: {level}\n"
                    f"   - Sommaire cliquable avec hiérarchie visuelle"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"❌ Erreur: Le fichier {output_file} n'a pas été créé."
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"❌ Erreur lors de la génération du PDF: {str(e)}"
            ))

"""
Les commandes:
python manage.py showalltree
python manage.py showalltree --output mon_projet
python manage.py showalltree --level 3
python manage.py showalltree --format txt
python manage.py showalltree --output structure_clean --level 2 --format txt
python manage.py showalltree --output equipe_version --level 2 --format pdf

"""