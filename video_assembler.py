import os
from pathlib import Path
from typing import List, Dict, Any
from moviepy import (
    ImageClip, VideoFileClip, AudioFileClip, 
    CompositeVideoClip, concatenate_videoclips, CompositeAudioClip
)
from PIL import Image


class VideoAssembler:
    def __init__(self):
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
    
    def _get_dimensions(self, orientation: str) -> tuple:
        if orientation == "portrait":
            return (1080, 1920)
        else:
            return (1920, 1080)
    
    def _resize_and_crop(self, clip, target_width, target_height):
        clip_aspect = clip.w / clip.h
        target_aspect = target_width / target_height
        
        if clip_aspect > target_aspect:
            new_height = target_height
            new_width = int(new_height * clip_aspect)
        else:
            new_width = target_width
            new_height = int(new_width / clip_aspect)
        
        clip = clip.resized(width=new_width, height=new_height)
        
        x_center = (new_width - target_width) / 2
        y_center = (new_height - target_height) / 2
        
        clip = clip.cropped(
            x1=x_center,
            y1=y_center,
            x2=x_center + target_width,
            y2=y_center + target_height
        )
        
        return clip
    
    def _apply_transition(self, clip, style: str, duration: float):
        from moviepy import vfx
        
        fade_duration = min(0.5, duration / 4)
        
        if style == "cinematic":
            clip = clip.with_effects([vfx.FadeIn(fade_duration), vfx.FadeOut(fade_duration)])
        elif style == "minimalist":
            pass
        elif style == "vibrant":
            clip = clip.with_effects([vfx.FadeIn(fade_duration * 0.5), vfx.FadeOut(fade_duration * 0.5)])
        elif style == "documentary":
            clip = clip.with_effects([vfx.FadeIn(fade_duration * 0.3), vfx.FadeOut(fade_duration * 0.3)])
        
        return clip
    
    def assemble_video(self, script: List[Dict[str, Any]], visual_files: List[str],
                       audio_files: List[str], orientation: str, style: str,
                       output_filename: str, progress_callback=None) -> str:
        if progress_callback:
            progress_callback("Assembling video clips...")
        
        target_width, target_height = self._get_dimensions(orientation)
        
        clips = []
        
        for i, (scene, visual_path, audio_path) in enumerate(zip(script, visual_files, audio_files)):
            if progress_callback:
                progress_callback(f"Processing scene {i+1}/{len(script)}...")
            
            audio_clip = AudioFileClip(audio_path)
            actual_duration = audio_clip.duration
            
            if visual_path.endswith(('.mp4', '.mov', '.avi')):
                video_clip = VideoFileClip(visual_path)
                
                if video_clip.duration < actual_duration:
                    loops_needed = int(actual_duration / video_clip.duration) + 1
                    video_clip = concatenate_videoclips([video_clip] * loops_needed)
                
                video_clip = video_clip.subclipped(0, min(actual_duration, video_clip.duration))
            else:
                try:
                    img = Image.open(visual_path)
                    img = img.convert('RGB')
                    img.save(visual_path.replace('.jpg', '_converted.jpg'))
                    visual_path = visual_path.replace('.jpg', '_converted.jpg')
                except Exception as e:
                    print(f"Image conversion warning: {e}")
                
                video_clip = ImageClip(visual_path, duration=actual_duration)
            
            video_clip = self._resize_and_crop(video_clip, target_width, target_height)
            
            video_clip = self._apply_transition(video_clip, style, actual_duration)
            
            video_clip = video_clip.with_audio(audio_clip)
            
            clips.append(video_clip)
        
        if progress_callback:
            progress_callback("Concatenating all scenes...")
        
        final_video = concatenate_videoclips(clips, method="compose")
        
        output_path = self.output_dir / output_filename
        
        if progress_callback:
            progress_callback("Rendering final video (this may take a few minutes)...")
        
        final_video.write_videofile(
            str(output_path),
            codec='libx264',
            audio_codec='aac',
            fps=24,
            preset='ultrafast',
            threads=4,
            verbose=False,
            logger=None
        )
        
        for clip in clips:
            clip.close()
        final_video.close()
        
        if progress_callback:
            progress_callback("Video assembly complete!")
        
        return str(output_path)
