@echo off
echo =========================================
echo Pushing Sentinel Ops Center to GitHub...
echo =========================================

REM Initialize git if it hasn't been initialized
git init

REM Add all files
git add .

REM Commit the files
git commit -m "Hackathon Final Submission: Sentinel Ops Center"

REM Rename the default branch to main
git branch -M main

REM Add the remote origin
git remote add origin https://github.com/Mishra123456/AI_INCIDENT_CAUSE_ANALYZER.git

REM Push to GitHub
git push -u origin main

echo =========================================
echo DONE! Check your GitHub Repository!
echo =========================================
pause
