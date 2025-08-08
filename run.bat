@echo off
echo ===================================================
echo  Starting PM Application Server...
echo ===================================================

REM --- Activate Virtual Environment ---
echo Activating virtual environment...
call .\.venv\Scripts\activate

REM --- Run the Flask Application ---
echo Starting Flask server. The page will load shortly.
echo (Press CTRL+C in this window to stop the server)
python app.py

echo ===================================================
echo  Server has been stopped.
echo ===================================================
pause