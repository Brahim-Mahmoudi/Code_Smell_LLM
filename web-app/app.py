# app.py
from flask import Flask, render_template, request, send_file, redirect
from pathlib import Path
import json
import shutil
import tempfile
import os
from specdetect4llm import discover_available_rules, run_analysis, RULES_ROOT

app = Flask(__name__)
# Taille maximale du fichier uploadé (ex: 32MB)
# app.py
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

@app.route('/', methods=['GET', 'POST'])
def index():
    available_rules = discover_available_rules(RULES_ROOT)
    error = None
    
    if request.method == 'POST':
        # 1. Vous définissez zip_file ici
        zip_file = request.files.get('project_zip') 
        # ...2. Récupérer les règles sélectionnées
        selected_rules = request.form.getlist('rules')
        
        # 3. Traiter le fichier dans un répertoire temporaire
        temp_dir = None
        try:
            # Crée un répertoire temporaire
            temp_dir = tempfile.TemporaryDirectory()
            zip_path = Path(temp_dir.name) / "project.zip"
            zip_file.save(zip_path)

            project_dir = Path(temp_dir.name) / "project_extracted"
            shutil.unpack_archive(zip_path, project_dir)

            # 4. Lancer l'analyse
            print(f"Lancement de l'analyse sur {project_dir}...")
            
            results, total_files, summary = run_analysis(project_dir, selected_rules)
            
            results_json_str = json.dumps(results, indent=2, ensure_ascii=False)
            
            # 5. SUCCÈS : Retourne immédiatement la page de résultats
            # IMPORTANT : Le nettoyage du temp_dir doit être fait AVANT de retourner
            temp_dir.cleanup() 
            
            return render_template(
                'results.html',
                results=results,
                total_files=total_files,
                summary=summary,
                project_name=zip_file.filename,
                results_json=results_json_str
            )

        except shutil.ReadError:
            error = "Erreur: Le fichier n'est pas un fichier ZIP ou TAR valide."
            # Pas de return ici, on laisse le flux continuer jusqu'à la fin du POST.
        except Exception as e:
            # Gérer toute autre erreur (erreur d'analyse, d'écriture, etc.)
            error = f"Erreur d'analyse: {e}"
            # Pas de return ici, on laisse le flux continuer jusqu'à la fin du POST.
        finally:
            # Assurez-vous que le répertoire temporaire est nettoyé si l'analyse a échoué
            # et qu'il n'a pas été nettoyé dans le bloc try (en cas de succès)
            if temp_dir and Path(temp_dir.name).exists(): 
                 # Utilisation de Path(temp_dir.name).exists() pour éviter un crash si cleanup() a déjà été appelé
                 try: 
                    temp_dir.cleanup()
                 except Exception:
                    pass # Ignore l'erreur de nettoyage s'il est déjà fait ou si le chemin n'existe plus

        # SI nous arrivons ici, C'EST QUE L'ANALYSE A ÉCHOUÉ (error est rempli)
        # On retourne l'index AVEC le message d'erreur.
        if error:
            return render_template('index.html', rules=available_rules, error=error)
                
    # Ce return est pour les requêtes GET initiales (ou si le POST n'a pas eu lieu)
    return render_template('index.html', rules=available_rules, error=error)

# Route pour l'export JSON (inchangée)
@app.route('/download_json', methods=['POST'])
def download_json():
    # ... (le code de download_json reste le même que dans la réponse précédente) ...
    results_json = request.form['results_json']
    
    temp_json_path = Path(tempfile.gettempdir()) / "specdetect_results.json"
    with open(temp_json_path, 'w', encoding='utf-8') as f:
        f.write(results_json)

    return send_file(
        temp_json_path,
        as_attachment=True,
        download_name='specdetect_results.json',
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(debug=True)