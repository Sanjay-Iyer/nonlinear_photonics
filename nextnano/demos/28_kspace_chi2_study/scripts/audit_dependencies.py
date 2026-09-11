"""Execute cached baseline/sweep with historical demo filesystem access blocked."""
from pathlib import Path
import ast
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chi2.artifacts import write_json
from chi2.studies import run_baseline,run_sweep


def main():
    attempts=[]
    repo=ROOT.parents[2]
    forbidden=[repo/'demo_results',ROOT.parent/'Demo26_Condensed',ROOT.parent/'Demo28']
    forbidden.extend(p for p in ROOT.parent.iterdir() if p.is_dir() and p!=ROOT and p.name[:1].isdigit())
    normalized=[str(p.resolve()).casefold() for p in forbidden]
    def guard(event,args):
        if event not in ('open','os.listdir','os.scandir') or not args or not isinstance(args[0],(str,bytes)):return
        p=str(Path(args[0]).resolve()).casefold()
        if any(p==f or p.startswith(f+'\\') or p.startswith(f+'/') for f in normalized):
            attempts.append(p);raise RuntimeError('Forbidden historical runtime dependency: '+p)
    sys.addaudithook(guard)
    imported=set()
    for path in (ROOT/'chi2').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node,ast.Import):imported.update(n.name.split('.')[0] for n in node.names)
            elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module:imported.add(node.module.split('.')[0])
    out=ROOT/'outputs/dependency_audit'
    # Deliberately separate output folders; historical regression data is vendored locally.
    a=run_baseline(out=out/'28A',make_plots=False)
    b=run_sweep(out=out/'28B',make_plots=False)
    external=[]
    for name,module in list(sys.modules.items()):
        f=getattr(module,'__file__',None)
        if f and str(repo).casefold() in str(f).casefold() and not str(Path(f).resolve()).casefold().startswith(str(ROOT).casefold()):
            external.append({'module':name,'file':f})
    report={'status':'PASS' if not attempts and not external else 'FAIL',
            'historical_access_attempts':attempts,'external_repository_imports':external,
            'absolute_import_roots':sorted(imported),'required_third_party':['numpy','scipy','matplotlib'],
            'test_only':['pytest'],'baseline_status':a['validation_status'],'sweep_status':b['validation_status'],
            'blocked_roots':forbidden,'historical_reference_policy':'Only package-local validation CSV/JSON read as regression references; no previous-demo code imports',
            'scope':'Runtime instrumented A/B; static import scan of all chi2 modules. Other study results have separate raw/code manifests.'}
    write_json(out/'metadata.json',report);print('Dependency audit:',report['status'])
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
