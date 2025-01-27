from flask import Flask, request, render_template
from deep_translator import GoogleTranslator

app = Flask(__name__)

def translate_text(text, target_language):
    try:
        translated = GoogleTranslator(target=target_language).translate(text)
        return translated
    except Exception as e:
        return f"Error: {e}"

@app.route("/", methods=["GET", "POST"])
def home():
    default_content = {
        "title": "Google Translate with Python",
        "header": "Welcome to the Custom Translator!",
        "instructions": "Enter text below and select a language to translate.",
        "textarea_placeholder": "Enter text to translate",
        "language_prompt": "Select Language:",
        "languages": {
            "ko": "Korean",
            "es": "Spanish",
            "fr": "French",
            "hi": "Hindi",
            "ja": "Japanese",
            "de": "German"
        },
        "button_text": "Translate",
        "translated_text_label": "Translated Text:",
    }
    translated_content = default_content

    if request.method == "POST":
        target_language = request.form["language"]
        translated_content = {key: translate_text(value, target_language) if isinstance(value, str) else value
                              for key, value in default_content.items()}
        translated_content["languages"] = {
            lang: translate_text(name, target_language) for lang, name in default_content["languages"].items()
        }

    return render_template("translator.html", **translated_content)

if __name__ == "__main__":
    app.run(debug=True)
