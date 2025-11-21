import streamlit as st
import os
import json
from pathlib import Path
from video_generator import VideoGenerator
from video_assembler import VideoAssembler
from database import init_db, save_video_to_history, get_all_videos, get_video_by_id, get_total_costs
import traceback


st.set_page_config(
    page_title="AI Video Generator",
    page_icon="🎬",
    layout="wide"
)

init_db()

st.title("🎬 AI Video Generator")
st.markdown("Create professional videos from any topic using AI")

page = st.sidebar.radio("Navigation", ["🎬 Create Video", "📊 History & Dashboard", "💰 Cost Tracking"])


@st.cache_resource
def get_generator():
    return VideoGenerator()

@st.cache_resource
def get_assembler():
    return VideoAssembler()


def generate_video_pipeline(topic, orientation, length, style):
    generator = get_generator()
    assembler = get_assembler()
    
    progress_container = st.empty()
    status_text = st.empty()
    
    try:
        script = generator.generate_script(
            user_topic=topic,
            video_orientation=orientation,
            video_length=length,
            style=style,
            progress_callback=lambda msg: status_text.info(f"📝 {msg}")
        )
        
        st.session_state.script = script
        
        with st.expander("📄 View Generated Script", expanded=False):
            for scene in script:
                st.markdown(f"**Scene {scene['scene_number']}** ({scene['duration_seconds']}s)")
                st.write(f"*Narration:* {scene['narration']}")
                st.write(f"*Visual:* {scene['visual_description']}")
                st.divider()
        
        audio_files = generator.generate_audio(
            script=script,
            progress_callback=lambda msg: status_text.info(f"🎵 {msg}")
        )
        
        visual_files = generator.generate_visuals(
            script=script,
            orientation=orientation,
            style=style,
            progress_callback=lambda msg: status_text.info(f"🎨 {msg}")
        )
        
        output_filename = f"video_{topic.replace(' ', '_')[:30]}_{orientation}_{style}.mp4"
        
        final_video_path = assembler.assemble_video(
            script=script,
            visual_files=visual_files,
            audio_files=audio_files,
            orientation=orientation,
            style=style,
            output_filename=output_filename,
            progress_callback=lambda msg: status_text.info(f"🎬 {msg}")
        )
        
        status_text.success("✅ Video generation complete!")
        
        return final_video_path
        
    except Exception as e:
        status_text.error(f"❌ Error: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())
        return None


col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Video Configuration")
    
    topic = st.text_input(
        "Topic",
        placeholder="e.g., The History of Space Exploration, Benefits of Meditation, etc.",
        help="What should your video be about?"
    )
    
    orientation = st.selectbox(
        "Orientation",
        options=["landscape", "portrait"],
        help="Choose video aspect ratio"
    )
    
    length = st.selectbox(
        "Length",
        options=["short_form", "long_form"],
        format_func=lambda x: "Short Form (30-60 seconds)" if x == "short_form" else "Long Form (2-10 minutes)",
        help="Video duration"
    )
    
    style = st.selectbox(
        "Style",
        options=["cinematic", "minimalist", "vibrant", "documentary"],
        help="Visual aesthetic of your video"
    )
    
    generate_button = st.button("🎬 Generate Video", type="primary", use_container_width=True)

with col2:
    st.subheader("Quick Guide")
    st.markdown("""
    **Steps:**
    1. Enter your topic
    2. Select orientation & length
    3. Choose visual style
    4. Click Generate Video
    
    **Processing Time:**
    - Short: 2-5 minutes
    - Long: 5-15 minutes
    
    **Features:**
    - AI-generated scripts
    - Professional voiceovers
    - AI images or stock footage
    - Automatic editing
    """)


if generate_button:
    if not topic:
        st.error("Please enter a topic for your video")
    else:
        st.divider()
        st.subheader("🎥 Generating Your Video")
        
        with st.spinner("Processing..."):
            video_path = generate_video_pipeline(topic, orientation, length, style)
            
            if video_path and Path(video_path).exists():
                st.divider()
                st.subheader("✅ Your Video is Ready!")
                
                col_vid1, col_vid2 = st.columns([2, 1])
                
                with col_vid1:
                    st.video(video_path)
                
                with col_vid2:
                    st.markdown("**Video Details:**")
                    st.write(f"📏 Orientation: {orientation.title()}")
                    st.write(f"⏱️ Length: {length.replace('_', ' ').title()}")
                    st.write(f"🎨 Style: {style.title()}")
                    
                    if 'script' in st.session_state:
                        st.write(f"🎬 Scenes: {len(st.session_state.script)}")
                    
                    with open(video_path, 'rb') as video_file:
                        st.download_button(
                            label="⬇️ Download Video",
                            data=video_file,
                            file_name=Path(video_path).name,
                            mime="video/mp4",
                            use_container_width=True
                        )


st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <small>Powered by Gemini Flash, ElevenLabs, Replicate & Pexels</small>
</div>
""", unsafe_allow_html=True)


if 'script' not in st.session_state:
    st.session_state.script = None
