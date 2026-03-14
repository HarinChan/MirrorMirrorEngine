from ..config import Config
import time
import asyncio

from flask_sqlalchemy import SQLAlchemy # need to be fed in
from sqlalchemy import text
from .webex_service import WebexService # need to be fed in
from .azure_keyvault_service import AzureKeyVaultService # only static service
from .chromadb_service import ChromaDBService # need to be fed in

class HealthCheckService:

    health_check_list = [
        "engine_latency_health",
        "config_health",
        "chromadb_health",
        "azkv_health",
        "openvino_health",
        "webex_health",
        "db_health",
        "faster_whisper_health"
    ]

    default_required_checks = [
        "engine_latency_health",
        "config_health",
        "chromadb_health",
        "azkv_health",
        "webex_health",
        "db_health",
    ]

    def __init__(self):
        self.latency_threshold_ms = int(Config.get_variable("LATENCY_THRESHOLD_MS", "500")) # milliseconds
        self.latency_check_enabled = Config.get_variable("LATENCY_CHECK_ENABLED", "true").lower() == "true"
        self.latency_check_interval_seconds = int(Config.get_variable("LATENCY_CHECK_INTERVAL_SECONDS", "60")) # seconds
        self.latency_check_history_length = int(Config.get_variable("LATENCY_CHECK_HISTORY_LENGTH", "100")) # number of entries to keep in history
        self.required_checks = Config.get_variable("REQUIRED_HEALTH_CHECKS", ",".join(HealthCheckService.default_required_checks)).split(",") # which checks are required for overall healthy status

        self.latency_history = []  # Store latency history for monitoring

    
    def refresh_config(self):
        """
        Refresh the configuration settings from the Config class.
        This can be called periodically or triggered by an event to ensure the latest config is used.
        """
        self.latency_threshold_ms = int(Config.get_variable("LATENCY_THRESHOLD_MS", "500"))
        self.latency_check_enabled = Config.get_variable("LATENCY_CHECK_ENABLED", "true").lower() == "true"
        self.latency_check_interval_seconds = int(Config.get_variable("LATENCY_CHECK_INTERVAL_SECONDS", "60"))
        self.latency_check_history_length = int(Config.get_variable("LATENCY_CHECK_HISTORY_LENGTH", "100"))
        self.required_checks = Config.get_variable("REQUIRED_HEALTH_CHECKS", ",".join(HealthCheckService.default_required_checks)).split(",")
    
    async def log_latency(self, request_log: str, latency_ms: int):
        """
        Log latency and maintain history.
        
        Args:
            request_log: The log message for the request
            latency_ms: The latency in milliseconds to respond
        """
        async with asyncio.Lock():
            self.latency_history.append({
                "request_log": request_log,
                "timestamp": time.time(),
                "latency_ms": latency_ms
            })
            # Keep only the most recent entries up to the specified history length
            if len(self.latency_history) > self.latency_check_history_length:
                self.latency_history.pop(0)  
    def perform_latency_check(self) -> dict:
        """
            healthy: if every latency is below threshold
            unhealthy: if any latency is above threshold
            degraded: if average latency is above threshold
        """
        if not self.latency_check_enabled:
            return {
                "status": "disabled",
                "message": "Latency check is disabled in configuration."
            }
        if not self.latency_history:
            return {
                "status": "unknown",
                "message": "No latency data available yet."
            }

        total_latency = 0
        for entry in self.latency_history:
            if entry["latency_ms"] > self.latency_threshold_ms:
                print(f"Warning: High latency detected - {entry['request_log']} - Latency: {entry['latency_ms']}ms")
            total_latency += entry["latency_ms"]
    
        status = "healthy"
        if any(entry["latency_ms"] > self.latency_threshold_ms for entry in self.latency_history):
            status = "unhealthy"
        elif average_latency > self.latency_threshold_ms:
            status = "degraded"
        average_latency = total_latency / len(self.latency_history) if self.latency_history else 0
    
        return {
            "status": status,
            "average_latency_ms": average_latency
        }
    
    # service  / dbhealth check
    
    def perform_config_health_check(self) -> dict:
        """
        Perform a health check on the configuration service by attempting to retrieve safe variables.
        
        Returns:
            A dictionary with the health status and retrieved variables if successful, or an error message if not.
        """
        try:
            safe_variables = Config.get_all_safe_variables()
            return {
                "status": "healthy"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }   
    def perform_chromadb_health_check(self, chroma_service: ChromaDBService) -> dict:
        """
        Perform a health check on the ChromaDB service by attempting to retrieve collection information.
        
        Args:
            chroma_service: An instance of the ChromaDBService to check
            
        Returns:
            A dictionary with the health status and collection information if successful, or an error message if not.
        """
        try:
            collection_info = chroma_service.get_collection_info()
            if collection_info.get("status") == "success":
                return {
                    "status": "healthy",
                    "collection_info": collection_info
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Failed to retrieve collection info"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }  
    def perform_azure_keyvault_health_check(self) -> dict:
        """
        Perform a health check on the Azure Key Vault service by attempting to retrieve a test secret.
        Returns:
            A dictionary with the health status and secret value if successful, or an error message if not.
        """
        try:
            test_secret_name = "healthchecktestsecret"
            test_secret_value = "healthchecktestvalue"
            AzureKeyVaultService.update_secret(test_secret_name, test_secret_value)
            retrieved_value = AzureKeyVaultService.get_secret(test_secret_name)
            if retrieved_value == test_secret_value:
                return {
                    "status": "healthy"
                }
            else:
                return {
                    "status": "unhealthy"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }  
    def perform_openvino_health_check(self) -> dict:
        return {
            "status": "unhealthy",
            "message": "Faster Whisper is not used. No health check implemented."
        }
    def perform_webex_health_check(self, webex_service: WebexService) -> dict:
        """
        Perform a health check on the Webex service by attempting to auth url.
        """
        try:
            authurl = webex_service.get_auth_url()
            if authurl:
                return {
                    "status": "healthy",
                    "message": "auth URL retrieved successfully"
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Failed to retrieve auth URL"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }
    def perform_db_health_check(self, db: SQLAlchemy) -> dict:
        """
        Perform a health check on the database with latency timing.
        """
        start_time = time.perf_counter()
        try:
            # 1. Use text() for 2.0+ compatibility
            # 2. Use .scalar() as a cleaner way to get a single value
            result = db.session.execute(text("SELECT 1")).scalar()
            
            latency_ms = (time.perf_counter() - start_time) * 1000

            if result == 1:
                return {
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2)
                }
            
            return {
                "status": "unhealthy",
                "message": "Unexpected query result",
                "latency_ms": round(latency_ms, 2)
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection error: {str(e)}",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }
    def perform_faster_whisper_health_check(self) -> dict:
        return {
            "status": "unhealthy",
            "message": "Faster Whisper is not used. No health check implemented."
        }
    
    # health check probe that checks everything
    
    def perform_comprehensive_health_check(self, chroma_service: ChromaDBService, webex_service: WebexService, db: SQLAlchemy): # checks the health of EVERYTHING.
        """
        Perform a comprehensive health check on all services and return an overall status.
        args:
            chroma_service: An instance of the ChromaDBService to check
            webex_service: An instance of the WebexService to check
            db: An instance of the SQLAlchemy database to check
        """
        
        all_health = {
            "engine_latency_health": self.perform_latency_check(),
            "config_health": self.perform_config_health_check(),
            "chromadb_health": self.perform_chromadb_health_check(chroma_service),
            "azkv_health": self.perform_azure_keyvault_health_check(),
            "openvino_health": self.perform_openvino_health_check(),
            "webex_health": self.perform_webex_health_check(webex_service),
            "db_health": self.perform_db_health_check(db),
            "faster_whisper_health": self.perform_faster_whisper_health_check()
        }

        overall_status = "healthy"
        for check in self.required_checks:
            if all_health.get(check, {}).get("status") != "healthy":
                overall_status = "degraded" # should be unhealthy, but whatever
                break

        return {
            "status": overall_status,
            "required_checks": self.required_checks,
            "engine_latency_health": all_health["engine_latency_health"],
            "config_health": all_health["config_health"],
            "chromadb_health": all_health["chromadb_health"],
            "azure_keyvault_health": all_health["azkv_health"],
            "openvino_health": all_health["openvino_health"],
            "webex_health": all_health["webex_health"],
            "db_health": all_health["db_health"],
            "faster_whisper_health": all_health["faster_whisper_health"]
        }