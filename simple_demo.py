#!/usr/bin/env python3
"""
Simple AgentryLab Python API Demo

A straightforward example showing the basic AgentryLab Python API usage.
"""

import time
from agentrylab import init, run, list_threads


def simple_callback(event):
    """Simple callback to show events as they happen"""
    event_type = event.get("event", "unknown")
    
    if event_type == "provider_result":
        node_id = event.get("node_id", "unknown")
        role = event.get("role", "unknown")
        print(f"  📝 {role} ({node_id}) responded")
    elif event_type == "iteration_complete":
        iteration = event.get("iteration", 0)
        print(f"  🔄 Iteration {iteration} done")


def main():
    """Main demo function"""
    print("🚀 AgentryLab Python API Demo")
    print("=" * 50)
    
    thread_id = f"demo-{int(time.time())}"
    
    # Step 1: Create lab
    print("\n1️⃣ Creating lab...")
    lab = init(
        "src/agentrylab/presets/solo_chat.yaml",
        experiment_id=thread_id,
        prompt="Tell me about your favorite season!"
    )
    print("✅ Lab created!")
    
    # Step 2: Run with callback
    print("\n2️⃣ Running lab with callback...")
    status = lab.run(
        rounds=3,
        stream=True,
        on_event=simple_callback
    )
    print("✅ Lab execution completed!")
    
    # Step 3: Show outputs
    print("\n3️⃣ Showing conversation...")
    history = lab.state.history
    
    print(f"\n💬 Conversation ({len(history)} messages):")
    print("-" * 40)
    
    for i, message in enumerate(history, 1):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        # Show first 100 characters
        preview = content[:100] + "..." if len(content) > 100 else content
        print(f"{i}. [{role.upper()}]: {preview}")
    
    # Step 4: Resume with new topic
    print("\n4️⃣ Resuming with new topic...")
    lab.state.objective = "Now tell me about your favorite hobby!"
    status = lab.run(
        rounds=2,
        stream=True,
        on_event=simple_callback
    )
    print("✅ Resume completed!")
    
    # Step 5: Show final conversation
    print("\n5️⃣ Final conversation...")
    final_history = lab.state.history
    
    print(f"\n💬 Complete conversation ({len(final_history)} messages):")
    print("=" * 50)
    
    for i, message in enumerate(final_history, 1):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        print(f"\nMessage {i} [{role.upper()}]:")
        print(content)
        print("-" * 30)
    
    # Step 6: List threads
    print("\n6️⃣ Listing threads...")
    threads = list_threads("src/agentrylab/presets/solo_chat.yaml")
    print(f"Found {len(threads)} threads:")
    for thread_id, timestamp in threads:
        print(f"  - {thread_id} (last updated: {timestamp})")
    
    print("\n🎉 Demo finished successfully!")


if __name__ == "__main__":
    main()
