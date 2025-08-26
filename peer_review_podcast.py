from crewai import Agent, Task, Crew, Process, LLM
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from dotenv import load_dotenv
import os
from tools import PodcastAudioGenerator, PodcastMixer, VoiceConfig


def setup_directories():
    """Set up organized directory structure"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    dirs = {
        'BASE': f'outputs/{timestamp}',
        'SEGMENTS': f'outputs/{timestamp}/segments',  # Individual voice segments
        'FINAL': f'outputs/{timestamp}/podcast',      # Final podcast file
        'DATA': f'outputs/{timestamp}/data'          # Metadata/JSON files
    }
    
    for directory in dirs.values():
        os.makedirs(directory, exist_ok=True)
    
    return dirs

# Load environment variables
load_dotenv()

# --- PDF Knowledge Source ---
research_paper = PDFKnowledgeSource(file_paths="workplace-prod.pdf")

# --- Pydantic Models definitions ---
class PaperSummary(BaseModel):
    """Summary of a research paper."""
    title: str = Field(..., description="Title of the research paper")                   
    main_findings: List[str] = Field(..., description="Key findings as a list of strings")
    methodology: str = Field(..., description="Research methodology as a single text block")
    key_implications: List[str] = Field(..., description="Implications as a list of strings")
    limitations: List[str] = Field(..., description="Limitations as a list of strings")
    future_work: List[str] = Field(..., description="Future research directions as a list")
    summary_date: datetime = Field(..., description="Timestamp of summary creation")

class DialogueLine(BaseModel):
    """Dialogue line for a podcast script."""
    speaker: str = Field(..., description="Name of the speaker (Julia or Guido)")
    text: str = Field(..., description="The actual dialogue line")

class PodcastScript(BaseModel):
    """Podcast script with dialogue lines."""
    dialogue: List[DialogueLine] = Field(..., description="Ordered list of dialogue lines")

class AudioGeneration(BaseModel):
    """Audio generation result with metadata."""
    segment_files: List[str] = Field(..., description="List of generated audio segment files")
    final_podcast: str = Field(..., description="Path to the final mixed podcast file")

# --- LLM Setup ---
summary_llm = LLM(
    model="openai/o1-preview",
    temperature=0.0,
)

script_llm = LLM(
    model="openai/o1-preview",
    temperature=0.3,
)

script_enhancer_llm = LLM(
    model="anthropic/claude-3-5-sonnet-20241022",
    temperature=0.7,
)

audio_llm = LLM(
    model="cerebras/llama3.3-70b",
    temperature=0.0,
)

# Create and configure tools
dirs = setup_directories()
audio_generator = PodcastAudioGenerator(output_dir=dirs['SEGMENTS'])

# Julia: Enthusiastic expert
audio_generator.add_voice(
    "Julia", 
    os.getenv("CLAUDIA_VOICE_ID"),
    VoiceConfig(
        stability=0.35,  # More variation for natural enthusiasm
        similarity_boost=0.75,  # Maintain voice consistency
        style=0.65,  # Good expressiveness without being over the top
        use_speaker_boost=True
    )
)

# Guido: Engaged and curious
audio_generator.add_voice(
    "Guido", 
    os.getenv("BEN_VOICE_ID"),
    VoiceConfig(
        stability=0.4,  # Slightly more stable but still natural
        similarity_boost=0.75,
        style=0.6,  # Balanced expressiveness
        use_speaker_boost=True
    )
)

podcast_mixer = PodcastMixer(output_dir=dirs['FINAL'])
search_tool = SerperDevTool()


# --- Agents ---
researcher = Agent(
    role="Research Analyst",
    goal="Create comprehensive yet accessible research paper summaries",
    backstory="""You're a PhD researcher with a talent for breaking down complex
    academic papers into clear, understandable summaries. You excel at identifying
    key findings and their real-world implications.""",
    verbose=True,
    llm=summary_llm
)

research_support = Agent(
    role="Research Support Specialist",
    goal="Find current context and supporting materials relevant to the paper's topic",
    backstory="""You're a versatile research assistant who excels at finding 
    supplementary information across academic fields. You have a talent for 
    connecting academic research with real-world applications, current events, 
    and practical examples, regardless of the field. You know how to find 
    credible sources and relevant discussions across various domains.""",
    verbose=True,
    tools=[search_tool],
    llm=script_enhancer_llm
)

script_writer = Agent(
    role="Podcast Script Writer",
    goal="Create engaging and constructive podcast scripts that simulate an author–reviewer discussion about a research paper",
    backstory="""You're a skilled podcast writer who specializes in turning technical
    paper reviews into insightful and natural conversations. You create dialogue
    between two people:
    - Julia: The researcher who wrote the paper, explaining their methods and findings.
    - Guido: The thoughtful reviewer who critically engages with the work,
      asking probing questions, highlighting limitations, and offering constructive improvements.
    Your job is to make this exchange both informative and conversational—something
    listeners can learn from while enjoying the dynamic interplay of critique and defense.""",
    verbose=True,
    llm=script_llm
)


script_enhancer = Agent(
    role="Podcast Script Enhancer",
    goal="Enhance podcast scripts to be more engaging while maintaining educational value",
    backstory="""You're a veteran podcast producer who specializes in making technical 
    content both entertaining and informative. You excel at adding natural humor, 
    relatable analogies, and engaging banter while ensuring the core technical content 
    remains accurate and valuable. You've worked on shows like Lex Fridman's podcast, 
    Hardcore History, and the Joe Rogan Experience, bringing their signature blend of 
    entertainment and education.""",
    verbose=True,
    llm=script_enhancer_llm 
)

audio_generator_agent = Agent(
    role="Audio Generation Specialist",
    goal="Generate high-quality podcast audio with natural-sounding voices",
    backstory="""You are an expert in audio generation and processing. You understand 
    how to generate natural-sounding voices and create professional podcast audio. You 
    consider pacing, tone, and audio quality in your productions.""",
    verbose=True,
    allow_delegation=False,
    tools=[audio_generator, podcast_mixer],
    llm=audio_llm
)

# --- Tasks ---
summary_task = Task(
    description="""Hey there, researcher! Your mission is to dive into the
    research paper provided in {paper} and uncover its core insights.
    As you create the summary, please:

    - Highlight the Big Ideas: What are the main findings and conclusions?
    - Explain the Method: Break down the study’s methodology in everyday language.
    - Discuss the Impact: What are the key implications for the field?
    - Note the Caveats: Mention any limitations or uncertainties.
    - Look Ahead: Offer some thoughts on future research directions.

    Keep your tone engaging and friendly so that an educated general audience can
    easily follow along while staying true to the technical details.""",
    expected_output="A clear, well-structured summary that covers all the critical aspects of the paper in an accessible and engaging manner.",
    agent=researcher,
    output_pydantic=PaperSummary,
    output_file="output/metadata/paper_summary.json"
)

supporting_research_task = Task(
    description="""Alright, now that we have the paper summary, let’s add some
    real-world flavor. Your task is to gather recent and credible supporting
    materials that enrich the topic. Here’s how to proceed:

    - Spot the Themes: Identify the main ideas from the paper and see how they connect with broader trends.
    - Current Developments: Find news, advancements, or case studies from the
    last couple of years that bring these ideas to life.
    - Explore Diverse Views: Look for expert opinions, debates, and alternative perspectives.
    - Real-World Examples: Gather examples from industry reports, white papers, or professional discussions.

    Your goal is to build a collection of supporting insights that help listeners
    understand how the research plays out in real life. Make sure your sources
    are recent, reliable, and add that extra context.""",
    expected_output="A curated collection of supporting materials and real-world examples that add context and depth to the research paper’s topic.",
    agent=research_support,
    context=[summary_task],
    output_file="output/metadata/supporting_research.json"
)

podcast_task = Task(
    description="""Using the paper summary and supporting research, craft a podcast-style
    conversation between Julia (the researcher) and Guido (the critical but
    constructive peer). The exchange should feel natural and conversational while
    reflecting the dynamics of academic discussion.

    Guidelines:

    Keep the Tone Academic Yet Accessible:
    - Allow the Author to explain their motivations, methods, and findings clearly,
      without being overly formal.
    - Have the Reviewer ask challenging but respectful questions, probing the
      assumptions, limitations, and potential improvements.

    Clearly Distinguish Perspectives:
    - Julia should use phrases like "In our study, we found…" or "Our approach was…"
    - Guido should use phrases like "Have you considered…" or "One limitation I see is…"

    Embrace Natural Dialogue:
    - Include interruptions, clarifications, and back-and-forth exchanges like in
      real academic discussions.
    - Use natural conversational markers such as "That’s a good point," "I see," or
      "Let me push back on that…"

    Balance Critique with Collaboration:
    - Reviewer should not only challenge but also suggest constructive directions
      or acknowledge strengths.
    - Author should occasionally defend their approach but also recognize areas
      for improvement.

    Example Flow:
    Julia: "In our study, we aimed to improve document layout understanding with AI."
    Guido: "That’s interesting. But how does your method handle noisy scans?"
    Julia: "Good question. We actually incorporated a preprocessing step to address that."
    Guido: "I like that. Though I wonder if integrating multimodal signals might strengthen the model further…"

    Your script should clearly separate the Author’s explanations from the Reviewer’s
    critiques and suggestions, while keeping it lively and engaging for listeners.""",
    expected_output="A lively and natural podcast script simulating a constructive discussion between a paper’s author and reviewer, blending clear explanations with probing critiques.",
    agent=script_writer,
    context=[summary_task, supporting_research_task],
    output_pydantic=PodcastScript,
    output_file="output/metadata/podcast_script.json"
)

enhance_script_task = Task(
    description="""Now, take the initial author–reviewer script and refine it so
    that it feels like a genuine academic yet conversational dialogue.

    - Infuse Realism: Add natural markers like "That’s interesting," "I see,"
      or "Let me clarify that…" to mimic real back-and-forth.
    - Smooth the Flow: Ensure transitions between critique and response feel
      like a genuine conversation, not a rigid Q&A.
    - Keep Roles Distinct: Author should defend, clarify, or acknowledge limitations.
      Reviewer should probe, critique, and suggest improvements.
    - Preserve Accuracy: Maintain correctness of technical details and paper content.
    - Encourage Constructive Tone: Even when critical, the Reviewer should balance
      with constructive advice.

    Important:
    - Do not rename or replace the roles (Julia, Guido).
    - Avoid stage directions (e.g., *laughs*); let tone come through in words.

    Your enhanced script should sound like you’re listening to an actual peer-review
    exchange—thoughtful, occasionally sharp, but ultimately collaborative and enlightening.""",
    expected_output="An enhanced podcast script that realistically simulates an author–reviewer exchange, engaging and educational while maintaining technical accuracy.",
    agent=script_enhancer,
    context=[summary_task, podcast_task],
    output_pydantic=PodcastScript,
    output_file="output/metadata/enhanced_podcast_script.json",
    human_input=True
)


audio_task = Task(
    description="""Generate high-quality audio for the podcast script and create the final podcast.

    The script will be provided in the context as a list of dialogue entries, each with:
    - speaker: Either "Julia" or "Guido"
    - text: The line to be spoken

    Process:
    1. Generate natural-sounding audio for each line of dialogue using appropriate voices
    2. Apply audio processing for professional quality:
       - Normalize audio levels
       - Add subtle fade effects between segments
       - Apply appropriate pacing and pauses
    3. Mix all segments into a cohesive final podcast

    Voice Assignments:
    - For Julia's lines: Use configured Julia voice
    - For Guido's lines: Use configured Guido voice

    Quality Guidelines:
    - Ensure consistent audio levels across all segments
    - Maintain natural pacing and flow
    - Create smooth transitions between speakers
    - Verify audio clarity and quality""",
    expected_output="A professional-quality podcast audio file with natural-sounding voices and smooth transitions",
    agent=audio_generator_agent,
    context=[enhance_script_task],
    output_pydantic=AudioGeneration,
    output_file="output/metadata/audio_generation_meta.json"
)
# --- Crew and Process ---
crew = Crew(
    agents=[researcher, research_support, script_writer, script_enhancer, audio_generator_agent],
    tasks=[summary_task, supporting_research_task, podcast_task, enhance_script_task, audio_task],
    process=Process.sequential,
    knowledge_sources=[research_paper],
    verbose=True
)

if __name__ == "__main__":    
    # Update task output files
    summary_task.output_file = os.path.join(dirs['DATA'], "paper_summary.json")
    supporting_research_task.output_file = os.path.join(dirs['DATA'], "supporting_research.json")
    podcast_task.output_file = os.path.join(dirs['DATA'], "podcast_script.json")
    enhance_script_task.output_file = os.path.join(dirs['DATA'], "enhanced_podcast_script.json")
    audio_task.output_file = os.path.join(dirs['DATA'], "audio_generation_meta.json")
    
    # Run the podcast generation process
    results = crew.kickoff(inputs={"paper": "workplace-prod.pdf"})