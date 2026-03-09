"""
Streamlit Data Dashboard for AI Quant Observatory
"""
import streamlit as st
import pandas as pd
import json
import random
from pathlib import Path
from datetime import datetime
import sys

# Set page configuration
st.set_page_config(
    layout="wide",
    page_title="AI Quant Observatory",
    page_icon="📊"
)

# Add title and description
st.title("📊 AI Quant Observatory")
st.markdown("""
Real-time monitoring dashboard for the AI-driven quantitative trading evolution engine.
Track fitness progression, explore generation details, and analyze failed strategies.
""")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a view:",
    ["Macro Overview", "Generation Explorer", "The Graveyard"]
)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATION_HISTORY_PATH = PROJECT_ROOT / "user_data" / "logs" / "generation_history.json"
GRAVEYARD_PATH = PROJECT_ROOT / "user_data" / "strategies" / "graveyard"
AI_TRANSCRIPTS_PATH = PROJECT_ROOT / "user_data" / "logs" / "ai_transcripts"

# Helper function to load generation history
@st.cache_data
def load_generation_history():
    """Load and parse generation history JSON file."""
    if GENERATION_HISTORY_PATH.exists():
        try:
            with open(GENERATION_HISTORY_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading generation history: {e}")
            return []
    else:
        st.warning(f"Generation history file not found at: {GENERATION_HISTORY_PATH}")
        return []

# Helper function to get AI transcript for a generation
def get_ai_transcript(gen_number):
    """Load AI transcript for a specific generation if it exists."""
    transcript_path = AI_TRANSCRIPTS_PATH / f"gen_{gen_number}.json"
    if transcript_path.exists():
        try:
            with open(transcript_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    return None

# Helper function to scan graveyard
@st.cache_data
def scan_graveyard():
    """Scan the graveyard directory for JSON files."""
    if not GRAVEYARD_PATH.exists():
        return []
    
    graveyard_files = list(GRAVEYARD_PATH.glob("*.json"))
    return graveyard_files

# MACRO OVERVIEW PAGE
if page == "Macro Overview":
    st.header("📈 Macro Overview")
    
    # Load generation history
    history = load_generation_history()
    
    if not history:
        st.info("No generation history data available yet.")
    else:
        # Create metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        # Total generations
        total_generations = len(history)
        col1.metric("Total Generations", total_generations)
        
        # Total execution time
        total_execution_time = sum(gen.get("execution_time_seconds", 0) for gen in history)
        col2.metric("Total Execution Time", f"{total_execution_time:.0f} sec")
        
        # Average execution time per generation
        avg_execution_time = total_execution_time / total_generations if total_generations > 0 else 0
        col3.metric("Avg Time per Gen", f"{avg_execution_time:.1f} sec")
        
        # Find best fitness across all generations
        best_fitness = 0
        best_gen = 0
        for gen in history:
            slots = gen.get("slots", [])
            for slot in slots:
                fitness = slot.get("fitness", 0)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_gen = gen.get("gen_number", 0)
        
        col4.metric("Best Fitness", f"{best_fitness:.4f}", f"Gen {best_gen}")
        
        st.divider()
        
        # Prepare data for fitness chart
        st.subheader("King's Fitness Progression")
        
        # Extract highest fitness from each generation
        fitness_data = []
        for gen in history:
            gen_num = gen.get("gen_number", 0)
            slots = gen.get("slots", [])
            
            # Find the highest fitness in this generation
            max_fitness = 0
            for slot in slots:
                fitness = slot.get("fitness", 0)
                if fitness > max_fitness:
                    max_fitness = fitness
            
            fitness_data.append({
                "Generation": gen_num,
                "Fitness": max_fitness,
                "Timestamp": gen.get("timestamp", "")
            })
        
        if fitness_data:
            # Create DataFrame for chart
            df_fitness = pd.DataFrame(fitness_data)
            df_fitness.set_index("Generation", inplace=True)
            
            # Display line chart
            st.line_chart(df_fitness["Fitness"])
            
            # Show raw data in expander
            with st.expander("View Raw Fitness Data"):
                st.dataframe(df_fitness)
        else:
            st.info("No fitness data available for charting.")
        
        st.divider()
        
        # Generation statistics table
        st.subheader("Generation Statistics")
        
        # Prepare detailed statistics
        stats_data = []
        for gen in history:
            gen_num = gen.get("gen_number", 0)
            slots = gen.get("slots", [])
            
            # Count different statuses
            status_counts = {}
            fitness_values = []
            smoke_test_results = []
            
            for slot in slots:
                status = slot.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                
                fitness = slot.get("fitness", 0)
                if fitness > 0:
                    fitness_values.append(fitness)
                
                smoke_test = slot.get("smoke_test")
                if smoke_test:
                    smoke_test_results.append(smoke_test)
            
            # Calculate statistics
            avg_fitness = sum(fitness_values) / len(fitness_values) if fitness_values else 0
            passed_smoke = smoke_test_results.count("passed") if smoke_test_results else 0
            total_smoke = len(smoke_test_results)
            
            stats_data.append({
                "Generation": gen_num,
                "King Fitness": max(fitness_values) if fitness_values else 0,
                "Avg Fitness": f"{avg_fitness:.4f}",
                "Kings": status_counts.get("king", 0),
                "Candidates": status_counts.get("candidate", 0),
                "Outsiders": status_counts.get("outsider", 0),
                "Smoke Passed": f"{passed_smoke}/{total_smoke}" if total_smoke > 0 else "N/A",
                "Exec Time (s)": f"{gen.get('execution_time_seconds', 0):.1f}"
            })
        
        if stats_data:
            df_stats = pd.DataFrame(stats_data)
            st.dataframe(df_stats, use_container_width=True)
        else:
            st.info("No detailed statistics available.")

# GENERATION EXPLORER PAGE
elif page == "Generation Explorer":
    st.header("🔍 Generation Explorer")
    
    # Load generation history
    history = load_generation_history()
    
    if not history:
        st.info("No generation history data available yet.")
    else:
        # Create generation selector
        gen_numbers = [gen.get("gen_number", 0) for gen in history]
        selected_gen = st.selectbox(
            "Select Generation:",
            gen_numbers,
            format_func=lambda x: f"Generation {x}"
        )
        
        # Find selected generation
        selected_gen_data = next((gen for gen in history if gen.get("gen_number") == selected_gen), None)
        
        if selected_gen_data:
            # Display generation metadata
            col1, col2, col3 = st.columns(3)
            col1.metric("Generation", selected_gen)
            col2.metric("Execution Time", f"{selected_gen_data.get('execution_time_seconds', 0):.1f} sec")
            col3.metric("Timestamp", selected_gen_data.get('timestamp', 'N/A')[:19])
            
            st.divider()
            
            # Display slots data
            st.subheader("Slot Details")
            slots = selected_gen_data.get("slots", [])
            
            if slots:
                # Prepare DataFrame for slots
                slots_data = []
                for slot in slots:
                    slots_data.append({
                        "Slot": slot.get("slot", 0),
                        "Lineage ID": slot.get("lineage_id", "unknown")[:12] + "...",
                        "Status": slot.get("status", "unknown"),
                        "Fitness": f"{slot.get('fitness', 0):.4f}",
                        "Smoke Test": slot.get("smoke_test", "N/A"),
                        "Full Lineage ID": slot.get("lineage_id", "unknown")
                    })
                
                df_slots = pd.DataFrame(slots_data)
                
                # Display the dataframe
                st.dataframe(df_slots, use_container_width=True)
                
                # Allow user to view full lineage ID
                with st.expander("View Full Lineage IDs"):
                    for slot in slots:
                        st.text(f"Slot {slot.get('slot', 0)}: {slot.get('lineage_id', 'unknown')}")
            else:
                st.info("No slot data available for this generation.")
            
            st.divider()
            
            # Check for AI transcript
            st.subheader("AI Transcript")
            transcript = get_ai_transcript(selected_gen)
            
            if transcript:
                with st.expander("View AI Transcript"):
                    st.json(transcript)
                
                # Try to extract and display key information
                if isinstance(transcript, dict):
                    # Display system prompt if available
                    if "system_prompt" in transcript:
                        st.markdown("**System Prompt:**")
                        st.text(transcript["system_prompt"][:500] + "..." if len(transcript["system_prompt"]) > 500 else transcript["system_prompt"])
                    
                    # Display response if available
                    if "response" in transcript:
                        st.markdown("**AI Response:**")
                        st.text(transcript["response"][:1000] + "..." if len(transcript["response"]) > 1000 else transcript["response"])
            else:
                st.info(f"No AI transcript found for Generation {selected_gen}.")
        else:
            st.warning(f"Could not find data for Generation {selected_gen}.")

# THE GRAVEYARD PAGE
elif page == "The Graveyard":
    st.header("⚰️ The Graveyard")
    st.markdown("""
    Strategies that failed the smoke test or were otherwise retired from the population.
    These genomes represent logic that didn't make the cut.
    """)
    
    # Scan graveyard
    graveyard_files = scan_graveyard()
    
    # Display metrics
    col1, col2 = st.columns(2)
    col1.metric("Total Graveyard Files", len(graveyard_files))
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in graveyard_files) if graveyard_files else 0
    col2.metric("Total Size", f"{total_size / 1024:.1f} KB")
    
    st.divider()
    
    if not graveyard_files:
        st.info("The graveyard is empty. No failed strategies yet!")
    else:
        # Show random sample
        st.subheader("Random Sample of Failed Strategies")
        
        # Select random sample (max 5)
        sample_size = min(5, len(graveyard_files))
        sample_files = random.sample(graveyard_files, sample_size) if graveyard_files else []
        
        for i, file_path in enumerate(sample_files):
            try:
                with open(file_path, 'r') as f:
                    genome_data = json.load(f)
                
                # Create expander for each file
                with st.expander(f"File: {file_path.name}"):
                    # Display basic info
                    col1, col2 = st.columns(2)
                    
                    lineage_id = genome_data.get("lineage_id", "unknown")
                    col1.metric("Lineage ID", lineage_id[:12] + "..." if len(lineage_id) > 12 else lineage_id)
                    
                    fitness = genome_data.get("fitness", 0)
                    col2.metric("Fitness", f"{fitness:.4f}")
                    
                    # Display entry tree structure
                    st.markdown("**Entry Tree Structure:**")
                    entry_tree = genome_data.get("entry_tree", {})
                    
                    # Try to display in a readable format
                    if entry_tree:
                        # Function to recursively display tree
                        def display_tree(node, depth=0):
                            indent = "  " * depth
                            if "primitive" in node:
                                primitive = node.get("primitive", "unknown")
                                params = node.get("parameters", {})
                                st.text(f"{indent}├─ Primitive: {primitive}")
                                for key, value in params.items():
                                    st.text(f"{indent}│  └─ {key}: {value}")
                            elif "operator" in node:
                                operator = node.get("operator", "unknown")
                                st.text(f"{indent}├─ Operator: {operator}")
                                children = node.get("children", [])
                                for child in children:
                                    display_tree(child, depth + 1)
                            elif "constant" in node:
                                constant = node.get("constant", "unknown")
                                st.text(f"{indent}└─ Constant: {constant}")
                            elif "left" in node or "right" in node:
                                st.text(f"{indent}├─ Comparator Node")
                                if "left" in node:
                                    st.text(f"{indent}│  ├─ Left:")
                                    display_tree(node["left"], depth + 2)
                                if "right" in node:
                                    st.text(f"{indent}│  └─ Right:")
                                    display_tree(node["right"], depth + 2)
                        
                        display_tree(entry_tree)
                    else:
                        st.info("No entry tree data available.")
                    
                    # Show raw JSON in another expander
                    with st.expander("View Raw JSON"):
                        st.json(genome_data)
            
            except Exception as e:
                st.error(f"Error loading {file_path.name}: {e}")
        
        st.divider()
        
        # Show all files in a table
        st.subheader("All Graveyard Files")
        
        files_data = []
        for file_path in graveyard_files:
            try:
                file_stat = file_path.stat()
                files_data.append({
                    "Filename": file_path.name,
                    "Size (KB)": f"{file_stat.st_size / 1024:.1f}",
                    "Modified": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
            except:
                files_data.append({
                    "Filename": file_path.name,
                    "Size (KB)": "N/A",
                    "Modified": "N/A"
                })
        
        if files_data:
            df_files = pd.DataFrame(files_data)
            st.dataframe(df_files, use_container_width=True)
        else:
            st.info("No file metadata available.")

# Footer
st.divider()
st.caption("AI Quant Observatory Dashboard • Built with Streamlit • Data updates automatically")
