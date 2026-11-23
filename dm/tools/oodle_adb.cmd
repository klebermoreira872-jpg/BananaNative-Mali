@rem DM_OODLE_HOST on Windows: Popen cannot start a .py, so this runs dm/tools/oodle_adb.py with the Python launcher (python.org installs)
@py -3 -I "%~dp0oodle_adb.py" %*
