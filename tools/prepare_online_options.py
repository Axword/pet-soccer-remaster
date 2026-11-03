"""Add the content toggle to an external pre-expansion options SCR with CRLF.

Only a fresh output file is written. The parser-compatible line ends are required;
an LF-only file can appear to load but create no controls in the legacy engine.
"""
from pathlib import Path
import argparse,re

def block(text,kind,identifier):
    match=re.search(r'\b'+kind+r'\([^\n]*"'+re.escape(identifier)+r'"[^\n]*\)',text)
    if not match:raise ValueError('Missing expected control: '+identifier)
    start,at=match.start(),text.index('{',match.end());depth=1;end=at+1
    while depth:
        if text[end]=='{':depth+=1
        if text[end]=='}':depth-=1
        end+=1
    return start,end,text[start:end]

def prepare(text):
    text=text.replace('\r\n','\n').replace('\r','\n')
    if 'CX_EXTRA_TEAMS' in text:raise ValueError('Content toggle already exists; use its verified output rather than patching twice')
    _,_,button=block(text,'Button','CX_RM')
    button=button.replace('"CX_RM"','"CX_EXTRA_TEAMS"')
    button=re.sub(r'Text\("[^"\n]*"\)','Text("Dodatkowe kluby: WYL.")',button)
    button=re.sub(r'LogicPos\([^\n]*\)','LogicPos(0.055,0.755)',button)
    button=re.sub(r'LogicSize\([^\n]*\)','LogicSize(0.42,0.055)',button)
    start,end,hint=block(text,'Static','CX_HINT')
    hint=re.sub(r'LogicPos\([^\n]*\)','LogicPos(0.05,0.825)',hint)
    hint=re.sub(r'LogicSize\([^\n]*\)','LogicSize(0.9,0.03)',hint)
    return (text[:start]+button+'\n\n '+hint+text[end:]).replace('\n','\r\n').encode('utf8')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.resolve()==a.input.resolve():p.error('Use a fresh output file')
    data=prepare(a.input.read_text('utf8'))
    assert b'\n' not in data.replace(b'\r\n',b'')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
    print('Wrote parser-compatible options script:',a.output)

if __name__=='__main__':main()
