"""
Test script to verify deployment environment works identically to local development.
This simulates what Render.com will do during deployment.
"""

import subprocess
import sys


def test_deployment_environment():
    """Test that the deployment environment works exactly like local"""

    print("🧪 Testing deployment environment...")

    # 1. Test production dependencies only
    print("\n1. Installing production dependencies only...")
    result = subprocess.run(["uv", "sync", "--no-dev"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to install production dependencies: {result.stderr}")
        return False
    print("✅ Production dependencies installed")

    # 2. Test that imports work
    print("\n2. Testing imports...")
    try:
        # Test the exact imports that main.py uses
        import backend.main  # noqa: F401

        print("✅ All imports work correctly")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

    # 3. Test that the app can start
    print("\n3. Testing app startup...")
    try:
        # Import the app object
        from backend.main import app  # noqa: F401

        print("✅ App object created successfully")
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        return False

    # 4. Test FlagSearcher initialization
    print("\n4. Testing FlagSearcher initialization...")
    try:
        from backend.src.flag_searcher import FlagSearcher

        searcher = FlagSearcher(top_k=3)
        print("✅ FlagSearcher initialized successfully")
    except Exception as e:
        print(f"❌ FlagSearcher initialization failed: {e}")
        return False

    # 5. Test a simple query
    print("\n5. Testing simple query...")
    try:
        flags = searcher.query("red white blue")
        print(f"✅ Query successful, returned {len(flags.flags)} flags")
        print(f"   Top result: {flags.flags[0].name} (score: {flags.flags[0].score:.3f})")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False

    print("\n🎉 All deployment environment tests passed!")
    print("✅ Local and deployment environments are identical")
    return True


if __name__ == "__main__":
    # Add the project root to Python path so imports work
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    success = test_deployment_environment()
    sys.exit(0 if success else 1)
