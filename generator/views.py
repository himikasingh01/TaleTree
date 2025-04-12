from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Story  , Profile
import google.generativeai as genai
import os
import base64
import re
import requests
from deep_translator import GoogleTranslator



# Load your API key (set this in your environment or hardcode for now)
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAbQwpW-7878kMqd7PVDOt5dOGoCqXQVhI"))

# Load the Gemini model
model = genai.GenerativeModel("gemini-2.0-flash-exp")

@login_required(login_url='login')
def home(request):
    original_content = {
        "welcome": f"Welcome, {request.user.username}!",
        "title": "AI Story Generator",
        "prompt_placeholder": "Enter your story idea...",
        "generate_button": "Generate"
    }

    translated_content = original_content

    if request.method == 'POST' and 'language' in request.POST:
        target_lang = request.POST.get('language')
        if target_lang:
            try:
                translated_content = {
                    key: GoogleTranslator(source='auto', target=target_lang).translate(text)
                    for key, text in original_content.items()
                }
            except Exception as e:
                translated_content = original_content
                translated_content['error'] = f"Translation failed: {e}"

    return render(request, 'generator/home.html', {
        'translations': translated_content
    })

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            return render(request, 'generator/login.html', {'error': 'Invalid credentials'})
    return render(request, 'generator/login.html')

def user_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            return render(request, 'generator/register.html', {'error': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'generator/register.html', {'error': 'Username already exists'})
        
        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        return redirect('login')
    
    return render(request, 'generator/register.html')

def user_logout(request):
    logout(request)
    return redirect('login')


def word_meaning(request):
    if request.method == "GET" and request.GET.get("word"):
        word = request.GET.get("word")
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)  # Corrected here ✅

        if response.status_code == 200:
            data = response.json()
            try:
                # Extract a simple definition
                meaning = data[0]["meanings"][0]["definitions"][0]["definition"]
            except (KeyError, IndexError):
                meaning = "Definition not found or too complex."
        else:
            meaning = "No definition found."

        # AJAX or normal GET
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"meaning": meaning})

        return render(request, "generator/word_meaning.html", {"meaning": meaning, "searched_word": word})

    return render(request, "generator/word_meaning.html")


@login_required(login_url='login')
def generate_story(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '')
        target_lang = request.POST.get('language', 'en')
        profile = Profile.objects.get(user=request.user)
        if profile.credits < 2:
            return JsonResponse({'error': 'Not enough credits to generate a story.'}, status=403)

        combined_prompt = (
            f"Write a story in 3 scenes (about 500 words total) based on: '{prompt}'. "
            "After writing the complete story, provide 3 image descriptions: one for the front page and one for each of the two scenes. "
            "Ensure image descriptions are at the end under a separate heading like 'Image Descriptions'."
        )

        try:
            response = model.generate_content(combined_prompt)
            story_text = response.text
            if target_lang != 'en':
                try:
                    story_text = GoogleTranslator(source='auto', target=target_lang).translate(story_text)
                except Exception as e:
                    pass 

            # Save the story to the database
            Story.objects.create(
                user=request.user,
                prompt=prompt,
                content=story_text
            )
            # Deduct credits
            profile.credits -= 2
            profile.save()
            raw_descriptions = re.findall(r"\*\*\s*(Front Page|Scene \d+):\*\*\s*(.*)", story_text.split("Image Descriptions")[-1])
            image_prompts = [desc.strip() for _, desc in raw_descriptions][:3]
            print("Extracted image prompts:", image_prompts)
            return JsonResponse({
                'story': story_text,
                'images': image_prompts # limit to 3 prompts
                })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required(login_url='login')
def story_library(request):
    stories = Story.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'generator/story_library.html', {'stories': stories})

