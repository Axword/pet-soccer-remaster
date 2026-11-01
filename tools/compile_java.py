"""Compile only original mod Java helpers against an external game class path."""
from pathlib import Path
import argparse, subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True, help='Read-only original Pet Soccer directory')
    parser.add_argument('--classpath', type=Path, required=True, help='Locally reconstructed mod code.pak')
    parser.add_argument('--ecj', type=Path, required=True, help='External Eclipse compiler JAR supporting target1.3')
    parser.add_argument('--output', type=Path, default=ROOT/'build/java')
    args = parser.parse_args()
    game = args.game.resolve()
    output = args.output.resolve()
    if output.is_relative_to(game):
        parser.error('The output must be outside the original game directory')
    java = game/'jre/bin/java.exe'
    boot = game/'jre/lib/rt.jar'
    for path in [java, boot, args.classpath, args.ecj]:
        if not path.is_file(): parser.error('Missing required external file: '+str(path))
    output.mkdir(parents=True, exist_ok=True)
    command = [str(java), '-cp', str(args.ecj.resolve()),
               'org.eclipse.jdt.internal.compiler.batch.Main', '-proc:none', '-encoding', 'UTF-8',
               '-source', '1.3', '-target', '1.3', '-bootclasspath', str(boot),
               '-classpath', str(args.classpath.resolve()), '-d', str(output)]
    command += [str(p) for p in sorted((ROOT/'src/java').glob('*.java'))]
    subprocess.run(command, check=True, cwd=ROOT)
    print('Compiled mod helpers into', output)

if __name__ == '__main__': main()
