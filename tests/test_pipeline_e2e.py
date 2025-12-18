"""End-to-end test pipeline with fake data"""
import asyncio
import httpx
import json
from typing import Dict, Any
from datetime import datetime

# Test configuration
MOCK_SALESFORCE_URL = "http://localhost:8001"
BACKEND_MCP_URL = "http://localhost:8000"


class PipelineTester:
    """Test pipeline for end-to-end testing"""
    
    def __init__(self):
        self.mock_sf_client = httpx.AsyncClient(base_url=MOCK_SALESFORCE_URL, timeout=30.0)
        self.mcp_client = httpx.AsyncClient(base_url=BACKEND_MCP_URL, timeout=30.0)
        self.test_results = []
    
    async def cleanup(self):
        """Cleanup clients"""
        await self.mock_sf_client.aclose()
        await self.mcp_client.aclose()
    
    def log_test(self, test_name: str, status: str, details: Dict[str, Any] = None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    async def test_mock_salesforce_get_record_data(self):
        """Test 1: Mock Salesforce - Get Record Data"""
        test_name = "Mock Salesforce - Get Record Data"
        try:
            # Test with valid record_id
            response = await self.mock_sf_client.post(
                "/mock/salesforce/get-record-data",
                json={"record_id": "001XXXX"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    record_data = data["data"]
                    self.log_test(
                        test_name,
                        "PASS",
                        {
                            "record_id": record_data.get("record_id"),
                            "documents_count": len(record_data.get("documents", [])),
                            "fields_count": len(record_data.get("fields_to_fill", []))
                        }
                    )
                    return record_data
                else:
                    self.log_test(test_name, "FAIL", {"response": data})
                    return None
            else:
                self.log_test(test_name, "FAIL", {"status_code": response.status_code, "response": response.text})
                return None
                
        except Exception as e:
            self.log_test(test_name, "FAIL", {"error": str(e)})
            return None
    
    async def test_mock_apex_send_user_request(self):
        """Test 2: Mock Apex - Send User Request"""
        test_name = "Mock Apex - Send User Request"
        try:
            # Test with new session (session_id = null)
            response = await self.mock_sf_client.post(
                "/mock/apex/send-user-request",
                json={
                    "record_id": "001XXXX",
                    "session_id": None,
                    "user_request": "Remplis tous les champs manquants"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    request_data = data["data"]
                    self.log_test(
                        test_name,
                        "PASS",
                        {
                            "request_id": request_data.get("request_id"),
                            "status": request_data.get("status")
                        }
                    )
                    return request_data
                else:
                    self.log_test(test_name, "FAIL", {"response": data})
                    return None
            else:
                self.log_test(test_name, "FAIL", {"status_code": response.status_code})
                return None
                
        except Exception as e:
            self.log_test(test_name, "FAIL", {"error": str(e)})
            return None
    
    async def test_mcp_receive_request_new_session(self):
        """Test 3: MCP - Receive Request (New Session)"""
        test_name = "MCP - Receive Request (New Session)"
        try:
            response = await self.mcp_client.post(
                "/api/mcp/receive-request",
                json={
                    "record_id": "001XXXX",
                    "session_id": None,
                    "user_message": "Remplis tous les champs manquants"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    workflow_data = data["data"]
                    self.log_test(
                        test_name,
                        "PASS",
                        {
                            "workflow_status": workflow_data.get("status"),
                            "workflow_id": workflow_data.get("workflow_id"),
                            "steps_completed": workflow_data.get("steps_completed", [])
                        }
                    )
                    return workflow_data
                else:
                    self.log_test(test_name, "FAIL", {"response": data})
                    return None
            else:
                self.log_test(test_name, "FAIL", {"status_code": response.status_code, "response": response.text})
                return None
                
        except Exception as e:
            self.log_test(test_name, "FAIL", {"error": str(e)})
            return None
    
    async def test_mcp_receive_request_continuation(self, session_id: str):
        """Test 4: MCP - Receive Request (Continuation)"""
        test_name = "MCP - Receive Request (Continuation)"
        try:
            response = await self.mcp_client.post(
                "/api/mcp/receive-request",
                json={
                    "record_id": "001XXXX",
                    "session_id": session_id,
                    "user_message": "Quel est le montant sur la facture ?"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    workflow_data = data.get("data", {})
                    self.log_test(
                        test_name,
                        "PASS",
                        {
                            "workflow_status": workflow_data.get("status"),
                            "workflow_id": workflow_data.get("workflow_id")
                        }
                    )
                    return workflow_data
                else:
                    self.log_test(test_name, "FAIL", {"response": data})
                    return None
            else:
                self.log_test(test_name, "FAIL", {"status_code": response.status_code})
                return None
                
        except Exception as e:
            self.log_test(test_name, "FAIL", {"error": str(e)})
            return None
    
    async def test_mcp_request_salesforce_data(self):
        """Test 5: MCP - Request Salesforce Data (Internal)"""
        test_name = "MCP - Request Salesforce Data"
        try:
            response = await self.mcp_client.post(
                "/api/mcp/request-salesforce-data",
                json={"record_id": "001XXXX"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    sf_data = data["data"]
                    self.log_test(
                        test_name,
                        "PASS",
                        {
                            "record_id": sf_data.get("record_id"),
                            "documents_count": len(sf_data.get("documents", [])),
                            "fields_count": len(sf_data.get("fields_to_fill", []))
                        }
                    )
                    return sf_data
                else:
                    self.log_test(test_name, "FAIL", {"response": data})
                    return None
            else:
                self.log_test(test_name, "FAIL", {"status_code": response.status_code})
                return None
                
        except Exception as e:
            self.log_test(test_name, "FAIL", {"error": str(e)})
            return None
    
    async def test_task_status_endpoint(self, task_id: str):
        """Test 6: Task Status Endpoint"""
        test_name = "Task Status Endpoint"
        try:
            response = await self.mcp_client.get(f"/api/task-status/{task_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    task_data = data.get("data", {})
                    self.log_test(
                        test_name,
                        "PASS",
                        {
                            "task_id": task_data.get("task_id"),
                            "task_status": task_data.get("status")
                        }
                    )
                    return task_data
                else:
                    self.log_test(test_name, "FAIL", {"response": data})
                    return None
            else:
                self.log_test(test_name, "FAIL", {"status_code": response.status_code})
                return None
                
        except Exception as e:
            self.log_test(test_name, "FAIL", {"error": str(e)})
            return None
    
    async def test_health_endpoints(self):
        """Test 7: Health Check Endpoints"""
        test_name = "Health Check Endpoints"
        try:
            # Test mock-salesforce health
            sf_health = await self.mock_sf_client.get("/health")
            mcp_health = await self.mcp_client.get("/health")
            
            sf_ok = sf_health.status_code == 200
            mcp_ok = mcp_health.status_code == 200
            
            if sf_ok and mcp_ok:
                self.log_test(
                    test_name,
                    "PASS",
                    {
                        "mock_salesforce": sf_health.json(),
                        "backend_mcp": mcp_health.json()
                    }
                )
                return True
            else:
                self.log_test(
                    test_name,
                    "FAIL",
                    {
                        "mock_salesforce_status": sf_health.status_code,
                        "backend_mcp_status": mcp_health.status_code
                    }
                )
                return False
                
        except Exception as e:
            self.log_test(test_name, "FAIL", {"error": str(e)})
            return False
    
    async def run_full_pipeline_test(self):
        """Run complete end-to-end pipeline test"""
        print("=" * 80)
        print("OPTICLAIMS PIPELINE E2E TEST")
        print("=" * 80)
        print()
        
        # Test 1: Health checks
        print("Step 1: Health Checks")
        print("-" * 80)
        await self.test_health_endpoints()
        print()
        
        # Test 2: Mock Salesforce - Get Record Data
        print("Step 2: Mock Salesforce - Get Record Data")
        print("-" * 80)
        record_data = await self.test_mock_salesforce_get_record_data()
        print()
        
        if not record_data:
            print("❌ Cannot continue without record data. Stopping tests.")
            return
        
        # Test 3: Mock Apex - Send User Request
        print("Step 3: Mock Apex - Send User Request")
        print("-" * 80)
        apex_request = await self.test_mock_apex_send_user_request()
        print()
        
        # Test 4: MCP - Request Salesforce Data (Internal)
        print("Step 4: MCP - Request Salesforce Data (Internal)")
        print("-" * 80)
        sf_data = await self.test_mcp_request_salesforce_data()
        print()
        
        # Test 5: MCP - Receive Request (New Session)
        print("Step 5: MCP - Receive Request (New Session)")
        print("-" * 80)
        workflow_result = await self.test_mcp_receive_request_new_session()
        print()
        
        if workflow_result:
            # Extract session_id from workflow if available
            routing_data = workflow_result.get("data", {}).get("routing", {})
            session_id = routing_data.get("session_id") if isinstance(routing_data, dict) else None
            
            # Test 6: MCP - Receive Request (Continuation)
            if session_id:
                print("Step 6: MCP - Receive Request (Continuation)")
                print("-" * 80)
                await self.test_mcp_receive_request_continuation(session_id)
                print()
        
        # Test 7: Task Status (with fake task_id for testing)
        print("Step 7: Task Status Endpoint")
        print("-" * 80)
        fake_task_id = "test-task-12345"
        await self.test_task_status_endpoint(fake_task_id)
        print()
        
        # Summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.test_results if r["status"] == "FAIL")
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print()
        
        if failed_tests > 0:
            print("Failed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result.get('details', {})}")
        
        print()
        print("=" * 80)
        
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "results": self.test_results
        }


async def main():
    """Main test function"""
    tester = PipelineTester()
    
    try:
        results = await tester.run_full_pipeline_test()
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Test results saved to test_results.json")
        
        # Exit with appropriate code
        exit_code = 0 if results["failed"] == 0 else 1
        return exit_code
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

