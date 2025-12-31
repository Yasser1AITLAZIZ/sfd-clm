"""
Quick test script to check endpoint connectivity
Tests the Mock Salesforce endpoint directly
"""

import asyncio
import httpx
import json
from pathlib import Path

async def test_endpoint():
    """Test the endpoint directly"""
    base_url = "http://localhost:8001"
    record_id = "001XX000001"
    
    print("=" * 80)
    print("TESTING MOCK SALESFORCE ENDPOINT CONNECTION")
    print("=" * 80)
    print(f"Base URL: {base_url}")
    print(f"Record ID: {record_id}")
    print()
    
    # Test 1: Health check
    print("Test 1: Health Check")
    print("-" * 80)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/health")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Health check passed: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 2: Get OpenAPI spec
    print("Test 2: Available Routes")
    print("-" * 80)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/openapi.json")
            if response.status_code == 200:
                spec = response.json()
                paths = spec.get("paths", {})
                print(f"✅ Found {len(paths)} endpoints:")
                for path, methods in sorted(paths.items()):
                    method_list = list(methods.keys())
                    print(f"   {', '.join(method_list).upper():6} {path}")
                
                # Check our target
                target = "/mock/salesforce/get-record-data"
                if target in paths:
                    print(f"\n✅ Target endpoint exists: {target}")
                else:
                    print(f"\n❌ Target endpoint NOT found: {target}")
                    print(f"   Similar paths:")
                    for p in paths.keys():
                        if "salesforce" in p.lower() or "record" in p.lower():
                            print(f"      - {p}")
            else:
                print(f"❌ Could not get OpenAPI spec: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Test 3: Try the endpoint
    print("Test 3: Direct Endpoint Test")
    print("-" * 80)
    endpoint_url = f"{base_url}/mock/salesforce/get-record-data"
    print(f"URL: {endpoint_url}")
    print(f"Method: POST")
    print(f"Body: {{'record_id': '{record_id}'}}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                endpoint_url,
                json={"record_id": record_id},
                headers={"Content-Type": "application/json"}
            )
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            try:
                body = response.json()
                print(f"Response: {json.dumps(body, indent=2, ensure_ascii=False)}")
            except:
                print(f"Response text: {response.text[:500]}")
            
            if response.status_code == 200:
                print("\n✅ Endpoint test PASSED")
            else:
                print(f"\n❌ Endpoint test FAILED with status {response.status_code}")
    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
        print("   Service might not be running")
        print("   Try: docker-compose ps")
    except httpx.TimeoutException as e:
        print(f"❌ Timeout error: {e}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
    print()
    
    # Test 4: Try alternative paths
    print("Test 4: Alternative Paths")
    print("-" * 80)
    alternative_paths = [
        "/api/v1/mock/salesforce/get-record-data",
        "/api/mock/salesforce/get-record-data",
        "/v1/mock/salesforce/get-record-data",
        "/salesforce/get-record-data",
        "/get-record-data"
    ]
    
    for alt_path in alternative_paths:
        alt_url = f"{base_url}{alt_path}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    alt_url,
                    json={"record_id": record_id},
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code != 404:
                    print(f"✅ Found at: {alt_path} (status: {response.status_code})")
                    break
        except:
            pass
    else:
        print("❌ None of the alternative paths worked")
    print()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_endpoint())

