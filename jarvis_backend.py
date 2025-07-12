from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import speech_recognition as sr
import pyttsx3
import os
import subprocess
import webbrowser
import requests
import json
import schedule
import time
import threading
from datetime import datetime, timedelta
import psutil
import pyautogui
import cv2
import numpy as np
from PIL import Image
import io
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import hashlib
import jwt
from functools import wraps
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = "your-secret-key-change-this"

# Initialize components
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
microphone = sr.Microphone()


# Database setup
def init_db():
    conn = sqlite3.connect("jarvis.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scheduled_time TIMESTAMP,
            priority INTEGER DEFAULT 1
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


class JARVISCore:
    def __init__(self):
        self.is_listening = False
        self.wake_word = "jarvis"
        self.commands = {
            "open": self.open_application,
            "search": self.web_search,
            "weather": self.get_weather,
            "news": self.get_news,
            "email": self.send_email,
            "screenshot": self.take_screenshot,
            "system": self.system_info,
            "schedule": self.schedule_task,
            "reminder": self.set_reminder,
            "calculate": self.calculate,
            "translate": self.translate_text,
            "control": self.system_control,
            "automation": self.run_automation,
        }

    def speak(self, text):
        """Convert text to speech"""
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"TTS Error: {e}")
            return False

    def listen(self):
        """Listen for voice commands"""
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

            command = recognizer.recognize_google(audio).lower()
            return command
        except sr.WaitTimeoutError:
            return "timeout"
        except sr.UnknownValueError:
            return "unknown"
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return "error"

    def process_command(self, command):
        """Process and execute commands"""
        command = command.lower().strip()

        for keyword, function in self.commands.items():
            if keyword in command:
                try:
                    result = function(command)
                    return result
                except Exception as e:
                    return f"Error executing command: {str(e)}"

        # If no specific command found, try AI response
        return self.ai_response(command)

    def open_application(self, command):
        """Open applications"""
        apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "browser": "chrome.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "visual studio": "devenv.exe",
            "code": "code.exe",
        }

        for app_name, app_path in apps.items():
            if app_name in command:
                try:
                    subprocess.Popen(app_path)
                    return f"Opening {app_name}"
                except:
                    return f"Could not open {app_name}"

        return "Application not found"

    def web_search(self, command):
        """Perform web search"""
        query = command.replace("search", "").strip()
        if query:
            url = f"https://www.google.com/search?q={query}"
            webbrowser.open(url)
            return f"Searching for: {query}"
        return "Please specify what to search for"

    def get_weather(self, command):
        """Get weather information"""
        try:
            # You'll need to get API key from OpenWeatherMap
            api_key = os.getenv("OPENWEATHER_API_KEY")
            if not api_key:
                return "Weather API key not configured"

            city = "New York"  # Default city
            if "in" in command:
                city = command.split("in")[-1].strip()

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200:
                temp = data["main"]["temp"]
                description = data["weather"][0]["description"]
                return f"Weather in {city}: {temp}°C, {description}"
            else:
                return "Could not fetch weather data"
        except Exception as e:
            return f"Weather error: {str(e)}"

    def get_news(self, command):
        """Get latest news"""
        try:
            # You'll need to get API key from NewsAPI
            api_key = os.getenv("NEWS_API_KEY")
            if not api_key:
                return "News API key not configured"

            url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200:
                articles = data["articles"][:3]  # Get top 3 news
                news_summary = "Top news headlines: "
                for article in articles:
                    news_summary += f"{article['title']}. "
                return news_summary
            else:
                return "Could not fetch news"
        except Exception as e:
            return f"News error: {str(e)}"

    def send_email(self, command):
        """Send email"""
        try:
            # Configure your email settings
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            sender_email = os.getenv("SENDER_EMAIL")
            sender_password = os.getenv("SENDER_PASSWORD")

            if not sender_email or not sender_password:
                return "Email credentials not configured"

            # Extract recipient and message from command
            # This is a simplified version - you can enhance the parsing
            recipient = "recipient@example.com"
            subject = "JARVIS Email"
            message = "This is an automated email from JARVIS"

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain"))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            return "Email sent successfully"
        except Exception as e:
            return f"Email error: {str(e)}"

    def take_screenshot(self, command):
        """Take screenshot"""
        try:
            screenshot = pyautogui.screenshot()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            screenshot.save(filename)
            return f"Screenshot saved as {filename}"
        except Exception as e:
            return f"Screenshot error: {str(e)}"

    def system_info(self, command):
        """Get system information"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            info = f"System Status: CPU {cpu_percent}%, "
            info += f"Memory {memory.percent}%, "
            info += f"Disk {disk.percent}%"
            return info
        except Exception as e:
            return f"System info error: {str(e)}"

    def schedule_task(self, command):
        """Schedule a task"""
        try:
            # Simple task scheduling - can be enhanced
            conn = sqlite3.connect("jarvis.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (task, status) VALUES (?, ?)", (command, "scheduled")
            )
            conn.commit()
            conn.close()
            return "Task scheduled successfully"
        except Exception as e:
            return f"Scheduling error: {str(e)}"

    def set_reminder(self, command):
        """Set reminder"""
        try:
            # Extract time and message from command
            reminder_time = datetime.now() + timedelta(minutes=5)  # Default 5 minutes
            message = command.replace("reminder", "").strip()

            conn = sqlite3.connect("jarvis.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (task, status, scheduled_time) VALUES (?, ?, ?)",
                (f"Reminder: {message}", "reminder", reminder_time),
            )
            conn.commit()
            conn.close()
            return f"Reminder set: {message}"
        except Exception as e:
            return f"Reminder error: {str(e)}"

    def calculate(self, command):
        """Perform calculations"""
        try:
            # Extract mathematical expression
            expression = command.replace("calculate", "").replace("what is", "").strip()
            # Simple math evaluation (be careful with eval in production)
            result = eval(expression)
            return f"The result is {result}"
        except Exception as e:
            return "Could not calculate that"

    def translate_text(self, command):
        """Translate text"""
        # This would require a translation API like Google Translate
        return "Translation feature requires API setup"

    def system_control(self, command):
        """Control system functions"""
        if "shutdown" in command:
            return "Initiating system shutdown"
        elif "restart" in command:
            return "Initiating system restart"
        elif "lock" in command:
            return "Locking system"
        elif "sleep" in command:
            return "Putting system to sleep"
        else:
            return "System control command not recognized"

    def run_automation(self, command):
        """Run automation scripts"""
        try:
            # Example automation tasks
            if "organize files" in command:
                return self.organize_files()
            elif "backup" in command:
                return self.backup_files()
            elif "clean system" in command:
                return self.clean_system()
            else:
                return "Automation task not recognized"
        except Exception as e:
            return f"Automation error: {str(e)}"

    def organize_files(self):
        """Organize files in downloads folder"""
        try:
            downloads_path = os.path.expanduser("~/Downloads")
            if not os.path.exists(downloads_path):
                return "Downloads folder not found"

            file_types = {
                "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf"],
                "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
                "Music": [".mp3", ".wav", ".flac", ".aac"],
            }

            organized_count = 0
            for filename in os.listdir(downloads_path):
                file_path = os.path.join(downloads_path, filename)
                if os.path.isfile(file_path):
                    file_ext = os.path.splitext(filename)[1].lower()

                    for folder, extensions in file_types.items():
                        if file_ext in extensions:
                            folder_path = os.path.join(downloads_path, folder)
                            os.makedirs(folder_path, exist_ok=True)

                            new_path = os.path.join(folder_path, filename)
                            os.rename(file_path, new_path)
                            organized_count += 1
                            break

            return f"Organized {organized_count} files"
        except Exception as e:
            return f"File organization error: {str(e)}"

    def backup_files(self):
        """Backup important files"""
        return "Backup automation would be implemented here"

    def clean_system(self):
        """Clean system temporary files"""
        return "System cleaning automation would be implemented here"

    def ai_response(self, command):
        """Generate AI response for general queries"""
        try:
            # You can integrate with OpenAI API here
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                openai.api_key = openai_api_key
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=f"As JARVIS AI assistant, respond to: {command}",
                    max_tokens=100,
                    temperature=0.7,
                )
                return response.choices[0].text.strip()
            else:
                return "I'm processing your request, but I need more specific commands to help you better."
        except Exception as e:
            return "I understand you're asking something, but I need more context to help you properly."


# Initialize JARVIS
jarvis = JARVISCore()


# API Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/command", methods=["POST"])
def process_command():
    data = request.json
    command = data.get("command", "")

    if not command:
        return jsonify({"error": "No command provided"}), 400

    result = jarvis.process_command(command)

    # Also speak the response
    threading.Thread(target=jarvis.speak, args=(result,)).start()

    return jsonify({"response": result})


@app.route("/api/listen", methods=["POST"])
def listen_command():
    try:
        command = jarvis.listen()
        if command in ["timeout", "unknown", "error"]:
            return jsonify({"error": f"Speech recognition {command}"}), 400

        result = jarvis.process_command(command)
        threading.Thread(target=jarvis.speak, args=(result,)).start()

        return jsonify({"command": command, "response": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    conn = sqlite3.connect("jarvis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = cursor.fetchall()
    conn.close()

    task_list = []
    for task in tasks:
        task_list.append(
            {
                "id": task[0],
                "task": task[1],
                "status": task[2],
                "created_at": task[3],
                "scheduled_time": task[4],
                "priority": task[5],
            }
        )

    return jsonify(task_list)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = sqlite3.connect("jarvis.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Task deleted"})


@app.route("/api/system-info", methods=["GET"])
def get_system_info():
    try:
        info = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "boot_time": psutil.boot_time(),
            "current_time": time.time(),
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/screenshot", methods=["POST"])
def take_screenshot():
    try:
        screenshot = pyautogui.screenshot()
        img_buffer = io.BytesIO()
        screenshot.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        return jsonify({"screenshot": f"data:image/png;base64,{img_base64}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Background task scheduler
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Start scheduler in background
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

if __name__ == "__main__":
    print("JARVIS AI System Starting...")
    print("Backend server running on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
