from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Story, Profile
import google.generativeai as genai
import os
import base64
import re
import requests
from deep_translator import GoogleTranslator
from django.views.decorators.csrf import csrf_exempt
import random

# Load your API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAbQwpW-7878kMqd7PVDOt5dOGoCqXQVhI"))
model = genai.GenerativeModel("gemini-2.0-flash-exp")

def landing_page(request):
    return render(request, 'generator/landing.html')

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
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
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

def story_library(request):
    stories = Story.objects.filter(user=request.user).order_by('-created_at')
    cartoon_images = [
        'https://cdn-icons-png.flaticon.com/512/2946/2946035.png',
        'https://cdn-icons-png.flaticon.com/512/2946/2946015.png',
        'https://cdn-icons-png.flaticon.com/512/2946/2946023.png',
        'https://cdn-icons-png.flaticon.com/512/2946/2946002.png',
        'https://cdn-icons-png.flaticon.com/512/2946/2946041.png',
        'https://cdn-icons-png.flaticon.com/512/2946/2946055.png',
    ]
    return render(request, 'generator/story_library.html', {
        'stories': stories,
        'random_cartoon_images': cartoon_images,
    })

def word_meaning(request):
    if request.method == "GET" and request.GET.get("word"):
        word = request.GET.get("word")
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            try:
                meaning = data[0]["meanings"][0]["definitions"][0]["definition"]
            except (KeyError, IndexError):
                meaning = "Definition not found."
        else:
            meaning = "No definition found."

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
            f"You are a skilled children's author. Write a short, logical, and engaging story for kids based on: '{prompt}'.\n"
            "Split the story into exactly 3 clear scenes. Each scene should continue from the previous one and be 100-150 words long.\n\n"
            "At the end of the story, add this:\n"
            "**Image Descriptions:**\n"
            "**Scene 1:** (short image prompt describing scene 1)\n"
            "**Scene 2:** (short image prompt describing scene 2)\n"
            "**Scene 3:** (short image prompt describing scene 3)\n"
        )

        try:
            response = model.generate_content(combined_prompt)
            story_text = response.text
            story_text_cleaned = story_text.split("Image Descriptions")[0].strip()
            if target_lang != 'en':
                story_text_cleaned = GoogleTranslator(source='auto', target=target_lang).translate(story_text_cleaned)

            raw_descriptions = re.findall(r"\*\*Scene \d+:\*\*\s*(.+)", story_text)
            image_prompts = [desc.strip() for desc in raw_descriptions][:3]

            Story.objects.create(user=request.user, prompt=prompt, content=story_text)
            profile.credits -= 2
            profile.save()

            return JsonResponse({'story': story_text_cleaned, 'images': image_prompts})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
def story_library(request):
    stories = Story.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'generator/story_library.html', {'stories': stories})

@login_required(login_url='login')
@csrf_exempt
def storybook_view(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        target_lang = request.POST.get('language', 'en')
        profile = Profile.objects.get(user=request.user)

        if profile.credits < 2:
            return render(request, 'generator/storybook.html', {'error': 'Not enough credits!', 'prompt': prompt})

        combined_prompt = (
            f"You are a skilled children's author. Write a short, logical, and engaging story for kids based on: '{prompt}'.\n"
            "Split the story into exactly 3 clear scenes. Each scene should continue from the previous one and be 100-150 words long.\n\n"
            "At the end of the story, add this:\n"
            "**Image Descriptions:**\n"
            "**Scene 1:** (short image prompt describing scene 1)\n"
            "**Scene 2:** (short image prompt describing scene 2)\n"
            "**Scene 3:** (short image prompt describing scene 3)\n"
        )

        try:
            response = model.generate_content(combined_prompt)
            story_text = response.text
            story_text_cleaned = story_text.split("Image Descriptions")[0].strip()
            if target_lang != 'en':
                story_text_cleaned = GoogleTranslator(source='auto', target=target_lang).translate(story_text_cleaned)

            raw_descriptions = re.findall(r"\*\*Scene \d+:\*\*\s*(.+)", story_text)
            image_prompts = [desc.strip() for desc in raw_descriptions][:3]

            Story.objects.create(user=request.user, prompt=prompt, content=story_text)
            profile.credits -= 2
            profile.save()

            return render(request, 'generator/storybook.html', {
                'prompt': prompt,
                'story': story_text_cleaned,
                'images': image_prompts
            })
        except Exception as e:
            return render(request, 'generator/storybook.html', {'error': str(e), 'prompt': prompt})

    return redirect('home')

