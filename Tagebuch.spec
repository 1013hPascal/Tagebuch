# Erstellt von CodeCockpit. Sie dürfen die Datei anpassen, das Cockpit nutzt sie
# bei jedem Bau weiter. Pfade sind relativ zum Ordner Code.

a = Analysis(['main.py'], pathex=[], binaries=[], datas=[],
             hiddenimports=[], excludes=[])
pyz = PYZ(a.pure)

exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Tagebuch',
          console=False, icon=None, upx=False)
