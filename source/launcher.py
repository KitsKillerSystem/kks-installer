from pathlib import Path
import argparse,json,sys,traceback
from kks_installer.engine import Release
from kks_installer.profile import Installer
from kks_installer._release import MANIFEST_SHA256
from kks_installer.platforms import discover

def main():
    parser=argparse.ArgumentParser(description='KKS 1.0.0 standalone installer')
    group=parser.add_mutually_exclusive_group()
    for name in ['check','install','repair','restore','recover','detect']:group.add_argument('--'+name,action='store_true')
    parser.add_argument('--game',help='Folder containing Fallout76.exe')
    parser.add_argument('--report',help='Write machine-readable result to this JSON file')
    args=parser.parse_args()
    try:
        if args.detect:result={'installations':discover()}
        else:
            base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
            release=Release(base/'release',MANIFEST_SHA256)
            action=next((x for x in ['check','install','repair','restore','recover'] if getattr(args,x)),None)
            if action is None:
                from kks_installer.ui import launch
                launch(release);return 0
            if not args.game:raise ValueError('--game is required for command-line operations')
            logs=[];engine=Installer(args.game,release,logs.append)
            result=engine.inspect() if action=='check' else engine.recover() if action=='recover' else engine.run(action)
            result['activity']=logs
        code=0
    except Exception as e:
        result={'status':'blocked','message':str(e)};code=1
    output=json.dumps(result,ensure_ascii=False,indent=2)
    if args.report:
        # Explicit command-line report path; never accepted from package or receipt data.
        report=Path(args.report);report.parent.mkdir(parents=True,exist_ok=True);report.write_text(output+'\n','utf8')
    if sys.stdout:print(output)
    elif code and not args.report:
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw();messagebox.showerror('KKS Installer',result['message']);root.destroy()
    return code

if __name__=='__main__':sys.exit(main())
