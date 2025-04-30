#!/usr/bin/env python3
"""
debug_openai.py - Script to debug OpenAI client initialization
"""

import os
import sys
import inspect
import importlib.util
import traceback

def main():
    """Debug OpenAI client initialization."""
    try:
        # Check Python version
        print(f"Python version: {sys.version}")
        
        # Check if openai is installed
        openai_spec = importlib.util.find_spec("openai")
        if openai_spec:
            print(f"OpenAI is installed at: {openai_spec.origin}")
        else:
            print("OpenAI is not installed")
            return
        
        # Import openai
        import openai
        print(f"OpenAI version: {openai.__version__}")
        
        # Check OpenAI class definition
        print("\nChecking OpenAI class initialization...")
        
        # Get the signature of the OpenAI class constructor
        from openai import OpenAI
        sig = inspect.signature(OpenAI.__init__)
        print(f"OpenAI constructor signature: {sig}")
        
        # Get the parameters
        params = sig.parameters
        for name, param in params.items():
            print(f"  Parameter '{name}': {param.default}")
        
        # Try creating a client with minimal parameters
        print("\nTrying to create OpenAI client...")
        try:
            # Simplest form
            client = OpenAI(api_key="test_key")
            print("Client created successfully using simple approach")
        except Exception as e:
            print(f"Error creating client: {e}")
            traceback.print_exc()
        
        # Check http client config
        print("\nChecking http client configuration...")
        
        # Look for SyncHttpxClientWrapper class
        if hasattr(openai, "_base_client"):
            base_client = openai._base_client
            if hasattr(base_client, "SyncHttpxClientWrapper"):
                wrapper_class = base_client.SyncHttpxClientWrapper
                print(f"Found SyncHttpxClientWrapper: {wrapper_class}")
                
                # Get its signature
                sig = inspect.signature(wrapper_class.__init__)
                print(f"Wrapper constructor signature: {sig}")
                
                # Get the parameters
                params = sig.parameters
                for name, param in params.items():
                    print(f"  Parameter '{name}': {param.default}")
            else:
                print("SyncHttpxClientWrapper not found")
        else:
            print("_base_client not found")
            
        # Check environment variables that might affect proxies
        print("\nChecking environment variables:")
        proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]
        for var in proxy_vars:
            print(f"  {var}: {os.environ.get(var, 'Not set')}")
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 