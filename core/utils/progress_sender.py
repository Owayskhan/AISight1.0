import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class ProgressSender:
    """
    Sends real-time progress updates to Azure Web PubSub groups
    """
    
    def __init__(self, group_name: Optional[str] = None):
        """
        Initialize the progress sender with Azure Web PubSub credentials
        
        Args:
            group_name: The group name to send updates to
        """
        self.hub_name = os.getenv("AZURE_WEBPUBSUB_HUB_NAME")
        self.connection_string = os.getenv("AZURE_WEBPUBSUB_CONNECTION_STRING")
        self.group_name = group_name
        self.enabled = False
        
        if not self.hub_name or not self.connection_string:
            logger.warning("Azure Web PubSub credentials not found in environment variables. Real-time updates disabled.")
            return
            
        if not self.group_name:
            logger.info("No group name provided. Real-time updates disabled.")
            return
            
        try:
            self.client = WebPubSubServiceClient.from_connection_string(
                self.connection_string, 
                hub=self.hub_name
            )
            self.enabled = True
            logger.info(f"✅ Progress sender initialized for group: {self.group_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Web PubSub client: {str(e)}")
            self.enabled = False
    
    def _send_update(self, update_type: str, message: str, data: Dict[str, Any] = None, **kwargs) -> bool:
        """
        Send an update to the group with consistent structure
        
        Args:
            update_type: Type of update (e.g., 'status', 'progress', 'error', 'result')
            message: Human-readable message
            data: Additional structured data
            **kwargs: Additional fields to include
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Consistent message structure that clients can always expect
            structured_message = {
                "type": update_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {},
                **kwargs  # Allow additional fields when needed
            }
            
            self.client.send_to_group(
                group=self.group_name,
                message=json.dumps(structured_message),
                content_type="application/json"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send update: {str(e)}")
            return False
    
    def send_status(self, status: str, message: str, **kwargs):
        """
        Send a status update
        
        Args:
            status: Status code (e.g., 'starting', 'processing', 'completed', 'error')
            message: Human-readable status message
            **kwargs: Additional data to include
        """
        data = {
            "status": status,
            **kwargs
        }
        self._send_update("status", message, data)
    
    def send_progress(self, current: int, total: int, step: str, **kwargs):
        """
        Send a progress update
        
        Args:
            current: Current item being processed
            total: Total items to process
            step: Current processing step description
            **kwargs: Additional data to include
        """
        percentage = round((current / total * 100) if total > 0 else 0, 1)
        message = f"Progress: {current}/{total} ({percentage}%) - {step}"
        data = {
            "current": current,
            "total": total,
            "percentage": percentage,
            "step": step,
            **kwargs
        }
        self._send_update("progress", message, data)
    
    def send_step_completed(self, step_name: str, result_summary: Dict[str, Any] = None):
        """
        Send notification that a processing step has completed
        
        Args:
            step_name: Name of the completed step
            result_summary: Optional summary of the step results
        """
        message = f"Completed: {step_name}"
        data = {
            "step_name": step_name,
            "result_summary": result_summary or {}
        }
        self._send_update("step_completed", message, data)
    
    def send_query_result(self, query_index: int, query_text: str, visibility_percentage: float, **kwargs):
        """
        Send result for a single query
        
        Args:
            query_index: Index of the query
            query_text: The query text
            visibility_percentage: Visibility percentage for this query
            **kwargs: Additional data (e.g., llm_breakdown)
        """
        message = f"Query {query_index}: {visibility_percentage}% visibility"
        data = {
            "query_index": query_index,
            "query_text": query_text,
            "visibility_percentage": visibility_percentage,
            **kwargs
        }
        self._send_update("query_result", message, data)
    
    def send_final_results(self, overall_visibility: float, queries_analyzed: int, **kwargs):
        """
        Send final analysis results
        
        Args:
            overall_visibility: Overall brand visibility percentage
            queries_analyzed: Total number of queries analyzed
            **kwargs: Additional data (e.g., intent_distribution, llm_performance)
        """
        message = f"Analysis complete: {overall_visibility}% visibility across {queries_analyzed} queries"
        data = {
            "overall_visibility": overall_visibility,
            "queries_analyzed": queries_analyzed,
            **kwargs
        }
        self._send_update("final_results", message, data)
    
    def send_error(self, error_message: str, error_type: str = "general", **kwargs):
        """
        Send an error notification
        
        Args:
            error_message: The error message
            error_type: Type of error (e.g., 'general', 'api_error', 'validation_error')
            **kwargs: Additional error details
        """
        data = {
            "error_type": error_type,
            **kwargs
        }
        self._send_update("error", error_message, data)


# Singleton instance management
_progress_sender_instance: Optional[ProgressSender] = None


def get_progress_sender(group_name: Optional[str] = None) -> ProgressSender:
    """
    Get or create a progress sender instance
    
    Args:
        group_name: Group name for updates. If provided, creates a new instance.
                   If not provided, returns existing instance or creates disabled one.
    
    Returns:
        ProgressSender instance
    """
    global _progress_sender_instance
    
    if group_name:
        # Create new instance with the provided group name
        _progress_sender_instance = ProgressSender(group_name)
    elif _progress_sender_instance is None:
        # Create disabled instance if none exists
        _progress_sender_instance = ProgressSender()
    
    return _progress_sender_instance