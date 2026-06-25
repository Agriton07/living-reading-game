LIVING READING — How to run
━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Open terminal in this folder

2. Run:
   pip install flask flask-socketio eventlet
   python app.py

3. Find your IP address:
   Mac/Linux: ifconfig | grep "inet "
   Windows:   ipconfig

4. Share these URLs:
   Audience phones → http://YOUR_IP:5050/
   Stage screen    → http://YOUR_IP:5050/stage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO RUN THE PRESENTATION:

Stage screen (you project this):
  → Click "Waiting" — audience connects
  → Click "Read"    — everyone reads the text
  → Click "Erase"   — everyone erases words
  → Click "Reveal"  — collective poem appears

The collective poem shows each word sized by
how many people kept it. Big = everyone kept it.
Small/dim = most people erased it.
