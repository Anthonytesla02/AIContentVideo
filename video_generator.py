import os
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from elevenlabs import ElevenLabs
from pydub import AudioSegment
import replicate
from mistralai import Mistral
from pydantic import BaseModel


class Scene(BaseModel):
    scene_number: int
    narration: str
    duration_seconds: int
    visual_description: str


class VideoGenerator:
    def __init__(self):
        self.mistral_client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))
        self.elevenlabs_client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))
        self.replicate_token = os.environ.get("REPLICATE_API_TOKEN")
        self.pexels_api_key = os.environ.get("PEXELS_API_KEY")
        
        self.output_dir = Path("outputs")
        self.cache_dir = Path("cache")
        self.output_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.image_cache = {}
        self._load_cache()
        
        self.costs = {
            "elevenlabs_chars": 0,
            "replicate_calls": 0,
            "pexels_calls": 0,
            "total_cost_usd": 0.0
        }
    
    def _load_cache(self):
        cache_file = self.cache_dir / "image_cache.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                self.image_cache = json.load(f)
    
    def _save_cache(self):
        cache_file = self.cache_dir / "image_cache.json"
        with open(cache_file, 'w') as f:
            json.dump(self.image_cache, f)
    
    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def generate_script(self, user_topic: str, video_orientation: str, 
                       video_length: str, style: str, progress_callback=None) -> List[Dict[str, Any]]:
        if progress_callback:
            progress_callback("Generating script with Mistral AI...")
        
        length_mapping = {
            "short_form": "30-60 seconds total",
            "long_form": "2-10 minutes total"
        }
        
        prompt = f"""You are a professional scriptwriter. Create a narration script for a video about: "{user_topic}".

Constraints:
- Video Length: {length_mapping.get(video_length, video_length)}
- Orientation: {video_orientation}
- Visual Style: {style}

Important:
- For short_form: create 4-6 scenes, each 7-10 seconds
- For long_form: create 10-20 scenes, each 6-12 seconds
- Make visual_description very detailed and cinematic for AI image generation
- Ensure narration flows naturally and engages the audience
- Match the {style} aesthetic in visual descriptions

Return a JSON array of scenes with scene_number, narration, duration_seconds, and visual_description."""

        response = self.mistral_client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            response_format={
                "type": "json_object"
            }
        )
        
        script_text = response.choices[0].message.content.strip()
        
        script_text = script_text.replace('```json', '').replace('```', '').strip()
        
        try:
            parsed_data = json.loads(script_text)
            
            if isinstance(parsed_data, dict):
                if "scenes" in parsed_data:
                    script = parsed_data["scenes"]
                elif "script" in parsed_data:
                    script = parsed_data["script"]
                else:
                    for key in parsed_data:
                        if isinstance(parsed_data[key], list):
                            script = parsed_data[key]
                            break
                    else:
                        script = [parsed_data]
            else:
                script = parsed_data
            
            if progress_callback:
                progress_callback(f"Script generated: {len(script)} scenes")
            return script
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse script JSON: {e}\nReceived: {script_text[:200]}")
    
    def generate_audio(self, script: List[Dict[str, Any]], progress_callback=None) -> List[str]:
        if progress_callback:
            progress_callback("Generating voiceover with ElevenLabs (per-scene)...")
        
        audio_files = []
        
        for i, scene in enumerate(script):
            if progress_callback:
                progress_callback(f"Generating audio for scene {i+1}/{len(script)}...")
            
            narration_text = scene["narration"]
            self.costs["elevenlabs_chars"] += len(narration_text)
            
            audio_generator = self.elevenlabs_client.text_to_speech.convert(
                text=narration_text,
                voice_id="21m00Tcm4TlvDq8ikWAM",
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            
            scene_audio_path = self.output_dir / f"audio_scene_{i+1}.mp3"
            with open(scene_audio_path, 'wb') as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            audio_files.append(str(scene_audio_path))
            
            time.sleep(0.5)
        
        if progress_callback:
            progress_callback(f"Generated {len(audio_files)} audio clips")
        
        return audio_files
    
    def generate_image_replicate(self, prompt: str, style: str) -> Optional[bytes]:
        style_modifiers = {
            "cinematic": "cinematic lighting, dramatic composition, film grain, 8k, professional photography",
            "minimalist": "minimalist, clean, simple, modern, high contrast, geometric",
            "vibrant": "vibrant colors, saturated, energetic, dynamic, colorful, bold",
            "documentary": "documentary style, realistic, natural lighting, authentic, photojournalistic"
        }
        
        enhanced_prompt = f"{prompt}, {style_modifiers.get(style, '')}"
        
        try:
            self.costs["replicate_calls"] += 1
            
            output = replicate.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": enhanced_prompt,
                    "negative_prompt": "ugly, blurry, low quality, distorted, text, watermark",
                    "width": 1024,
                    "height": 1024,
                    "num_inference_steps": 20
                },
                wait=60
            )
            
            output_list = list(output) if output else []
            if output_list and len(output_list) > 0:
                image_url = output_list[0]
                
                response = requests.get(str(image_url), timeout=30)
                if response.status_code == 200:
                    return response.content
            
            return None
        except Exception as e:
            print(f"Replicate generation failed: {e}")
            return None
    
    def get_pexels_media(self, query: str, orientation: str, style: str) -> Optional[tuple]:
        style_keywords = {
            "cinematic": "cinematic dramatic",
            "minimalist": "minimal simple clean",
            "vibrant": "colorful vibrant bright",
            "documentary": "realistic natural authentic"
        }
        
        search_query = f"{query} {style_keywords.get(style, '')}"
        
        headers = {"Authorization": self.pexels_api_key}
        
        orientation_map = {
            "landscape": "landscape",
            "portrait": "portrait"
        }
        
        params = {
            "query": search_query,
            "per_page": 5,
            "orientation": orientation_map.get(orientation, "landscape")
        }
        
        try:
            response = requests.get(
                "https://api.pexels.com/v1/search",
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    photo = data["photos"][0]
                    image_url = photo["src"]["large2x"]
                    
                    img_response = requests.get(image_url, timeout=15)
                    if img_response.status_code == 200:
                        return (img_response.content, "image")
            
            video_response = requests.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params=params,
                timeout=15
            )
            
            if video_response.status_code == 200:
                data = video_response.json()
                if data.get("videos") and len(data["videos"]) > 0:
                    video = data["videos"][0]
                    video_files = video.get("video_files", [])
                    if video_files:
                        video_url = video_files[0]["link"]
                        vid_response = requests.get(video_url, timeout=30)
                        if vid_response.status_code == 200:
                            return (vid_response.content, "video")
            
            return None
        except Exception as e:
            print(f"Pexels search failed: {e}")
            return None
    
    def generate_visuals(self, script: List[Dict[str, Any]], orientation: str, 
                        style: str, progress_callback=None) -> List[str]:
        if progress_callback:
            progress_callback("Generating visuals (AI images + stock fallback)...")
        
        visual_files = []
        
        for i, scene in enumerate(script):
            if progress_callback:
                progress_callback(f"Generating visual {i+1}/{len(script)}: {scene['visual_description'][:50]}...")
            
            prompt = scene["visual_description"]
            prompt_hash = self._hash_prompt(prompt)
            
            if prompt_hash in self.image_cache:
                cached_path = self.image_cache[prompt_hash]
                if Path(cached_path).exists():
                    visual_files.append(cached_path)
                    if progress_callback:
                        progress_callback(f"Using cached visual for scene {i+1}")
                    continue
            
            ai_image_content = self.generate_image_replicate(prompt, style)
            
            if ai_image_content:
                visual_path = self.output_dir / f"visual_scene_{i+1}.jpg"
                with open(visual_path, 'wb') as f:
                    f.write(ai_image_content)
                
                visual_files.append(str(visual_path))
                self.image_cache[prompt_hash] = str(visual_path)
                self._save_cache()
                
                time.sleep(1.5)
            else:
                if progress_callback:
                    progress_callback(f"AI generation failed for scene {i+1}, using Pexels...")
                
                pexels_result = self.get_pexels_media(prompt, orientation, style)
                
                if pexels_result:
                    self.costs["pexels_calls"] += 1
                    content, media_type = pexels_result
                    
                    if media_type == "video":
                        visual_path = self.output_dir / f"visual_scene_{i+1}.mp4"
                    else:
                        visual_path = self.output_dir / f"visual_scene_{i+1}.jpg"
                    
                    with open(visual_path, 'wb') as f:
                        f.write(content)
                    
                    visual_files.append(str(visual_path))
                    
                    if media_type == "image":
                        self.image_cache[prompt_hash] = str(visual_path)
                        self._save_cache()
                else:
                    raise Exception(f"Failed to generate visual for scene {i+1}")
        
        if progress_callback:
            progress_callback(f"All {len(visual_files)} visuals generated")
        
        return visual_files
    
    def calculate_costs(self):
        elevenlabs_cost = (self.costs["elevenlabs_chars"] / 1000) * 0.30
        replicate_cost = self.costs["replicate_calls"] * 0.02
        pexels_cost = 0.0
        
        total_cost = elevenlabs_cost + replicate_cost + pexels_cost
        self.costs["total_cost_usd"] = round(total_cost, 4)
        
        return self.costs
