#!/usr/bin/env python3
print("Hello from AgentryLab!")
print("Testing basic Python execution...")

import sys
import os
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")

# Test if we can import the telegram adapter
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from agentrylab.telegram.adapter import TelegramAdapter
    print("✅ Successfully imported TelegramAdapter")
except Exception as e:
    print(f"❌ Failed to import TelegramAdapter: {e}")

print("Test completed!")
