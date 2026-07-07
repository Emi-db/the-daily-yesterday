@echo off
rem ============================================================
rem  Imprime la edicion del dia de The Daily Yesterday.
rem  Lo corre solo la tarea programada de Windows cada manana,
rem  o vos a mano con doble clic.
rem ============================================================
cd /d "%~dp0"
"C:\Users\Emiliano Dalla Bella\AppData\Local\Programs\Python\Python313\python.exe" generar_edicion.py
