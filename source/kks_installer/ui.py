"""Small native Windows interface; worker operations never block the UI loop."""
from pathlib import Path
import queue,threading,tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .profile import Installer
from .platforms import discover

BG='#111b18';PANEL='#1b2923';PANEL2='#24362d';INK='#ecf1e9';MUTED='#acbdb0';GREEN='#b7f36c';LINE='#3c5143';RED='#ffb89a'

class App:
    def __init__(self,release):
        self.release=release;self.root=tk.Tk();self.root.title('KKS Installer · 1.0.0')
        self.root.geometry('940x820');self.root.minsize(880,800);self.root.configure(bg=BG)
        self.root.option_add('*Font',('Segoe UI',10));self.busy=False;self.events=queue.Queue();self.last_status=None
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        style=ttk.Style();style.theme_use('clam')
        style.configure('KKS.Horizontal.TProgressbar',troughcolor=PANEL,bordercolor=PANEL,background=GREEN,lightcolor=GREEN,darkcolor=GREEN)
        outer=tk.Frame(self.root,bg=BG);outer.pack(fill='both',expand=True,padx=34,pady=28)
        top=tk.Frame(outer,bg=BG);top.pack(fill='x')
        logo=tk.Label(top,text='KKS',font=('Segoe UI',31,'bold'),fg=GREEN,bg=BG);logo.pack(side='left')
        tk.Label(top,text='KIT’S KILLER SYSTEM',font=('Segoe UI',11,'bold'),fg=INK,bg=BG).pack(side='left',padx=20)
        tk.Label(top,text='1.0.0  /  ENGLISH',font=('Segoe UI',10),fg=MUTED,bg=BG).pack(side='right')
        tk.Label(outer,text='Your inventory. Rewritten.',font=('Segoe UI',24,'bold'),fg=INK,bg=BG,anchor='w').pack(fill='x',pady=(18,6))
        tk.Label(outer,text="Over 1,000 custom glyphs transform Fallout 76's inventory into information you can understand at a glance.",fg=MUTED,bg=BG,anchor='w',justify='left',wraplength=790).pack(fill='x',pady=(0,24))
        location=tk.Frame(outer,bg=PANEL,highlightbackground=LINE,highlightthickness=1);location.pack(fill='x')
        tk.Label(location,text='FALLOUT 76 LOCATION',font=('Segoe UI',9,'bold'),fg=MUTED,bg=PANEL,anchor='w').pack(fill='x',padx=20,pady=(14,8))
        row=tk.Frame(location,bg=PANEL);row.pack(fill='x',padx=20,pady=(0,18))
        self.path=tk.StringVar();self.entry=tk.Entry(row,textvariable=self.path,bg=PANEL2,fg=INK,insertbackground=INK,relief='flat',font=('Segoe UI',11))
        self.entry.pack(side='left',fill='x',expand=True,ipady=9);self.entry.bind('<Return>',lambda e:self.start('check'))
        self.browse=self.button(row,'Browse…',self.choose);self.browse.pack(side='left',padx=(10,0))
        self.check=self.button(row,'Check',lambda:self.start('check'));self.check.pack(side='left',padx=(8,0))
        self.status_panel=tk.Frame(outer,bg=PANEL,highlightbackground=LINE,highlightthickness=1);self.status_panel.pack(fill='x',pady=16)
        self.status_title=tk.Label(self.status_panel,text='Let’s find your game.',font=('Segoe UI',19,'bold'),fg=INK,bg=PANEL,anchor='w')
        self.status_title.pack(fill='x',padx=20,pady=(17,5))
        self.status_message=tk.Label(self.status_panel,text='Choose your Fallout 76 folder, then check compatibility.',fg=MUTED,bg=PANEL,justify='left',wraplength=790,anchor='w')
        self.status_message.pack(fill='x',padx=20,pady=(0,12))
        chips=tk.Frame(self.status_panel,bg=PANEL);chips.pack(fill='x',padx=20,pady=(0,16))
        for label in ['Build verification','Restoration backups','File validation']:
            tk.Label(chips,text=label,fg=GREEN,bg=PANEL2,padx=10,pady=5,font=('Segoe UI',9)).pack(side='left',padx=(0,10))
        # These labels describe safeguards, never claim that an unchecked game passed.
        self.progress=ttk.Progressbar(outer,style='KKS.Horizontal.TProgressbar',mode='indeterminate');self.progress.pack(fill='x',pady=(0,14))
        actions=tk.Frame(outer,bg=BG);actions.pack(fill='x')
        self.primary=self.button(actions,'Install KKS',lambda:self.start('install'),primary=True);self.primary.pack(side='left')
        self.repair=self.button(actions,'Repair',lambda:self.start('repair'));self.repair.pack(side='left',padx=10)
        self.restore=self.button(actions,'Restore vanilla',lambda:self.start('restore'));self.restore.pack(side='left')
        self.primary.configure(state='disabled');self.repair.configure(state='disabled');self.restore.configure(state='disabled')
        tk.Label(actions,text='No xTranslator required',fg=MUTED,bg=BG,font=('Segoe UI',9)).pack(side='right')
        tk.Label(outer,text='ACTIVITY',fg=MUTED,bg=BG,font=('Segoe UI',9,'bold'),anchor='w').pack(fill='x',pady=(22,8))
        self.log=tk.Text(outer,height=5,bg=PANEL,fg=MUTED,relief='flat',font=('Consolas',10),wrap='word',padx=14,pady=10,state='disabled')
        self.log.pack(fill='both',expand=True)
        tk.Label(outer,text='Supports Steam English Slasher build 25258219 · Backups remain in your game folder',fg=MUTED,bg=BG,font=('Segoe UI',9),anchor='w').pack(fill='x',pady=(14,0))
        self.path.trace_add('write',self.path_changed)
        candidates=discover()
        if candidates:
            self.path.set(candidates[0]);self.root.after(350,lambda:self.start('check'))
        else:self.append('No game installation was detected automatically. Use Browse to choose its folder.')
        self.root.after(100,self.pump)

    def button(self,parent,text,command,primary=False):
        return tk.Button(parent,text=text,command=command,font=('Segoe UI',11,'bold' if primary else 'normal'),
                         bg=GREEN if primary else PANEL2,fg=BG if primary else INK,activebackground='#cafb90' if primary else LINE,
                         activeforeground=BG if primary else INK,disabledforeground='#758677',relief='flat',borderwidth=0,padx=19,pady=10,cursor='hand2')
    def append(self,text):
        self.log.configure(state='normal');self.log.insert('end',text+'\n');self.log.see('end');self.log.configure(state='disabled')
    def path_changed(self,*args):
        if not self.busy:
            self.last_status=None
            for b in [self.primary,self.repair,self.restore]:b.configure(state='disabled')
    def choose(self):
        path=filedialog.askdirectory(title='Choose the folder containing Fallout76.exe',initialdir=self.path.get() or None)
        if path:self.path.set(path);self.start('check')
    def close(self):
        if self.busy:
            messagebox.showinfo('KKS is working','Please wait for the operation to finish. If it is interrupted, KKS will retain the recovery journal and backups.')
        else:self.root.destroy()
    def start(self,action):
        if self.busy:return
        game=self.path.get().strip()
        if not game:self.choose();return
        self.busy=True;self.last_status=None
        for widget in [self.entry,self.browse,self.check,self.primary,self.repair,self.restore]:widget.configure(state='disabled')
        self.progress.start(12);self.status_title.configure(text='Checking your installation…' if action=='check' else 'Working safely…',fg=INK)
        self.status_message.configure(text='This can take a moment while KKS verifies the game files. Keep the game closed.')
        self.append({'check':'Checking compatibility…','install':'Installing KKS…','repair':'Repairing KKS…','restore':'Restoring vanilla…','recover':'Recovering the interrupted operation…'}[action])
        def work():
            try:
                engine=Installer(game,self.release,lambda text:self.events.put(('log',text)))
                result=engine.inspect() if action=='check' else engine.recover() if action=='recover' else engine.run(action)
                if action!='check':result=engine.inspect()
                self.events.put(('success',result))
            except Exception as e:self.events.put(('error',str(e)))
        threading.Thread(target=work,daemon=False).start()
    def pump(self):
        try:
            while True:
                kind,data=self.events.get_nowait()
                if kind=='log':self.append(data);continue
                self.busy=False;self.progress.stop()
                for widget in [self.entry,self.browse,self.check]:widget.configure(state='normal')
                if kind=='error':
                    self.status_title.configure(text='Needs attention before continuing',fg=RED)
                    self.status_message.configure(text=data[:460]);self.append(data)
                else:
                    status=data['status'];self.last_status=status
                    self.status_title.configure(text={'ready':'Ready for KKS.','installed':'KKS is installed.','repairable':'KKS needs a repair.','recovery_required':'Let’s recover the interrupted change.'}.get(status,status),fg=GREEN)
                    self.status_message.configure(text=data.get('message','Verified.'));self.append(data.get('message',status))
                    self.primary.configure(text='Recover previous state' if status=='recovery_required' else 'Install KKS',command=lambda:self.start('recover' if self.last_status=='recovery_required' else 'install'),state='normal' if status in ('ready','recovery_required') else 'disabled')
                    self.repair.configure(state='normal' if status in ('installed','repairable') else 'disabled')
                    self.restore.configure(state='normal' if status in ('installed','repairable') else 'disabled')
        except queue.Empty:pass
        self.root.after(100,self.pump)
    def run(self):self.root.mainloop()

def launch(release):App(release).run()
