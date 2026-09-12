MIKA — Personal Logistics Agent

1. Put app.py, templates/, static/, and requirements.txt in your existing project folder.
2. Keep your existing .env file with:
   GEMINI_API_KEY=your_key
   STEEL_API_KEY=your_key
3. In your virtual environment, install Flask if needed:
   pip install flask
4. Run:
   python app.py
5. Open:
   http://127.0.0.1:5000

The webpage sends the user's brain dump to the Flask backend. The backend uses your existing Gemini + Steel pipeline, then returns the plan to the webpage.
