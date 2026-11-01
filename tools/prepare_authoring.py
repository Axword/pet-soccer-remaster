"""Copy development recipes into an isolated build workspace before running Blender."""
from pathlib import Path
import argparse, os, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=ROOT/'build/authoring')
    p.add_argument('--base-game',type=Path,help='Optional external original game; only robot reference mesh/INI are copied')
    p.add_argument('--gothic-game',type=Path)
    p.add_argument('--witcher-game',type=Path)
    p.add_argument('--recipe',help='Relative .py path inside authoring/recipes')
    p.add_argument('--blender',type=Path,help='External Blender executable; needed only with --run')
    p.add_argument('--run',action='store_true')
    a=p.parse_args()
    workspace=a.workspace.resolve()
    if not workspace.is_relative_to((ROOT/'build').resolve()):p.error('Workspace must be inside this checkout\'s ignored build directory')
    recipes=ROOT/'authoring/recipes'
    workspace.mkdir(parents=True,exist_ok=True)
    count=0
    for source in recipes.rglob('*.py'):
        target=workspace/source.relative_to(recipes);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target);count+=1
    if a.base_game:
        base=a.base_game.resolve()
        for parent in [workspace,workspace/'remaster/factions']:
            source=base/'Data/Meshes/Animals/robocik.3da'
            if not source.is_file():p.error('Missing original robot reference mesh: '+str(source))
            shutil.copyfile(source,parent/'robot-reference.3da')
            ini=base/'Data/Meshes/Animals/robocik.ini'
            if ini.is_file():
                target=parent/'PetSoccer-Steve-Test/Data/Meshes/Animals';target.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ini,target/'robocik.ini')
    print('Prepared',count,'source recipes in',workspace)
    print('Proprietary source models/textures/clips must be supplied locally as described in authoring/README.md.')
    if a.run:
        if not a.recipe or not a.blender or not a.blender.is_file():p.error('--run requires --recipe and --blender')
        recipe=(workspace/a.recipe).resolve()
        if not recipe.is_relative_to(workspace) or recipe.suffix!='.py' or not (recipes/a.recipe).is_file():p.error('Select a published recipe')
        environment=dict(os.environ,PETSOCCER_AUTHORING_WORKSPACE=str(workspace))
        for argument,key in [(a.base_game,'PETSOCCER_GAME_DIR'),(a.gothic_game,'GOTHIC_GAME_DIR'),(a.witcher_game,'WITCHER_GAME_DIR')]:
            if argument:environment[key]=str(argument.resolve())
        subprocess.run([str(a.blender.resolve()),'--background','--python',str(recipe)],env=environment,cwd=workspace,check=True)

if __name__=='__main__':main()
