# Detailed Plan: Schedulable AI Bot Tasks for AgentryLab

Based on my analysis of the agentrylab codebase, here's a comprehensive plan to implement schedulable AI bot tasks with the Facebook Marketplace deals finder example.

## 🏗️ Architecture Overview

The current agentrylab architecture is well-designed with:
- **Preset-based configuration** (YAML)
- **Pluggable schedulers** (RoundRobin, EveryN)
- **Tool system** (DuckDuckGo, Wolfram Alpha)
- **Agent nodes** (Agent, Moderator, Summarizer, Advisor)
- **Persistence layer** (SQLite checkpoints, JSONL transcripts)

## 📋 Implementation Plan

### Phase 1: Core Infrastructure Extensions

#### 1.1 Time-Based Scheduler Extension
**Current State**: Agentrylab has `RoundRobinScheduler` and `EveryNScheduler` that work on turn-based iterations.

**New Component**: `TimeBasedScheduler`
```python
# src/agentrylab/runtime/scheduler/time_based.py
class TimeBasedScheduler(Scheduler):
    """Scheduler that executes agents based on time intervals (cron-like)"""
    
    def __init__(self, schedule_config: Dict[str, Any]):
        # Support cron expressions, intervals, and specific times
        # schedule_config: {"task_id": {"cron": "0 * * * *", "agents": ["deals_finder"]}}
```

**Key Features**:
- Support cron expressions (`0 * * * *` for hourly)
- Support interval-based scheduling (`every: 3600` seconds)
- Support duration limits (`end_date: "2024-01-15"`)
- Integration with existing agent system

#### 1.2 Task Management System (ENHANCED)
**New Component**: `TaskManager`
```python
# src/agentrylab/runtime/tasks/manager.py
from datetime import datetime
from typing import Dict, List, Optional
import threading
import asyncio
from dataclasses import dataclass

@dataclass
class Listing:
    """Standardized listing format"""
    id: str
    title: str
    price: float
    currency: str
    url: str
    images: List[str] = field(default_factory=list)
    posted_at: Optional[datetime] = None
    location: Optional[Dict[str, Any]] = None  # {city, lat, lon, distance_km}
    seller: Optional[Dict[str, Any]] = None

class TaskManager:
    """Manages lifecycle of scheduled tasks with background execution"""
    
    def __init__(self, store: Store, max_concurrent: int = 10):
        self.store = store
        self.active_tasks: Dict[str, ScheduledTask] = {}
        self.max_concurrent = max_concurrent
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        
    def create_task(self, preset_path: str, overrides: Dict[str, Any] = None) -> str:
        """Create a new scheduled task from preset"""
        
    def enable_task(self, task_id: str) -> None:
        """Enable/start a scheduled task"""
        
    def disable_task(self, task_id: str) -> None:
        """Disable/stop a scheduled task"""
        
    def update_schedule(self, task_id: str, schedule: Dict[str, Any]) -> None:
        """Update task schedule without recreating"""
        
    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks with their status and next_due_at"""
        
    def get_task_logs(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for a task"""
        
    def _run_task_background(self, task: ScheduledTask) -> None:
        """Background runner for scheduled tasks"""
        # Creates isolated Lab instance per task
        # Runs with streaming to capture results
        # Handles persistence and error recovery
```

#### 1.3 Enhanced Configuration Schema
**Extensions to existing config**:
```yaml
# New sections in preset YAML
tasks:
  - id: marketplace_deals
    name: "Facebook Marketplace Deals Finder"
    description: "Monitors Facebook Marketplace for specific deals"
    schedule:
      type: "interval"  # or "cron"
      value: "3600"     # seconds for interval, cron expression for cron
      duration: "3d"    # optional: how long to run
    agents: ["deals_finder"]
    tools: ["apify_marketplace"]
    max_deals: 5
    search_query: "Bambulab x1 carbon best value deals"

runtime:
  task_manager:
    enabled: true
    persistence: true
```

### Phase 2: Tool Integration

#### 2.1 Apify Facebook Marketplace Tool
**New Tool**: `ApifyMarketplaceTool`
```python
# src/agentrylab/runtime/tools/apify_marketplace.py
class ApifyMarketplaceTool(Tool):
    """Tool for searching Facebook Marketplace via Apify actor"""
    
    def run(self, search_query: str, location: str = None, 
            max_results: int = 10, **kwargs) -> ToolResult:
        """
        Search Facebook Marketplace for deals
        
        Returns:
            ToolResult with:
            - data: List of deals with title, price, location, url
            - meta: citations (marketplace URLs)
        """
```

**Features**:
- Integration with Apify's Facebook Marketplace actor
- Configurable search parameters (location, price range, keywords)
- Result filtering and ranking
- Error handling and retries

#### 2.2 Deal Analysis Agent
**New Agent Type**: `DealsFinderAgent`
```python
# Custom agent specifically for deal finding
# Uses the Apify tool to search and analyze deals
# Filters results based on user criteria
# Ranks deals by value/price ratio
```

### Phase 3: Preset Configuration

#### 3.1 Marketplace Deals Preset (REVISED)
```yaml
# src/agentrylab/presets/marketplace_deals.yaml
version: "1.0.0"
id: marketplace_deals
name: "Facebook Marketplace Deals Finder"
description: "Scheduled monitoring of Facebook Marketplace for specific deals"

# Task configuration - SINGLE SOURCE OF TRUTH
tasks:
  - id: deals_monitor
    name: "Deals Monitor"
    description: "Monitors Facebook Marketplace for deals"
    schedule:
      type: "cron"              # or "interval"
      value: "0 9 * * *"        # daily at 09:00 (local timezone)
      timezone: "Asia/Jerusalem"
      duration: "3d"            # run for 3 days
    params:
      region: "Ra'anana, Israel"
      radius_km: 40
      query: ${SEARCH_QUERY:"Bambulab x1 carbon best value deals"}
      top_n: 3
      max_price_ils: 15000      # price filter
    agents: ["deals_finder"]
    sources: ["fb_marketplace"]
    sinks: ["telegram_notifier"]

# Data Pipeline Configuration
sources:
  - id: fb_marketplace
    type: apify_actor
    params:
      actor_id: "apify/facebook-marketplace-scraper"
      apify_token: ${APIFY_API_TOKEN}
      timeout_s: 300

pipeline:
  - id: normalize
    type: listing_normalizer
  - id: dedupe
    type: deal_tracker
    params:
      cache_backend: "redis"  # or "sqlite"
      ttl_hours: 168  # 7 days
  - id: currency_normalize
    type: fx_converter
    params:
      target_currency: "ILS"
      fx_provider: "exchangerate-api"
  - id: rank_rules
    type: rule_based_ranker
  - id: llm_rerank
    type: ai_ranker
    params:
      enabled: true
      fallback_to_rules: true

sinks:
  - id: telegram_notifier
    type: telegram_bot
    params:
      bot_token: ${TG_BOT_TOKEN}
      chat_id: ${TG_CHAT_ID}

runtime:
  task_manager:
    enabled: true
    persistence: true
    max_concurrent_tasks: 10
    background_runner: "threading"  # or "asyncio"

providers:
  - id: openai_gpt4o_mini
    impl: agentrylab.runtime.providers.openai.OpenAIProvider
    model: "gpt-4o-mini"
    api_key: ${OPENAI_API_KEY}

tools:
  - id: apify_marketplace
    impl: agentrylab.runtime.tools.apify_marketplace.ApifyMarketplaceTool
    params:
      apify_token: ${APIFY_API_TOKEN}
      actor_id: "apify/facebook-marketplace-scraper"
      max_results: 20
      location: ${LOCATION:"New York, NY"}
    budget:
      per_run_max: 10
      per_iteration_max: 1

agents:
  - id: deals_finder
    role: agent
    display_name: "Deals Finder"
    description: "Finds and analyzes Facebook Marketplace deals"
    provider: openai_gpt4o_mini
    tools: [apify_marketplace]
    context:
      max_messages: 3
      pin_objective: true
    system_prompt: |
      You are a deals finder for Facebook Marketplace. Your job is to:
      1. Search for deals using the apify_marketplace tool
      2. Analyze each deal for value and quality
      3. Rank deals by best value (price vs quality)
      4. Return the top deals with explanations
      
      Focus on:
      - Price competitiveness
      - Item condition
      - Location convenience
      - Seller reputation indicators
      
      Always provide reasoning for your rankings.
```

### Phase 4: CLI Extensions

#### 4.1 New CLI Commands (ENHANCED)
```bash
# New commands to add to agentrylab CLI
agentrylab task create --preset marketplace_deals.yaml --query "Bambulab x1 carbon"
agentrylab task enable <task_id>
agentrylab task disable <task_id>
agentrylab task update <task_id> --every 1d --top 3 --query "..."
agentrylab task list
agentrylab task status <task_id>
agentrylab task logs <task_id> --limit 50
agentrylab task results <task_id> --latest
```

#### 4.2 CLI Implementation
```python
# src/agentrylab/cli/commands/tasks.py
class TaskCommands:
    """CLI commands for task management"""
    
    def create_task(self, preset_path: str, **kwargs):
        """Create a new scheduled task from preset"""
        
    def start_task(self, task_id: str):
        """Start a scheduled task"""
        
    def list_tasks(self):
        """List all tasks with status"""
```

### Phase 5: Persistence and State Management

#### 5.1 Task Persistence
**Extensions to existing Store**:
```python
# Enhanced persistence for tasks
class TaskStore:
    """Handles persistence of scheduled tasks"""
    
    def save_task(self, task_id: str, task_config: Dict[str, Any]):
        """Save task configuration"""
        
    def load_task(self, task_id: str) -> Dict[str, Any]:
        """Load task configuration"""
        
    def save_task_results(self, task_id: str, results: List[Dict[str, Any]]):
        """Save task execution results"""
```

#### 5.2 Task State Management
```python
# src/agentrylab/runtime/state.py extensions
class TaskState:
    """State management for scheduled tasks"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = "created"  # created, running, stopped, completed
        self.last_run = None
        self.results = []
        self.error_count = 0
```

### Phase 6: Advanced Features

#### 6.1 Notifications and Alerts
```python
# src/agentrylab/runtime/notifications/
class NotificationManager:
    """Handles task notifications"""
    
    def send_deal_alert(self, deals: List[Dict[str, Any]]):
        """Send notification when good deals are found"""
        
    def send_task_status(self, task_id: str, status: str):
        """Send task status updates"""
```

#### 6.2 Deal Tracking and History
```python
# Track deal history to avoid duplicates
class DealTracker:
    """Tracks previously found deals"""
    
    def is_new_deal(self, deal: Dict[str, Any]) -> bool:
        """Check if deal is new"""
        
    def track_deal(self, deal: Dict[str, Any]):
        """Add deal to tracking"""
```

### Phase 7: Testing and Documentation

#### 7.1 Test Coverage
- Unit tests for all new components
- Integration tests for task scheduling
- End-to-end tests with mock Apify responses
- Performance tests for long-running tasks

#### 7.2 Documentation
- Updated architecture documentation
- User guide for creating scheduled tasks
- API documentation for new components
- Example presets and configurations

## 🗓️ Implementation Steps

### Step 1: Core Scheduler Extension (Week 1)
1. Implement `TimeBasedScheduler` class
2. Extend configuration schema for time-based scheduling
3. Update `Engine` to support time-based execution
4. Basic tests for scheduler functionality

### Step 2: Task Management System (Week 2)
1. Implement `TaskManager` class
2. Create task persistence layer
3. Add task state management
4. Implement basic CLI commands

### Step 3: Apify Integration (Week 3)
1. Implement `ApifyMarketplaceTool`
2. Create marketplace deals agent
3. Test tool integration with mock data
4. Handle authentication and error cases

### Step 4: Preset and Configuration (Week 4)
1. Create marketplace deals preset
2. Extend configuration validation
3. Add environment variable support
4. Create example configurations

### Step 5: CLI and User Experience (Week 5)
1. Implement CLI commands
2. Add task monitoring and logging
3. Create user-friendly error messages
4. Add help documentation

### Step 6: Advanced Features (Week 6)
1. Implement notifications
2. Add deal tracking
3. Create result formatting
4. Add task analytics

### Step 7: Testing and Polish (Week 7)
1. Comprehensive testing
2. Performance optimization
3. Documentation updates
4. Example scenarios

## 🎯 Success Criteria

1. **Functional**: Users can create scheduled tasks via YAML configuration
2. **Reliable**: Tasks execute on schedule with proper error handling
3. **Extensible**: Easy to add new tools and agents for different use cases
4. **User-Friendly**: Clear CLI commands and helpful error messages
5. **Maintainable**: Well-documented code following agentrylab patterns

## 🚀 Future Extensions

1. **Multiple Platforms**: Extend to eBay, Craigslist, other marketplaces
2. **Smart Filtering**: ML-based deal quality assessment
3. **Price Tracking**: Historical price analysis and trends
4. **Multi-User**: Support for multiple users with different preferences
5. **Web Interface**: Browser-based task management
6. **Mobile Notifications**: Push notifications for great deals

## 📁 File Structure

The implementation will add these new files to the agentrylab codebase:

```
src/agentrylab/
├── runtime/
│   ├── scheduler/
│   │   └── time_based.py          # TimeBasedScheduler
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── manager.py             # TaskManager
│   │   ├── state.py               # TaskState
│   │   └── store.py               # TaskStore
│   ├── tools/
│   │   └── apify_marketplace.py   # ApifyMarketplaceTool
│   └── notifications/
│       ├── __init__.py
│       └── manager.py             # NotificationManager
├── cli/
│   └── commands/
│       └── tasks.py               # Task CLI commands
└── presets/
    └── marketplace_deals.yaml     # Marketplace deals preset
```

## 🔧 Dependencies

New dependencies to add to `pyproject.toml`:

```toml
# Additional dependencies for schedulable tasks
dependencies = [
    # ... existing dependencies ...
    "apscheduler>=3.10.0",      # Advanced Python Scheduler
    "apify-client>=1.7.0",      # Apify API client
    "croniter>=1.4.0",          # Cron expression parsing
    "redis>=5.0.0",             # For deal deduplication cache
    "requests>=2.31.0",         # For FX rate API calls
    "pytz>=2023.3",             # Timezone handling
]
```

## 🔄 **UPDATED: Incorporating Grok4 & GPT5 Feedback**

### **Critical Changes Made:**

#### 1. **Single Source of Truth for Scheduling**
- ✅ **Fixed**: Removed dual schedule configuration
- ✅ **Result**: Schedule defined only in `tasks[].schedule` 
- ✅ **Benefit**: No configuration drift, clearer user experience

#### 2. **Enhanced Background Execution Model**
- ✅ **Added**: ThreadPoolExecutor in TaskManager for concurrency
- ✅ **Added**: Explicit background runner configuration
- ✅ **Added**: Task isolation via separate Lab instances per task

#### 3. **Data Pipeline Architecture (GPT5's Suggestion)**
- ✅ **Added**: `sources`, `pipeline`, `sinks` configuration sections
- ✅ **Added**: Standardized `Listing` dataclass for type safety
- ✅ **Benefit**: Easy extension to eBay, Craigslist, other platforms

#### 4. **Deal Deduplication System**
- ✅ **Added**: DealTracker component in pipeline
- ✅ **Added**: Redis/SQLite backend options for seen listings
- ✅ **Added**: TTL-based cache management (7 days default)

#### 5. **Currency & Price Normalization**
- ✅ **Added**: FX converter pipeline component
- ✅ **Added**: Target currency configuration (ILS for Israel)
- ✅ **Added**: Daily FX rate caching

#### 6. **Robust Ranking System**
- ✅ **Added**: Rule-based ranker as primary system
- ✅ **Added**: LLM re-ranker as optional enhancement with fallback
- ✅ **Benefit**: Works even when LLM is down or over budget

#### 7. **Enhanced CLI Ergonomics**
- ✅ **Added**: `task update` command for in-place edits
- ✅ **Added**: `task results --latest` for quick access to findings
- ✅ **Added**: Better parameter control (--every, --top, --query)

### **MVP Roadmap (Based on GPT5 Recommendation)**

**Phase 1: Core Pipeline (Week 1-2)**
```
Source → Normalize → Dedupe → Rank → Notify
```

**Components to build first:**
1. ✅ **ApifyActorSource**: Calls Apify actor + fetches dataset
2. ✅ **ListingNormalizer**: Maps raw data to `Listing` dataclass
3. ✅ **DealTracker**: Redis/SQLite deduplication on `listing.id`
4. ✅ **RuleBasedRanker**: Z-score pricing, recency, distance scoring
5. ✅ **TelegramSink**: Posts top 3 picks with rationale
6. ✅ **CronScheduler**: Single daily run at 09:00 Asia/Jerusalem
7. ✅ **TaskObservability**: JSON logging for counts/errors/chosen IDs

**MVP Success Criteria:**
- [ ] Task runs daily at scheduled time
- [ ] Finds Bambu Lab deals in Ra'anana area
- [ ] Eliminates duplicate listings across runs
- [ ] Ranks by price competitiveness + distance
- [ ] Sends top 3 to Telegram with reasoning
- [ ] Survives Apify API failures gracefully
- [ ] Logs structured data for debugging

**Deferred to Phase 2:**
- LLM re-ranking (rule-based sufficient for MVP)
- Multi-platform sources (eBay, Craigslist)
- Price baselines (static comparison for MVP)
- Multi-user support
- Web interface

### **Open Questions (To Resolve Before Coding):**

1. **Multi-User Support**: Single operator or per-Telegram-chat tasks?
   - **Recommendation**: Single operator for MVP, multi-user in Phase 2

2. **FX Rates Storage**: Where to cache daily exchange rates?
   - **Recommendation**: Simple Redis cache with daily refresh

3. **Apify Actor Fields**: What fields are guaranteed from the actor?
   - **Action Required**: Test Apify actor to determine reliable fields

4. **Fallback Strategy**: What happens when Apify is down?
   - **Recommendation**: Log error, skip run, retry next scheduled time

5. **Location Matching**: How to handle "Ra'anana" vs "רעננה" in Hebrew?
   - **Recommendation**: Normalize to English + distance calculation

### **Risk Mitigation (Addressing Grok4's Concerns)**

#### **Scalability Risks:**
- ✅ **Solution**: ThreadPoolExecutor with configurable `max_concurrent_tasks`
- ✅ **Solution**: Task isolation prevents resource contention
- ✅ **Solution**: Optional async mode for high-scale deployments

#### **Apify Dependency Risks:**
- ✅ **Solution**: Timeout + retry logic in ApifyActorSource
- ✅ **Solution**: Graceful degradation when actor fails
- ✅ **Solution**: Mock data support for testing

#### **Notification Flexibility:**
- ✅ **Solution**: Pluggable sink architecture (Telegram, Email, SMS)
- ✅ **Solution**: Abstract NotificationSink base class

#### **Testing Coverage:**
- ✅ **Solution**: Edge case tests (no deals, API limits, network failures)
- ✅ **Solution**: Integration tests with mock Apify responses
- ✅ **Solution**: Load testing for concurrent task execution

This plan leverages agentrylab's existing architecture while adding powerful scheduling capabilities. The modular design allows for easy extension to other use cases beyond marketplace monitoring.

---

*Created: December 2024*
*Updated: December 2024 (Grok4 & GPT5 feedback integrated)*
*Status: Ready for MVP Implementation*
*Next Steps: Start with ApifyActorSource + ListingNormalizer*
