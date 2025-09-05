#!/usr/bin/env python3
"""
AgentryLab Python API Demo Script

This script demonstrates the complete AgentryLab Python API workflow:
1. Create a lab with simple chat preset
2. Run it with callbacks
3. Show outputs
4. Resume the conversation
5. View outputs
6. Clean up thread

Run with: python demo_agentrylab_api.py
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from agentrylab import Lab, LabConfig
from agentrylab.config.loader import load_preset


class AgentryLabDemo:
    """Demo class showing AgentryLab Python API usage"""
    
    def __init__(self):
        self.lab = None
        self.thread_id = f"demo-{int(time.time())}"
        self.preset_path = "src/agentrylab/presets/solo_chat.yaml"
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
        
    def print_step(self, step: str):
        """Print a step indicator"""
        print(f"\n🔹 {step}")
        
    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
        
    def print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  {message}")
        
    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")

    def callback_handler(self, event: Dict[str, Any]):
        """Callback function to handle events during lab execution"""
        event_type = event.get("event", "unknown")
        
        if event_type == "provider_result":
            node_id = event.get("node_id", "unknown")
            role = event.get("role", "unknown")
            content_len = event.get("content_len", 0)
            print(f"  📝 {role} ({node_id}): {content_len} characters")
            
        elif event_type == "iteration_complete":
            iteration = event.get("iteration", 0)
            print(f"  🔄 Iteration {iteration} complete")
            
        elif event_type == "run_complete":
            print(f"  🎉 Run complete!")
            
        else:
            print(f"  📡 Event: {event_type}")

    async def step1_create_lab(self):
        """Step 1: Create lab with simple chat preset"""
        self.print_header("STEP 1: CREATE LAB")
        
        try:
            # Load the preset configuration
            self.print_step("Loading preset configuration...")
            preset_config = load_preset(self.preset_path)
            self.print_success(f"Loaded preset: {preset_config.name}")
            
            # Create lab configuration
            self.print_step("Creating lab configuration...")
            config = LabConfig(
                preset=preset_config,
                thread_id=self.thread_id,
                max_iterations=3
            )
            self.print_success(f"Created config for thread: {self.thread_id}")
            
            # Create the lab
            self.print_step("Creating lab instance...")
            self.lab = Lab(config)
            self.print_success("Lab created successfully!")
            
            return True
            
        except Exception as e:
            self.print_error(f"Failed to create lab: {e}")
            return False

    async def step2_run_with_callback(self):
        """Step 2: Run lab with callback to show real-time outputs"""
        self.print_header("STEP 2: RUN WITH CALLBACK")
        
        try:
            self.print_step("Starting lab execution with callback...")
            print("  📡 Real-time events:")
            
            # Run the lab with callback
            result = await self.lab.run(callback=self.callback_handler)
            
            self.print_success(f"Lab execution completed!")
            self.print_info(f"Total iterations: {result.get('iterations', 0)}")
            self.print_info(f"Final state: {result.get('state', 'unknown')}")
            
            return True
            
        except Exception as e:
            self.print_error(f"Failed to run lab: {e}")
            return False

    async def step3_show_outputs(self):
        """Step 3: Show outputs from the lab execution"""
        self.print_header("STEP 3: SHOW OUTPUTS")
        
        try:
            self.print_step("Retrieving lab outputs...")
            
            # Get the conversation history
            history = await self.lab.get_history()
            
            if not history:
                self.print_info("No conversation history found")
                return True
                
            self.print_success(f"Found {len(history)} messages in history")
            
            # Display the conversation
            print("\n  💬 Conversation:")
            print("  " + "-" * 50)
            
            for i, message in enumerate(history, 1):
                role = message.get("role", "unknown")
                content = message.get("content", "")
                
                # Truncate long messages for display
                if len(content) > 100:
                    content = content[:100] + "..."
                    
                print(f"  {i}. [{role.upper()}]: {content}")
                
            return True
            
        except Exception as e:
            self.print_error(f"Failed to show outputs: {e}")
            return False

    async def step4_resume_conversation(self):
        """Step 4: Resume the conversation with new topic"""
        self.print_header("STEP 4: RESUME CONVERSATION")
        
        try:
            self.print_step("Resuming lab with new topic...")
            
            # Update the objective for a new topic
            new_topic = "Now let's talk about your favorite type of music!"
            await self.lab.update_objective(new_topic)
            self.print_info(f"Updated topic: {new_topic}")
            
            # Run for a few more iterations
            print("  📡 Resuming with new events:")
            result = await self.lab.run(
                max_iterations=2,
                callback=self.callback_handler
            )
            
            self.print_success("Resume completed!")
            self.print_info(f"Additional iterations: {result.get('iterations', 0)}")
            
            return True
            
        except Exception as e:
            self.print_error(f"Failed to resume: {e}")
            return False

    async def step5_view_final_outputs(self):
        """Step 5: View final outputs after resume"""
        self.print_header("STEP 5: VIEW FINAL OUTPUTS")
        
        try:
            self.print_step("Retrieving final conversation...")
            
            # Get the complete conversation history
            history = await self.lab.get_history()
            
            if not history:
                self.print_info("No conversation history found")
                return True
                
            self.print_success(f"Total messages: {len(history)}")
            
            # Show the complete conversation
            print("\n  💬 Complete Conversation:")
            print("  " + "=" * 60)
            
            for i, message in enumerate(history, 1):
                role = message.get("role", "unknown")
                content = message.get("content", "")
                timestamp = message.get("timestamp", "unknown")
                
                print(f"\n  Message {i} [{role.upper()}] ({timestamp}):")
                print(f"  {content}")
                print("  " + "-" * 40)
                
            return True
            
        except Exception as e:
            self.print_error(f"Failed to view final outputs: {e}")
            return False

    async def step6_cleanup(self):
        """Step 6: Clean up thread and resources"""
        self.print_header("STEP 6: CLEANUP")
        
        try:
            self.print_step("Cleaning up thread...")
            
            # Get thread info before cleanup
            thread_info = await self.lab.get_thread_info()
            self.print_info(f"Thread ID: {thread_info.get('thread_id', 'unknown')}")
            self.print_info(f"Created: {thread_info.get('created_at', 'unknown')}")
            
            # Clean up the thread
            await self.lab.cleanup()
            self.print_success("Thread cleaned up successfully!")
            
            # Reset lab instance
            self.lab = None
            self.print_success("Lab instance reset")
            
            return True
            
        except Exception as e:
            self.print_error(f"Failed to cleanup: {e}")
            return False

    async def run_demo(self):
        """Run the complete demo"""
        self.print_header("AGENTRYLAB PYTHON API DEMO")
        self.print_info(f"Thread ID: {self.thread_id}")
        self.print_info(f"Preset: {self.preset_path}")
        
        steps = [
            ("Create Lab", self.step1_create_lab),
            ("Run with Callback", self.step2_run_with_callback),
            ("Show Outputs", self.step3_show_outputs),
            ("Resume Conversation", self.step4_resume_conversation),
            ("View Final Outputs", self.step5_view_final_outputs),
            ("Cleanup", self.step6_cleanup),
        ]
        
        for step_name, step_func in steps:
            try:
                success = await step_func()
                if not success:
                    self.print_error(f"Step '{step_name}' failed. Stopping demo.")
                    break
                    
                # Small delay between steps
                await asyncio.sleep(1)
                
            except Exception as e:
                self.print_error(f"Unexpected error in step '{step_name}': {e}")
                break
        
        self.print_header("DEMO COMPLETE")
        self.print_success("All steps completed successfully!")


async def main():
    """Main function to run the demo"""
    demo = AgentryLabDemo()
    await demo.run_demo()


if __name__ == "__main__":
    print("🚀 Starting AgentryLab Python API Demo...")
    print("📋 This demo will show you how to use the AgentryLab Python API")
    print("⏱️  Estimated time: 2-3 minutes")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
    
    print("\n👋 Demo finished!")
