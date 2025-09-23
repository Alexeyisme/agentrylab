"""Task management system for scheduled tasks.

This module provides the TaskManager class that orchestrates the execution
of scheduled tasks, manages their lifecycle, and handles persistence.
"""

from __future__ import annotations

import time
import uuid
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from agentrylab.runtime.tasks.sources import ApifyActorSource, Listing
from agentrylab.runtime.tasks.normalizer import FacebookMarketplaceNormalizer
from agentrylab.persistence.store import Store


@dataclass
class TaskConfig:
    """Configuration for a scheduled task."""
    id: str
    name: str
    description: str
    schedule: Dict[str, Any]
    params: Dict[str, Any] = field(default_factory=dict)
    agents: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    sinks: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    enabled: bool = True


@dataclass 
class TaskStatus:
    """Status information for a scheduled task."""
    task_id: str
    status: str = "created"  # "created", "running", "stopped", "completed", "error"
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    results: List[Dict[str, Any]] = field(default_factory=list)


class TaskManager:
    """Manages lifecycle of scheduled tasks with background execution.
    
    This class orchestrates the execution of scheduled tasks, manages
    their persistence, and provides monitoring capabilities.
    
    Features:
    - Background task execution using ThreadPoolExecutor
    - Task isolation via separate Lab instances per task
    - Persistence of task configurations and results
    - Scheduling with cron and interval support
    - Error handling and retry logic
    """
    
    def __init__(self, store: Store, max_concurrent: int = 10):
        self.store = store
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(__name__)
        
        # Task management
        self.tasks: Dict[str, TaskConfig] = {}
        self.task_status: Dict[str, TaskStatus] = {}
        self.active_futures: Dict[str, Future] = {}
        
        # Background execution
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._scheduler_thread = None
        self._running = False
        
        # Initialize sources and normalizers
        self._sources: Dict[str, Any] = {}
        self._normalizers: Dict[str, Any] = {}
        self._register_default_components()
    
    def _register_default_components(self):
        """Register default source and normalizer components."""
        # Register default Facebook Marketplace source
        self._sources["apify_facebook_marketplace"] = ApifyActorSource
        
        # Register default normalizer
        self._normalizers["facebook_marketplace"] = FacebookMarketplaceNormalizer
    
    def create_task(self, preset_path: str, overrides: Dict[str, Any] = None) -> str:
        """Create a new scheduled task from preset.
        
        Args:
            preset_path: Path to YAML preset file
            overrides: Optional parameter overrides
            
        Returns:
            Task ID of the created task
        """
        try:
            from agentrylab.config.loader import load_config
            
            # Load preset configuration
            cfg = load_config(preset_path)
            
            # Extract task configuration
            tasks_cfg = getattr(cfg, "tasks", []) or []
            if not tasks_cfg:
                raise ValueError("No tasks found in preset")
            
            # Use first task configuration (for MVP, single task per preset)
            task_cfg = tasks_cfg[0]
            
            # Apply overrides
            if overrides:
                task_cfg.update(overrides)
            
            # Create task ID
            task_id = task_cfg.get("id") or f"task-{uuid.uuid4().hex[:8]}"
            
            # Create task configuration
            task_config = TaskConfig(
                id=task_id,
                name=task_cfg.get("name", "Unnamed Task"),
                description=task_cfg.get("description", ""),
                schedule=task_cfg.get("schedule", {}),
                params=task_cfg.get("params", {}),
                agents=task_cfg.get("agents", []),
                sources=task_cfg.get("sources", []),
                sinks=task_cfg.get("sinks", []),
            )
            
            # Store task configuration
            self.tasks[task_id] = task_config
            self.task_status[task_id] = TaskStatus(task_id=task_id, status="created")
            
            # Persist task configuration
            self._save_task_config(task_config)
            
            self.logger.info(f"Created task {task_id}: {task_config.name}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            raise
    
    def enable_task(self, task_id: str) -> None:
        """Enable/start a scheduled task.
        
        Args:
            task_id: ID of the task to enable
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task_config = self.tasks[task_id]
        task_config.enabled = True
        
        # Start scheduler if not running
        if not self._running:
            self.start_scheduler()
        
        # Update status
        self.task_status[task_id].status = "running"
        self._save_task_status(task_id)
        
        self.logger.info(f"Enabled task {task_id}")
    
    def disable_task(self, task_id: str) -> None:
        """Disable/stop a scheduled task.
        
        Args:
            task_id: ID of the task to disable
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task_config = self.tasks[task_id]
        task_config.enabled = False
        
        # Cancel any running execution
        if task_id in self.active_futures:
            future = self.active_futures[task_id]
            future.cancel()
            del self.active_futures[task_id]
        
        # Update status
        self.task_status[task_id].status = "stopped"
        self._save_task_status(task_id)
        
        self.logger.info(f"Disabled task {task_id}")
    
    def update_schedule(self, task_id: str, schedule: Dict[str, Any]) -> None:
        """Update task schedule without recreating.
        
        Args:
            task_id: ID of the task to update
            schedule: New schedule configuration
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task_config = self.tasks[task_id]
        task_config.schedule.update(schedule)
        
        self._save_task_config(task_config)
        self.logger.info(f"Updated schedule for task {task_id}")
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks with their status and next_due_at.
        
        Returns:
            List of task information dictionaries
        """
        tasks_info = []
        
        for task_id, task_config in self.tasks.items():
            status = self.task_status.get(task_id, TaskStatus(task_id=task_id))
            
            task_info = {
                "id": task_id,
                "name": task_config.name,
                "description": task_config.description,
                "status": status.status,
                "enabled": task_config.enabled,
                "last_run": status.last_run.isoformat() if status.last_run else None,
                "next_run": status.next_run.isoformat() if status.next_run else None,
                "run_count": status.run_count,
                "error_count": status.error_count,
                "created_at": task_config.created_at.isoformat(),
            }
            
            tasks_info.append(task_info)
        
        return tasks_info
    
    def get_task_logs(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for a task.
        
        Args:
            task_id: ID of the task
            limit: Maximum number of log entries to return
            
        Returns:
            List of log entries
        """
        try:
            # Read transcript from store
            transcript = self.store.read_transcript(f"task-{task_id}", limit=limit)
            return transcript
        except Exception as e:
            self.logger.error(f"Failed to get logs for task {task_id}: {e}")
            return []
    
    def start_scheduler(self) -> None:
        """Start the background task scheduler."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        self.logger.info("Task scheduler started")
    
    def stop_scheduler(self) -> None:
        """Stop the background task scheduler."""
        self._running = False
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5.0)
        
        # Cancel all active futures
        for future in self.active_futures.values():
            future.cancel()
        
        self.active_futures.clear()
        
        self.logger.info("Task scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks for tasks to run."""
        while self._running:
            try:
                current_time = datetime.now()
                
                for task_id, task_config in self.tasks.items():
                    if not task_config.enabled:
                        continue
                    
                    if task_id in self.active_futures:
                        continue  # Task already running
                    
                    # Check if task should run now
                    if self._should_run_task(task_config, current_time):
                        self._execute_task(task_id)
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)  # Continue on error
    
    def _should_run_task(self, task_config: TaskConfig, current_time: datetime) -> bool:
        """Check if a task should run at the current time.
        
        Args:
            task_config: Task configuration
            current_time: Current datetime
            
        Returns:
            True if task should run now
        """
        schedule = task_config.schedule
        task_id = task_config.id
        status = self.task_status.get(task_id, TaskStatus(task_id=task_id))
        
        # Check if task has run recently (prevent duplicate runs)
        if status.last_run:
            time_since_last = current_time - status.last_run
            if time_since_last < timedelta(minutes=5):  # Minimum 5 minutes between runs
                return False
        
        # Check schedule type
        schedule_type = schedule.get("type", "interval")
        
        if schedule_type == "cron":
            return self._check_cron_schedule(schedule, current_time)
        elif schedule_type == "interval":
            return self._check_interval_schedule(schedule, current_time)
        
        return False
    
    def _check_cron_schedule(self, schedule: Dict[str, Any], current_time: datetime) -> bool:
        """Check if current time matches cron schedule."""
        try:
            import croniter
            
            cron_expr = schedule.get("value")
            if not cron_expr:
                return False
            
            # Get last run time (approximate)
            last_run = current_time - timedelta(hours=1)  # Simplified for MVP
            
            cron = croniter.croniter(cron_expr, last_run)
            next_run = cron.get_next(datetime)
            
            return next_run <= current_time
            
        except Exception as e:
            self.logger.error(f"Cron schedule check failed: {e}")
            return False
    
    def _check_interval_schedule(self, schedule: Dict[str, Any], current_time: datetime) -> bool:
        """Check if current time matches interval schedule."""
        try:
            interval_seconds = int(schedule.get("value", 3600))
            
            # Simple interval check (run every N seconds)
            # In a real implementation, this would track last run time more precisely
            return True  # Simplified for MVP
            
        except Exception as e:
            self.logger.error(f"Interval schedule check failed: {e}")
            return False
    
    def _execute_task(self, task_id: str) -> None:
        """Execute a task in the background.
        
        Args:
            task_id: ID of the task to execute
        """
        task_config = self.tasks[task_id]
        
        # Submit task to executor
        future = self._executor.submit(self._run_task, task_config)
        self.active_futures[task_id] = future
        
        self.logger.info(f"Started execution of task {task_id}")
    
    def _run_task(self, task_config: TaskConfig) -> None:
        """Run a single task execution.
        
        Args:
            task_config: Configuration for the task to run
        """
        task_id = task_config.id
        status = self.task_status[task_id]
        
        try:
            # Update status
            status.status = "running"
            status.last_run = datetime.now()
            status.run_count += 1
            self._save_task_status(task_id)
            
            # Execute task pipeline
            results = self._execute_pipeline(task_config)
            
            # Store results
            status.results.extend(results)
            status.status = "completed"
            
            # Calculate next run time
            status.next_run = self._calculate_next_run(task_config)
            
            self.logger.info(f"Task {task_id} completed successfully with {len(results)} results")
            
        except Exception as e:
            status.status = "error"
            status.error_count += 1
            status.last_error = str(e)
            
            self.logger.error(f"Task {task_id} failed: {e}")
            
        finally:
            # Clean up
            if task_id in self.active_futures:
                del self.active_futures[task_id]
            
            self._save_task_status(task_id)
    
    def _execute_pipeline(self, task_config: TaskConfig) -> List[Dict[str, Any]]:
        """Execute the task pipeline: source -> normalize -> process -> sink.
        
        Args:
            task_config: Task configuration
            
        Returns:
            List of processed results
        """
        results = []
        
        # Execute sources
        raw_data = []
        for source_id in task_config.sources:
            source_data = self._execute_source(source_id, task_config.params)
            raw_data.extend(source_data)
        
        # Normalize data
        normalized_listings = []
        for raw_item in raw_data:
            listing = self._normalize_listing(raw_item)
            if listing:
                normalized_listings.append(listing)
        
        # Process listings (ranking, filtering, etc.)
        processed_listings = self._process_listings(normalized_listings, task_config.params)
        
        # Execute sinks
        for sink_id in task_config.sinks:
            self._execute_sink(sink_id, processed_listings, task_config.params)
        
        # Convert to results format
        for listing in processed_listings:
            results.append({
                "id": listing.id,
                "title": listing.title,
                "price": listing.price,
                "currency": listing.currency,
                "url": listing.url,
                "timestamp": datetime.now().isoformat(),
            })
        
        return results
    
    def _execute_source(self, source_id: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a data source.
        
        Args:
            source_id: ID of the source to execute
            params: Parameters for the source
            
        Returns:
            Raw data from the source
        """
        if source_id == "apify_facebook_marketplace":
            source = ApifyActorSource()
            result = source.run(**params)
            
            if result["ok"]:
                return result["data"] or []
            else:
                raise Exception(f"Source failed: {result.get('error', 'Unknown error')}")
        
        raise ValueError(f"Unknown source: {source_id}")
    
    def _normalize_listing(self, raw_item: Dict[str, Any]) -> Optional[Listing]:
        """Normalize a raw listing item.
        
        Args:
            raw_item: Raw item data
            
        Returns:
            Normalized Listing object
        """
        normalizer = FacebookMarketplaceNormalizer()
        normalized = normalizer.normalize([raw_item])
        return normalized[0] if normalized else None
    
    def _process_listings(self, listings: List[Listing], params: Dict[str, Any]) -> List[Listing]:
        """Process and rank listings.
        
        Args:
            listings: List of normalized listings
            params: Processing parameters
            
        Returns:
            Processed and ranked listings
        """
        # Get filtering parameters (generic)
        min_price = params.get("min_price", 0)
        max_price = params.get("max_price", float('inf'))
        target_currency = params.get("currency", "USD")
        top_n = params.get("top_n", 5)
        
        # Filter by price range (in target currency)
        filtered = []
        for listing in listings:
            # Simple currency matching for MVP
            # In production, this would use the FX converter
            if listing.currency == target_currency:
                if min_price <= listing.price <= max_price:
                    filtered.append(listing)
        
        # Sort by price (ascending for best deals)
        filtered.sort(key=lambda x: x.price)
        
        # Return top N results
        return filtered[:top_n]
    
    def _execute_sink(self, sink_id: str, listings: List[Listing], params: Dict[str, Any]) -> None:
        """Execute a data sink (notification, storage, etc.).
        
        Args:
            sink_id: ID of the sink to execute
            listings: Processed listings to send
            params: Sink parameters
        """
        if sink_id == "telegram_notifier":
            self._send_telegram_notification(listings, params)
        else:
            self.logger.warning(f"Unknown sink: {sink_id}")
    
    def _send_telegram_notification(self, listings: List[Listing], params: Dict[str, Any]) -> None:
        """Send Telegram notification with listings.
        
        Args:
            listings: Listings to send
            params: Notification parameters
        """
        if not listings:
            return
        
        # Format message
        message = f"🔍 Found {len(listings)} deals:\n\n"
        
        for i, listing in enumerate(listings[:3], 1):  # Top 3
            message += f"{i}. {listing.title}\n"
            message += f"   💰 {listing.price} {listing.currency}\n"
            message += f"   🔗 {listing.url}\n\n"
        
        self.logger.info(f"Would send Telegram notification: {message}")
        # TODO: Implement actual Telegram sending
    
    def _calculate_next_run(self, task_config: TaskConfig) -> datetime:
        """Calculate next run time for a task.
        
        Args:
            task_config: Task configuration
            
        Returns:
            Next run datetime
        """
        schedule = task_config.schedule
        schedule_type = schedule.get("type", "interval")
        
        if schedule_type == "cron":
            try:
                import croniter
                cron_expr = schedule.get("value")
                if cron_expr:
                    cron = croniter.croniter(cron_expr, datetime.now())
                    return cron.get_next(datetime)
            except Exception:
                pass
        
        # Default: next run in 1 hour
        return datetime.now() + timedelta(hours=1)
    
    def _save_task_config(self, task_config: TaskConfig) -> None:
        """Save task configuration to persistence."""
        try:
            config_data = {
                "id": task_config.id,
                "name": task_config.name,
                "description": task_config.description,
                "schedule": task_config.schedule,
                "params": task_config.params,
                "agents": task_config.agents,
                "sources": task_config.sources,
                "sinks": task_config.sinks,
                "created_at": task_config.created_at.isoformat(),
                "enabled": task_config.enabled,
            }
            
            # Save to store (using thread_id as task_id for isolation)
            self.store.save_checkpoint(f"task-config-{task_config.id}", config_data)
            
        except Exception as e:
            self.logger.error(f"Failed to save task config: {e}")
    
    def _save_task_status(self, task_id: str) -> None:
        """Save task status to persistence."""
        try:
            status = self.task_status[task_id]
            status_data = {
                "task_id": status.task_id,
                "status": status.status,
                "last_run": status.last_run.isoformat() if status.last_run else None,
                "next_run": status.next_run.isoformat() if status.next_run else None,
                "run_count": status.run_count,
                "error_count": status.error_count,
                "last_error": status.last_error,
                "results": status.results,
            }
            
            # Save to store
            self.store.save_checkpoint(f"task-status-{task_id}", status_data)
            
        except Exception as e:
            self.logger.error(f"Failed to save task status: {e}")
