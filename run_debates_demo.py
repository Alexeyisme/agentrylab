#!/usr/bin/env python3
"""
Debates Demo - Direct AgentryLab Testing Tool

This script provides a clean way to test AgentryLab's debates preset
without the complexity of the Telegram bot integration. Useful for:

- Debugging core engine issues
- Testing conversation quality  
- Validating fixes and changes
- Performance benchmarking
- Feature development testing

Usage: python3 run_debates_demo.py

The script will prompt you for a debate topic and run a full conversation
using the AgentryLab core engine with the debates preset.
"""
"""
Debates Demo - Run the debates preset using the Telegram API

This demo showcases the complete debate functionality including:
- Multi-agent debate coordination (Pro, Con, Moderator, Summarizer)
- Real-time event streaming
- Comprehensive final summaries with evidence and recommendations
- Progress tracking and analytics

Key Features Demonstrated:
- Async event streaming for real-time conversation monitoring
- Final summary generation with run_on_last=true configuration
- Evidence-based arguments with web search integration
- Structured debate outcomes with next steps and open questions

The debates preset automatically generates comprehensive final summaries that include:
- Clear outcome statements
- Key arguments from both sides
- Supporting evidence with URLs
- Open questions for further discussion
- Actionable next steps and recommendations
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    if key.strip() == 'OPENAI_API_KEY':
                        os.environ['OPENAI_API_KEY'] = value
                        break
    except Exception as e:
        print(f"⚠️ Error loading .env file: {e}")

from agentrylab.telegram.adapter import TelegramAdapter

async def run_debates_demo():
    """Run a debates demonstration."""
    
    print("🎭 AgentryLab Debates Demo")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found. Please set it in your .env file.")
        return
    
    print(f"✅ OpenAI API key found ({len(api_key)} characters)")
    
    # Initialize adapter
    adapter = TelegramAdapter()
    
    # Debate topics to choose from
    topics = [
        "Should artificial intelligence be regulated by governments?",
        "Is remote work better than office work?",
        "Should cryptocurrency replace traditional banking?",
        "Is social media harmful to society?",
        "Should we colonize Mars?",
        "Is universal basic income a good idea?",
        "Should college education be free?",
        "Is nuclear energy the solution to climate change?"
    ]
    
    # Select a topic
    selected_topic = topics[0]  # AI regulation
    print(f"\n🎯 Debate Topic: {selected_topic}")
    
    # Start conversation
    print("\n🚀 Starting debate conversation...")
    conversation_id = adapter.start_conversation(
        preset_id="src/agentrylab/presets/debates.yaml",
        topic=selected_topic,
        user_id="demo_user",
        conversation_id="debates_demo_001",
        resume=False
    )
    
    print(f"✅ Conversation started: {conversation_id}")
    
    # Set rounds for a good debate
    adapter.set_conversation_rounds(conversation_id, 4)
    print("✅ Set to 4 rounds for a comprehensive debate")
    
    # Show initial status
    progress = adapter.get_conversation_progress(conversation_id)
    print(f"📊 Initial Progress: {progress['progress_percent']:.1f}% ({progress['current_iteration']}/{progress['max_rounds']})")
    
    # Start the conversation task manually to ensure it runs
    if conversation_id not in adapter._running_tasks:
        task = asyncio.create_task(adapter._run_conversation(conversation_id))
        adapter._running_tasks[conversation_id] = task
        print("✅ Started conversation task")
    
    # Run the debate
    print("\n🎭 Starting the debate...")
    print("-" * 50)
    
    event_count = 0
    conversation_completed = False
    
    async for event in adapter.stream_events(conversation_id):
        event_count += 1
        timestamp = event.timestamp.strftime("%H:%M:%S")
        
        if event.event_type == "conversation_started":
            print(f"[{timestamp}] 🚀 {event.content}")
            
        elif event.event_type == "agent_message":
            agent_name = event.agent_id or "Unknown"
            role = event.role or "agent"
            
            # Format the message nicely
            content = event.content
            if len(content) > 200:
                content = content[:200] + "..."
            
            # Add emoji based on agent
            emoji = "🔵" if agent_name == "pro" else "🔴" if agent_name == "con" else "👨‍⚖️" if agent_name == "moderator" else "📝"
            
            print(f"[{timestamp}] {emoji} {agent_name.upper()} ({role}):")
            print(f"    {content}")
            print()
            
        elif event.event_type == "moderator_action":
            print(f"[{timestamp}] 👨‍⚖️ MODERATOR ACTION:")
            moderator_content = str(event.content)
            if len(moderator_content) > 150:
                moderator_content = moderator_content[:150] + "..."
            print(f"    {moderator_content}")
            print()
            
        elif event.event_type == "summary_update":
            print(f"[{timestamp}] 📝 SUMMARY UPDATE:")
            summary_content = event.content
            if len(summary_content) > 200:
                summary_content = summary_content[:200] + "..."
            print(f"    {summary_content}")
            print()
            
        elif event.event_type == "conversation_completed":
            print(f"[{timestamp}] ✅ {event.content}")
            conversation_completed = True
            # Wait a moment for final summary to complete
            await asyncio.sleep(3)
            break
        
        # Limit for demo (increased to allow for final summary)
        if event_count >= 100:
            print(f"[{timestamp}] ⏹️ Demo limit reached")
            break
    
    # If conversation didn't complete naturally, wait for it to finish
    if not conversation_completed:
        print("⏳ Waiting for conversation to complete...")
        # Wait for the conversation task to finish
        if conversation_id in adapter._running_tasks:
            try:
                await asyncio.wait_for(adapter._running_tasks[conversation_id], timeout=30)
                print("✅ Conversation task completed")
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for conversation completion")
        await asyncio.sleep(2)
    
    # Show final results
    print("\n" + "=" * 50)
    print("🎊 DEBATE COMPLETED!")
    print("=" * 50)
    
    # Get final analytics
    analytics = adapter.get_conversation_analytics(conversation_id)
    progress = adapter.get_conversation_progress(conversation_id)
    health = adapter.get_system_health(conversation_id)
    
    print(f"📊 Final Progress: {progress['progress_percent']:.1f}% ({progress['current_iteration']}/{progress['max_rounds']})")
    print(f"📈 Total Messages: {analytics['total_messages']}")
    print(f"🤖 Agent Messages: {analytics['agent_messages']}")
    print(f"👨‍⚖️ Moderator Messages: {analytics['moderator_messages']}")
    print(f"🛠️ Tool Calls: {analytics['total_tool_calls']}")
    print(f"🏥 System Health: {health['health_score']}/100 ({health['health_status']})")
    print(f"⏱️ Duration: {analytics['duration_seconds']:.1f} seconds")
    
    # Get final comprehensive summary from the summarizer
    print("\n📝 FINAL DEBATE SUMMARY:")
    print("=" * 50)
    
    final_summary = adapter.get_final_summary(conversation_id)
    if final_summary:
        print(final_summary)
        print("\n💡 This comprehensive summary includes:")
        print("   • Clear outcome statement")
        print("   • Key arguments from both sides")
        print("   • Supporting evidence with URLs")
        print("   • Open questions for further discussion")
        print("   • Actionable next steps and recommendations")
    else:
        print("No final summary found from summarizer")
        # Fallback to the basic summary method
        summary = adapter.get_conversation_summary(conversation_id)
        if summary:
            print(f"Running summary: {summary}")
        else:
            print("No summary available")
    
    # Get technical summary report
    print("\n📋 TECHNICAL SUMMARY REPORT:")
    print("-" * 30)
    report = adapter.get_conversation_summary_report(conversation_id)
    print(report)
    
    # Cleanup
    print(f"\n🧹 Cleaning up conversation...")
    adapter.cleanup_conversation(conversation_id)
    print("✅ Cleanup completed")
    
    print(f"\n🎉 Debates demo completed successfully!")
    print(f"💡 You can modify the topic, rounds, or add user input to customize the debate!")

if __name__ == "__main__":
    try:
        asyncio.run(run_debates_demo())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()




