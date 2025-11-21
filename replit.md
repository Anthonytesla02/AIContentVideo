# AI Video Generator

## Overview
A modular, efficient, and cost-effective AI video generator that creates professional videos from user topics. The system generates scripts, voiceovers, visuals, and assembles complete videos with proper audio-visual synchronization.

## Recent Changes
- **2025-11-21**: Migration to Mistral AI and optimizations
  - **Migrated from Gemini to Mistral AI** for script generation (better free tier limits)
  - Phase 1: Script generation with Mistral AI using JSON mode
  - Phase 2: Per-scene audio generation with ElevenLabs
  - Phase 3: AI image generation (Replicate) with Pexels fallback
  - Phase 4: Video assembly with moviepy
  - Fixed audio-visual synchronization by using actual audio durations
  - Fixed Pexels media type detection (images vs videos)
  - Implemented prompt-based caching for AI-generated images
  - Added rate-limit handling with delays between API calls
  - Optimized video rendering with ultrafast preset
  - Added timeouts to Replicate (60s wait) and Pexels (15-30s) API calls

## Project Architecture

### Core Modules

#### video_generator.py
Handles all content generation:
- **Script Generation**: Uses Mistral AI to create scene-based scripts with structured JSON output
- **Audio Generation**: Per-scene ElevenLabs TTS for perfect timing alignment
- **Visual Generation**: Replicate SDXL for AI images with Pexels fallback
- **Caching**: MD5 hash-based prompt caching to avoid regenerating identical visuals
- **Rate Limiting**: Strategic delays (0.5s for audio, 1.5s for images) to prevent API throttling

#### video_assembler.py
Handles video composition:
- **Audio-Visual Sync**: Uses actual audio clip durations for perfect synchronization
- **Orientation Support**: Portrait (1080x1920) and Landscape (1920x1080)
- **Style-Based Transitions**: Cinematic, minimalist, vibrant, documentary fade effects
- **Media Handling**: Supports both AI images and stock videos
- **Rendering**: H.264 codec at 24fps with AAC audio

#### app.py
Streamlit web interface:
- User input form (topic, orientation, length, style)
- Real-time progress tracking for each phase
- Script preview with expandable view
- Video player and download functionality
- Comprehensive error handling with stack traces

### Dependencies

**Python Libraries:**
- `streamlit` - Web interface
- `mistralai` - Mistral AI for script generation
- `elevenlabs` - Text-to-speech voiceovers
- `replicate` - AI image generation
- `groq` - Backup LLM option (installed but not currently used)
- `pydub` - Audio processing
- `moviepy` - Video assembly
- `Pillow` - Image processing
- `requests` - API calls

**System:**
- `ffmpeg` - Video encoding/decoding

**External APIs:**
- Mistral AI API (generous free tier with better limits)
- ElevenLabs API (10k chars/month free)
- Replicate API (free tier)
- Pexels API (completely free)

## Features

### Video Configuration
- **Topics**: Any subject matter
- **Orientations**: Landscape (1920x1080) or Portrait (1080x1920)
- **Lengths**: 
  - Short form: 30-60 seconds (4-6 scenes)
  - Long form: 2-10 minutes (10-20 scenes)
- **Styles**: Cinematic, Minimalist, Vibrant, Documentary

### Performance Optimizations
1. **Prompt Caching**: Reuses AI-generated images for identical prompts
2. **Rate Limit Handling**: Delays between API calls prevent throttling
3. **Per-Scene Audio**: Generates audio per scene for accurate timing
4. **Smart Fallback**: Automatically uses Pexels when AI generation fails
5. **Media Type Detection**: Properly distinguishes images from videos

### Cost Efficiency
- Uses free/low-cost API tiers
- Caches generated assets to minimize regeneration
- Strategic API usage to stay within limits
- Can generate 3-5 videos in sequence without rate-limit failures

## User Preferences
- Default to free tier APIs whenever possible
- Prioritize quality while minimizing costs
- Clear progress feedback for long-running operations
- Error messages should be informative but user-friendly

## API Keys Required
All API keys are stored as environment secrets:
- `MISTRAL_API_KEY` - Mistral AI for script generation
- `ELEVENLABS_API_KEY` - Voice synthesis
- `REPLICATE_API_TOKEN` - AI image generation
- `PEXELS_API_KEY` - Stock media fallback

## File Structure
```
outputs/          # Generated videos and assets
cache/            # Cached AI-generated images
  image_cache.json
app.py            # Streamlit interface
video_generator.py # Core generation logic
video_assembler.py # Video composition
```

## Known Limitations
- ElevenLabs free tier: 10,000 characters/month
- Replicate may have rate limits on free tier
- Processing time: 2-5 minutes for short videos, 5-15 for long videos
- Video rendering is CPU-intensive

## Future Enhancements
- Video preview player before download
- Batch video generation queue
- User dashboard for generation history
- Background music integration
- Subtitle overlays
- Custom transitions
- Cost tracking dashboard
