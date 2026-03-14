from ..config import Config
import time
import asyncio
class HealthCheckService:

    def __init__(self):
        self.latency_threshold_ms = int(Config.get_variable("LATENCY_THRESHOLD_MS", "500")) # milliseconds
        self.latency_check_enabled = Config.get_variable("LATENCY_CHECK_ENABLED", "true").lower() == "true"
        self.latency_check_interval_seconds = int(Config.get_variable("LATENCY_CHECK_INTERVAL_SECONDS", "60")) # seconds
        self.latency_check_history_length = int(Config.get_variable("LATENCY_CHECK_HISTORY_LENGTH", "100")) # number of entries to keep in history
        self.azkv_required = Config.get_variable("AZKV_REQUIRED", "false").lower() == "true"
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
    
    def perform_latency_check(self, start_time) -> dict:
        """
            healthy: if every latency is below threshold
            unhealthy: if any latency is above threshold
            degraded: if average latency is above threshold
        """
        if not HealthCheckService.latency_check_enabled:
            return {
                "status": "disabled",
                "message": "Latency check is disabled in configuration."
            }
        if not HealthCheckService.latency_history:
            return {
                "status": "unknown",
                "message": "No latency data available yet."
            }

        total_latency = 0
        for entry in HealthCheckService.latency_history:
            if entry["latency_ms"] > HealthCheckService.latency_threshold_ms:
                print(f"Warning: High latency detected - {entry['request_log']} - Latency: {entry['latency_ms']}ms")
            total_latency += entry["latency_ms"]
    
        status = "healthy"
        if any(entry["latency_ms"] > HealthCheckService.latency_threshold_ms for entry in HealthCheckService.latency_history):
            status = "unhealthy"
        elif average_latency > HealthCheckService.latency_threshold_ms:
            status = "degraded"
        average_latency = total_latency / len(HealthCheckService.latency_history) if HealthCheckService.latency_history else 0
    
        return {
            "status": status,
            "average_latency_ms": average_latency
        }
    
    # service health check
    
    def perform_config_health_check(self) -> dict:
        """
        Perform a health check on the configuration service by attempting to retrieve safe variables.
        
        Args:
            config_service: An instance of the Config class to check
            
        Returns:
            A dictionary with the health status and retrieved variables if successful, or an error message if not.
        """
        try:
            safe_variables = config_service.get_all_safe_variables()
            return {
                "status": "healthy"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }   
    def perform_chromadb_health_check(self, chroma_service) -> dict:
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
        
        Args:
            azkv_service: An instance of the AzureKeyVaultService to check
            
        Returns:
            A dictionary with the health status and secret value if successful, or an error message if not.
        """
        try:
            test_secret_name = "healthchecktestsecret"
            test_secret_value = "healthchecktestvalue"
            azkv_service.update_secret(test_secret_name, test_secret_value)
            retrieved_value = azkv_service.get_secret(test_secret_name)
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
    def perform_openvino_health_check(self, openvino_service) -> dict:
        """
        Perform a health check on the OpenVINO service by attempting to run a simple inference.
        
        Args:
            openvino_service: An instance of the OpenVINOService to check
            
        Returns:
            A dictionary with the health status and inference result if successful, or an error message if not.
        """
        try:
            inference_result = openvino_service.run_health_check_inference()
            if inference_result.get("status") == "success":
                return {
                    "status": "healthy",
                    "inference_result": inference_result
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Inference failed"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }
    
    # health check probe that checks everything
    
    def perform_comprehensive_health_check(self): # checks the health of EVERYTHING.
        config_health = self.perform_config_health_check()
        chromadb_health = self.perform_chromadb_health_check()
        azkv_health = self.perform_azure_keyvault_health_check()
        openvino_health = self.perform_openvino_health_check()

        all_health = {
            "config_health": config_health,
            "chromadb_health": chromadb_health,
            "azkv_health": azkv_health,
            "openvino_health": openvino_health
        }

        overall_status = "healthy"
        # if any(health.get("status") != "healthy" for health in all_health.values()):
        #     overall_status = "unhealthy"

        # decide better

        return {
            "status": overall_status,
            "config_health": config_health,
            "chromadb_health": chromadb_health,
            "azure_keyvault_health": azkv_health,
            "openvino_health": openvino_health
        }