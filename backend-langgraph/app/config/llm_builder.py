"""LLM Builder with support for OpenAI (Azure) and Anthropic"""
import os
import asyncio
import time
from typing import Optional, Protocol
from abc import ABC, abstractmethod
from dotenv import load_dotenv

import aiohttp
import httpx
from langchain_openai import AzureChatOpenAI
from langchain_anthropic import ChatAnthropic

load_dotenv()


class BaseLLMBuilder(ABC):
    """Base interface for LLM builders"""
    
    @abstractmethod
    def build_llm(self, model: str, **kwargs):
        """Build and return an LLM instance"""
        pass


class AzureOpenAIBuilder(BaseLLMBuilder):
    """Fetch AAD token for Azure OpenAI with caching to prevent throttling."""

    def __init__(
        self,
        token_url: Optional[str] = None,
        scope: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        cache_duration_seconds: int = 3000,  # Cache for 50 minutes (tokens usually last 60)
    ):
        self.token_url = token_url or os.environ.get("AZ_TENANT_TOKEN_URL")
        self.scope = scope or os.environ.get("AZ_SCOPE")
        self.client_id = client_id or os.environ.get("AZ_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("AZ_CLIENT_SECRET")

        if not all([self.token_url, self.scope, self.client_id, self.client_secret]):
            raise ValueError("Missing required Azure AD env vars: AZ_TENANT_TOKEN_URL, AZ_SCOPE, AZ_CLIENT_ID, AZ_CLIENT_SECRET")
        
        # Token cache
        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0
        self._cache_duration = cache_duration_seconds
        self._lock = asyncio.Lock()

    async def fetch_token(self) -> str:
        """Fetch a new token from Azure AD with caching to prevent throttling."""
        async with self._lock:
            # Check if we have a valid cached token
            current_time = time.time()
            if self._cached_token and current_time < self._token_expiry:
                # Return cached token
                print(f"🔑 [LLM Builder] Using cached Azure AD token (expires in {self._token_expiry - current_time:.0f}s)")
                return self._cached_token
            
            # Need to fetch a new token
            print(f"🔑 [LLM Builder] Fetching new Azure AD token at {current_time}")
            print(f"🌐 [LLM Builder] Token URL: {self.token_url}")
            print(f"🎯 [LLM Builder] Scope: {self.scope}")
            print(f"🆔 [LLM Builder] Client ID: {self.client_id[:4]}...")
            
            try:
                async with aiohttp.ClientSession(trust_env=True) as session:
                    data = {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "client_credentials",
                        "scope": self.scope
                    }
                    
                    print(f"📤 [LLM Builder] Sending token request to Azure AD...")
                    start_time = time.time()
                    
                    async with session.post(self.token_url, data=data) as response:
                        request_time = time.time() - start_time
                        print(f"📥 [LLM Builder] Token response received in {request_time:.2f}s (status: {response.status})")
                        
                        if response.status != 200:
                            text = await response.text()
                            print(f"❌ [LLM Builder] Token request failed: {response.status}")
                            print(f"📄 [LLM Builder] Error response: {text}")
                            raise RuntimeError(f"Token request failed with status {response.status}: {text}")
                        
                        token_response = await response.json()
                        access_token = token_response.get("access_token")
                        expires_in = token_response.get("expires_in", 3600)  # Default 1 hour
                        
                        if not access_token:
                            print(f"❌ [LLM Builder] No access_token in response: {token_response}")
                            raise RuntimeError(f"Token endpoint returned no access_token: {token_response}")
                        
                        # Cache the token
                        self._cached_token = access_token
                        # Use min of expires_in and cache_duration for safety
                        cache_time = min(expires_in - 300, self._cache_duration)  # 5 min safety buffer
                        self._token_expiry = current_time + cache_time
                        
                        print(f"✅ [LLM Builder] Token cached until {self._token_expiry} ({cache_time}s)")
                        print(f"🔑 [LLM Builder] Token length: {len(access_token)} chars")
                        
                        return access_token
                        
            except aiohttp.ClientError as e:
                print(f"❌ [LLM Builder] Network error fetching token: {e}")
                print(f"🌐 [LLM Builder] Check network connectivity to Azure AD")
                raise
            except Exception as e:
                print(f"❌ [LLM Builder] Unexpected error fetching token: {e}")
                raise

    def build_llm(self, model: str, **kwargs) -> AzureChatOpenAI:
        """Build a LangChain AzureChatOpenAI bound to this token provider."""
        print(f"🏗️ [LLM Builder] Building AzureChatOpenAI instance...")
        
        endpoint = os.environ.get("AZ_OPENAI_ENDPOINT")
        api_version = os.environ.get("AZ_OPENAI_API_VERSION")

        http_client = httpx.AsyncClient(
            verify=False,
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
        
        print(f"🌐 [LLM Builder] Azure OpenAI Endpoint: {endpoint}")
        print(f"📅 [LLM Builder] API Version: {api_version}")
        print(f"🚀 [LLM Builder] Deployment: {model}")
        
        if not endpoint or not api_version:
            print(f"❌ [LLM Builder] Missing required environment variables:")
            print(f"   - AZ_OPENAI_ENDPOINT: {'✓' if endpoint else '✗'}")
            print(f"   - AZ_OPENAI_API_VERSION: {'✓' if api_version else '✗'}")
            raise ValueError("Missing AZ_OPENAI_ENDPOINT or AZ_OPENAI_API_VERSION")
        if not model:
            print(f"❌ [LLM Builder] model is required")
            raise ValueError("model is required")

        print(f"🔧 [LLM Builder] Additional kwargs: {list(kwargs.keys())}")
        
        try:
            llm = AzureChatOpenAI(
                azure_endpoint=endpoint.rstrip("/"),
                deployment_name=model,   
                api_version=api_version,
                http_async_client=http_client,
                azure_ad_token_provider=self.fetch_token, 
                **kwargs,
            )
            print(f"✅ [LLM Builder] AzureChatOpenAI instance created successfully")
            print(f"🔗 [LLM Builder] Model will use Azure AD token authentication")
            return llm
        except Exception as e:
            print(f"❌ [LLM Builder] Failed to create AzureChatOpenAI: {e}")
            raise


class AnthropicBuilder(BaseLLMBuilder):
    """Builder for Anthropic Claude models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("Missing required Anthropic env var: ANTHROPIC_API_KEY")
        
        print(f"🔑 [Anthropic Builder] Initialized with API key: {self.api_key[:8]}...")

    def build_llm(self, model: str, **kwargs) -> ChatAnthropic:
        """Build a LangChain ChatAnthropic instance."""
        print(f"🏗️ [Anthropic Builder] Building ChatAnthropic instance...")
        print(f"🚀 [Anthropic Builder] Model: {model}")
        
        if not model:
            print(f"❌ [Anthropic Builder] model is required")
            raise ValueError("model is required")

        print(f"🔧 [Anthropic Builder] Additional kwargs: {list(kwargs.keys())}")
        
        try:
            llm = ChatAnthropic(
                model=model,
                api_key=self.api_key,
                **kwargs,
            )
            print(f"✅ [Anthropic Builder] ChatAnthropic instance created successfully")
            return llm
        except Exception as e:
            print(f"❌ [Anthropic Builder] Failed to create ChatAnthropic: {e}")
            raise


class LLMBuilderFactory:
    """Factory for creating LLM builders based on provider type."""
    
    @staticmethod
    def create_builder(provider: str = "openai") -> BaseLLMBuilder:
        """
        Create an LLM builder based on provider type.
        
        Args:
            provider: "openai" or "anthropic"
            
        Returns:
            BaseLLMBuilder instance
        """
        provider_lower = provider.lower()
        
        if provider_lower == "openai":
            print(f"🏭 [LLM Factory] Creating AzureOpenAIBuilder")
            return AzureOpenAIBuilder()
        elif provider_lower == "anthropic":
            print(f"🏭 [LLM Factory] Creating AnthropicBuilder")
            return AnthropicBuilder()
        else:
            raise ValueError(f"Unknown provider: {provider}. Supported: 'openai', 'anthropic'")

