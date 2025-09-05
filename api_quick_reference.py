#!/usr/bin/env python3
"""
AgentryLab Python API Quick Reference

This file contains simple examples of common AgentryLab Python API patterns.
Copy and paste these examples to get started quickly!
"""

from agentrylab import init, run, list_threads


# ============================================================================
# BASIC USAGE PATTERNS
# ============================================================================

def example_1_simple_chat():
    """Example 1: Simple chat with callback"""
    # Create lab
    lab = init(
        "src/agentrylab/presets/solo_chat.yaml",
        experiment_id="my-chat",
        prompt="Tell me about your favorite hobby!"
    )
    
    # Define callback
    def callback(event):
        if event.get("event") == "provider_result":
            print(f"Agent responded: {event.get('content_len', 0)} chars")
    
    # Run with callback
    status = lab.run(rounds=3, stream=True, on_event=callback)
    
    # Show conversation
    for msg in lab.state.history:
        print(f"[{msg['role']}]: {msg['content'][:100]}...")


def example_2_resume_conversation():
    """Example 2: Resume conversation with new topic"""
    # Create lab
    lab = init(
        "src/agentrylab/presets/solo_chat.yaml",
        experiment_id="resume-demo",
        prompt="What's your favorite season?"
    )
    
    # Initial conversation
    lab.run(rounds=2)
    
    # Resume with new topic
    lab.state.objective = "Now tell me about your dream vacation!"
    lab.run(rounds=2)
    
    print(f"Total messages: {len(lab.state.history)}")


def example_3_different_presets():
    """Example 3: Try different presets"""
    presets = [
        "src/agentrylab/presets/solo_chat.yaml",
        "src/agentrylab/presets/argue.yaml",
        "src/agentrylab/presets/brainstorm.yaml",
    ]
    
    for preset in presets:
        try:
            lab = init(preset, experiment_id=f"test-{preset.split('/')[-1]}")
            status = lab.run(rounds=1)
            print(f"✅ {preset} worked!")
        except Exception as e:
            print(f"❌ {preset} failed: {e}")


def example_4_thread_management():
    """Example 4: List and manage threads"""
    # List all threads for a preset
    threads = list_threads("src/agentrylab/presets/solo_chat.yaml")
    print(f"Found {len(threads)} threads:")
    
    for thread_id, timestamp in threads:
        print(f"  - {thread_id} (updated: {timestamp})")
    
    # Create new thread
    lab = init(
        "src/agentrylab/presets/solo_chat.yaml",
        experiment_id="new-thread"
    )
    lab.run(rounds=1)


def example_5_custom_callback():
    """Example 5: Custom callback with detailed logging"""
    def detailed_callback(event):
        event_type = event.get("event")
        
        if event_type == "provider_result":
            node_id = event.get("node_id")
            role = event.get("role")
            content_len = event.get("content_len", 0)
            print(f"📝 {role} ({node_id}): {content_len} characters")
            
        elif event_type == "iteration_complete":
            iteration = event.get("iteration", 0)
            print(f"🔄 Iteration {iteration} complete")
            
        elif event_type == "run_complete":
            print("🎉 Run finished!")
            
        elif event_type == "error":
            error = event.get("error", "Unknown error")
            print(f"❌ Error: {error}")
    
    # Use the callback
    lab = init("src/agentrylab/presets/solo_chat.yaml")
    lab.run(rounds=2, stream=True, on_event=detailed_callback)


# ============================================================================
# ADVANCED PATTERNS
# ============================================================================

def example_6_error_handling():
    """Example 6: Robust error handling"""
    try:
        lab = init("src/agentrylab/presets/solo_chat.yaml")
        status = lab.run(rounds=5)
        print("✅ Success!")
        
    except FileNotFoundError:
        print("❌ Preset file not found")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def example_7_conversation_analysis():
    """Example 7: Analyze conversation"""
    lab = init("src/agentrylab/presets/solo_chat.yaml")
    lab.run(rounds=3)
    
    # Analyze conversation
    history = lab.state.history
    total_chars = sum(len(msg.get("content", "")) for msg in history)
    avg_length = total_chars / len(history) if history else 0
    
    print(f"Conversation stats:")
    print(f"  - Messages: {len(history)}")
    print(f"  - Total characters: {total_chars}")
    print(f"  - Average length: {avg_length:.1f} chars")


def example_8_multiple_topics():
    """Example 8: Multiple topics in one session"""
    lab = init("src/agentrylab/presets/solo_chat.yaml")
    
    topics = [
        "What's your favorite season?",
        "Tell me about your dream vacation!",
        "What's the best advice you've ever received?",
    ]
    
    for i, topic in enumerate(topics, 1):
        print(f"\n--- Topic {i}: {topic} ---")
        lab.state.objective = topic
        lab.run(rounds=1)
        
        # Show last message
        if lab.state.history:
            last_msg = lab.state.history[-1]
            print(f"Response: {last_msg['content'][:100]}...")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_conversation(lab):
    """Utility: Print conversation nicely"""
    print("\n💬 Conversation:")
    print("-" * 50)
    
    for i, msg in enumerate(lab.state.history, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        print(f"{i}. [{role.upper()}]: {content}")
        print()


def save_conversation(lab, filename):
    """Utility: Save conversation to file"""
    import json
    
    with open(filename, 'w') as f:
        json.dump(lab.state.history, f, indent=2)
    print(f"💾 Conversation saved to {filename}")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

if __name__ == "__main__":
    print("📚 AgentryLab Python API Quick Reference")
    print("=" * 50)
    print("This file contains examples you can copy and paste.")
    print("Uncomment the examples below to run them:")
    print()
    
    # Uncomment any of these to run:
    
    # example_1_simple_chat()
    # example_2_resume_conversation()
    # example_3_different_presets()
    # example_4_thread_management()
    # example_5_custom_callback()
    # example_6_error_handling()
    # example_7_conversation_analysis()
    # example_8_multiple_topics()
    
    print("✅ Quick reference loaded! Uncomment examples to run them.")
