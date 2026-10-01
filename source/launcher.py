from pathlib import Path
import argparse
import json
import sys
import tempfile
from kks_installer._application import APP_VERSION
from kks_installer.manager import Manager
from kks_installer.packages import import_package
from kks_installer.platforms import discover


def main():
    parser=argparse.ArgumentParser(description='KKS Installer '+APP_VERSION+' — independent offline content packages')
    group=parser.add_mutually_exclusive_group()
    for name in ('check','install','repair','restore','recover','detect','verify-package','version'):
        group.add_argument('--'+name,action='store_true')
    parser.add_argument('--game',help='Folder containing Fallout76.exe')
    parser.add_argument('--package',help='Complete signed KKS content ZIP')
    parser.add_argument('package_path',nargs='?',help='A ZIP dropped onto the application or supplied at launch')
    parser.add_argument('--report',help='Write the result to this explicitly selected JSON path')
    args=parser.parse_args()
    try:
        package=args.package or args.package_path
        if args.package and args.package_path: raise ValueError('Select one content package at a time')
        if args.version: result={'application_version':APP_VERSION,'embedded_payload':False}
        elif args.detect: result={'installations':discover()}
        elif args.verify_package:
            if not package: raise ValueError('--package is required')
            with tempfile.TemporaryDirectory(prefix='kks-verify-') as cache:
                release=import_package(package,cache)
                result={'status':'verified','content':release.name,'manifest':release.manifest_digest,
                        'supported_build':release.data['supported_build'],'payload_files':len(release.files)}
        else:
            action=next((x for x in ('check','install','repair','restore','recover') if getattr(args,x)),None)
            if action is None:
                from kks_installer.ui import launch
                launch(package,args.game); return 0
            if not args.game: raise ValueError('--game is required for command-line operations')
            logs=[]; manager=Manager(args.game,logs.append)
            if action=='check':
                # Check never creates a game-side cache or performs automatic recovery.
                if package:
                    with tempfile.TemporaryDirectory(prefix='kks-check-') as cache:
                        selected=import_package(package,cache); result=manager.inspect(selected)
                else: result=manager.inspect()
            elif action=='recover': result=manager.recover()
            else:
                selected=manager.select(package) if package else None
                result=manager.run(action,selected)
            result['activity']=logs
        code=0
    except Exception as e:
        result={'status':'blocked','message':str(e)}; code=1
    output=json.dumps(result,ensure_ascii=False,indent=2)
    if args.report:
        report=Path(args.report); report.parent.mkdir(parents=True,exist_ok=True); report.write_text(output+'\n','utf8')
    if sys.stdout: print(output)
    elif code and not args.report:
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk(); root.withdraw(); messagebox.showerror('KKS Installer',result['message']); root.destroy()
    return code


if __name__=='__main__': sys.exit(main())
