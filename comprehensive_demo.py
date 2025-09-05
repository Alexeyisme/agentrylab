#!/usr/bin/env python3
"""
Comprehensive AgentryLab Python API Demo

This demo shows all the key features of the AgentryLab Python API:
- Creating labs with different presets
- Running with callbacks and streaming
- Resuming conversations
- Managing threads
- Error handling
- Different configuration options
"""

import time
from agentrylab import init, run, list_threads


def event_callback(event):
    """Enhanced callback to show detailed events"""
    event_type = event.get("event", "unknown")
    
    if event_type == "provider_result":
        node_id = event.get("node_id", "unknown")
        role = event.get("role", "unknown")
        content_len = event.get("content_len", 0)
        print(f"  📝 {role} ({node_id}): {content_len} chars")
        
    elif event_type == "iteration_complete":
        iteration = event.get("iteration", 0)
        print(f"  🔄 Iteration {iteration} complete")
        
    elif event_type == "run_complete":
        print(f"  🎉 Run completed!")
        
    elif event_type == "error":
        error = event.get("error", "Unknown error")
        print(f"  ❌ Error: {error}")
        
    else:
        print(f"  📡 Event: {event_type}")


def demo_basic_usage():
    """Demo 1: Basic usage with simple chat"""
    print("\n" + "="*60)
    print("DEMO 1: BASIC USAGE")
    print("="*60)
    
    # Create lab with simple chat preset
    print("\n🔧 Creating lab with solo_chat preset...")
    lab = init(
        "src/agentrylab/presets/solo_chat.yaml",
        experiment_id=f"basic-{int(time.time())}",
        prompt="Tell me about your favorite type of music!"
    )
    print("✅ Lab created successfully!")
    
    # Run with callback
    print("\n🚀 Running lab with event streaming...")
    status = lab.run(
        rounds=2,
        stream=True,
        on_event=event_callback
    )
    print(f"✅ Completed! Status: {status}")
    
    # Show conversation
    print("\n💬 Conversation:")
    for i, msg in enumerate(lab.state.history, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:100]
        print(f"  {i}. [{role.upper()}]: {content}...")
    
    return lab


def demo_resume_conversation():
    """Demo 2: Resume conversation with new topic"""
    print("\n" + "="*60)
    print("DEMO 2: RESUME CONVERSATION")
    print("="*60)
    
    thread_id = f"resume-{int(time.time())}"
    
    # Initial run
    print("\n🔧 Creating lab for resume demo...")
    lab = init(
        "src/agentrylab/presets/solo_chat.yaml",
        experiment_id=thread_id,
        prompt="What's your favorite season?"
    )
    
    print("\n🚀 Initial run...")
    lab.run(rounds=2, stream=True, on_event=event_callback)
    
    # Resume with new topic
    print("\n🔄 Resuming with new topic...")
    lab.state.objective = "Now tell me about your dream vacation!"
    lab.run(rounds=2, stream=True, on_event=event_callback)
    
    print(f"\n💬 Total conversation ({len(lab.state.history)} messages):")
    for i, msg in enumerate(lab.state.history, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:80]
        print(f"  {i}. [{role.upper()}]: {content}...")
    
    return lab


def demo_different_presets():
    """Demo 3: Try different presets"""
    print("\n" + "="*60)
    print("DEMO 3: DIFFERENT PRESETS")
    print("="*60)
    
    presets = [
        ("solo_chat.yaml", "Tell me about your favorite hobby!"),
        ("argue.yaml", "Should remote work become the standard?"),
    ]
    
    for preset_file, prompt in presets:
        print(f"\n🔧 Testing preset: {preset_file}")
        try:
            lab = init(
                f"src/agentrylab/presets/{preset_file}",
                experiment_id=f"preset-{int(time.time())}",
                prompt=prompt
            )
            
            print(f"🚀 Running {preset_file}...")
            status = lab.run(rounds=1, stream=True, on_event=event_callback)
            print(f"✅ {preset_file} completed!")
            
        except Exception as e:
            print(f"❌ Error with {preset_file}: {e}")


def demo_thread_management():
    """Demo 4: Thread management"""
    print("\n" + "="*60)
    print("DEMO 4: THREAD MANAGEMENT")
    print("="*60)
    
    # List all threads
    print("\n📋 Listing all threads...")
    threads = list_threads("src/agentrylab/presets/solo_chat.yaml")
    print(f"Found {len(threads)} threads:")
    
    for thread_id, timestamp in threads[-5:]:  # Show last 5
        print(f"  - {thread_id}")
        print(f"    Last updated: {time.ctime(timestamp)}")
    
    # Create a new thread
    print(f"\n🔧 Creating new thread...")
    new_thread_id = f"management-{int(time.time())}"
    lab = init(
        "src/agentrylab/presets/solo_chat.yaml",
        experiment_id=new_thread_id,
        prompt="What's the best advice you've ever received?"
    )
    
    print(f"✅ Created thread: {new_thread_id}")
    
    # Run it
    lab.run(rounds=1, stream=True, on_event=event_callback)
    
    # List threads again to see the new one
    print(f"\n📋 Threads after creating new one:")
    updated_threads = list_threads("src/agentrylab/presets/solo_chat.yaml")
    print(f"Now have {len(updated_threads)} threads")
    
    return lab


def demo_error_handling():
    """Demo 5: Error handling"""
    print("\n" + "="*60)
    print("DEMO 5: ERROR HANDLING")
    print("="*60)
    
    # Try to load non-existent preset
    print("\n🔧 Testing error handling...")
    try:
        lab = init("non_existent_preset.yaml")
        print("❌ Should have failed!")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")
    
    # Try to run with invalid parameters
    try:
        lab = init(
            "src/agentrylab/presets/solo_chat.yaml",
            experiment_id=f"error-{int(time.time())}"
        )
        lab.run(rounds=-1)  # Invalid rounds
        print("❌ Should have failed!")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")


def main():
    """Run all demos"""
    print("🚀 AgentryLab Comprehensive Python API Demo")
    print("This demo shows all the key features of the AgentryLab Python API")
    
    try:
        # Run all demos
        demo_basic_usage()
        demo_resume_conversation()
        demo_different_presets()
        demo_thread_management()
        demo_error_handling()
        
        print("\n" + "="*60)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nKey takeaways:")
        print("✅ Easy to create and run labs")
        print("✅ Real-time event streaming with callbacks")
        print("✅ Simple conversation resumption")
        print("✅ Thread management and persistence")
        print("✅ Robust error handling")
        print("✅ Works with different presets")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
