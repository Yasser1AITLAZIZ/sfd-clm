"""Simplified pipeline test for quick validation"""
import asyncio
import httpx
import json


async def quick_test():
    """Quick test of main endpoints"""
    print("🚀 Quick Pipeline Test\n")
    
    base_mcp = "http://localhost:8000"
    base_mock = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health checks
        print("1. Testing health endpoints...")
        try:
            mcp_health = await client.get(f"{base_mcp}/health", timeout=5.0)
            mock_health = await client.get(f"{base_mock}/health", timeout=5.0)
            
            if mcp_health.status_code == 200 and mock_health.status_code == 200:
                print("   ✅ Both services are healthy\n")
            else:
                print(f"   ❌ Health check failed: MCP={mcp_health.status_code}, Mock={mock_health.status_code}\n")
                return
        except Exception as e:
            print(f"   ❌ Cannot connect to services: {e}\n")
            print("   💡 Make sure both services are running:")
            print("      - Mock Salesforce: uvicorn app.main:app --port 8001")
            print("      - Backend MCP: uvicorn app.main:app --port 8000\n")
            return
        
        # Test 2: Mock Salesforce - Get Record Data
        print("2. Testing Mock Salesforce - Get Record Data...")
        try:
            response = await client.post(
                f"{base_mock}/mock/salesforce/get-record-data",
                json={"record_id": "001XXXX"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    record_data = data.get("data", {})
                    print(f"   ✅ Success: {len(record_data.get('documents', []))} documents, "
                          f"{len(record_data.get('fields_to_fill', []))} fields\n")
                else:
                    print(f"   ❌ Failed: {data}\n")
            else:
                print(f"   ❌ Status code: {response.status_code}\n")
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
        
        # Test 3: Mock Apex - Send User Request
        print("3. Testing Mock Apex - Send User Request...")
        try:
            response = await client.post(
                f"{base_mock}/mock/apex/send-user-request",
                json={
                    "record_id": "001XXXX",
                    "session_id": None,
                    "user_request": "Remplis tous les champs manquants"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    print(f"   ✅ Success: Request ID = {data.get('data', {}).get('request_id', 'N/A')}\n")
                else:
                    print(f"   ❌ Failed: {data}\n")
            else:
                print(f"   ❌ Status code: {response.status_code}\n")
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
        
        # Test 4: MCP - Receive Request (New Session)
        print("4. Testing MCP - Receive Request (New Session)...")
        try:
            response = await client.post(
                f"{base_mcp}/api/mcp/receive-request",
                json={
                    "record_id": "001XXXX",
                    "session_id": None,
                    "user_message": "Remplis tous les champs manquants"
                },
                timeout=30.0
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    workflow = data.get("data", {})
                    print(f"   ✅ Success: Workflow ID = {workflow.get('workflow_id', 'N/A')}, "
                          f"Status = {workflow.get('status', 'N/A')}\n")
                    
                    # Extract session_id for continuation test
                    routing = workflow.get("data", {}).get("routing", {})
                    session_id = routing.get("session_id") if isinstance(routing, dict) else None
                    
                    # Test 5: MCP - Receive Request (Continuation)
                    if session_id:
                        print("5. Testing MCP - Receive Request (Continuation)...")
                        try:
                            response2 = await client.post(
                                f"{base_mcp}/api/mcp/receive-request",
                                json={
                                    "record_id": "001XXXX",
                                    "session_id": session_id,
                                    "user_message": "Quel est le montant sur la facture ?"
                                },
                                timeout=30.0
                            )
                            if response2.status_code == 200:
                                data2 = response2.json()
                                if data2.get("status") == "success":
                                    print(f"   ✅ Success: Continuation workflow completed\n")
                                else:
                                    print(f"   ❌ Failed: {data2}\n")
                            else:
                                print(f"   ❌ Status code: {response2.status_code}\n")
                        except Exception as e:
                            print(f"   ❌ Error: {e}\n")
                    else:
                        print("5. ⚠️  Skipping continuation test (no session_id returned)\n")
                else:
                    print(f"   ❌ Failed: {data}\n")
            else:
                print(f"   ❌ Status code: {response.status_code}\n")
                print(f"   Response: {response.text[:200]}\n")
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
        
        print("✨ Quick test completed!")


if __name__ == "__main__":
    asyncio.run(quick_test())

