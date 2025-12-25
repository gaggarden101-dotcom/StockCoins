import os
import sys
import subprocess
from threading import Thread
from flask import Flask

# Function to run the bot.py script
def run_bot():
    # Use sys.executable to ensure the correct Python interpreter is used
    # This runs bot.py as a separate process, which is more robust than just import
    subprocess.run([sys.executable, "bot.py"])

# Start the bot.py script in a separate thread
# This prevents the Flask web server from blocking your Discord bot's operations
bot_thread = Thread(target=run_bot)
bot_thread.start()

# This is a dummy Flask app that Replit will detect and use to provide the webview URL.
# Your Discord bot's logic runs independently in 'bot.py'.
app = Flask(__name__)

@app.route('/')
def home():
    return "Your Discord Bot's Web Server is Active!"

# Replit automatically exposes port 8080 for web apps.
# We explicitly run the Flask app on this port.
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
