"""
test_email_setup.py - Validation script for email notification setup
Run this to verify everything is working correctly
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

load_dotenv()


def print_header(text):
    """Print formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_section(text):
    """Print section header."""
    print(f"\n📋 {text}\n" + "-" * 50)


def test_imports():
    """Test if all required packages are installed."""
    print_section("Testing Package Imports")

    packages = {
        "dotenv": "python-dotenv",
        "schedule": "schedule",
        "streamlit": "streamlit",
        "flask": "flask (optional for API)",
        "pandas": "pandas",
    }

    all_ok = True
    for package, display_name in packages.items():
        try:
            __import__(package)
            print(f"✅ {display_name}")
        except ImportError:
            print(f"❌ {display_name} - Install with: pip install {package}")
            all_ok = False

    return all_ok


def test_env_file():
    """Test if .env file exists and has required variables."""
    print_section("Testing .env Configuration")

    env_path = Path(".env")

    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Create it: cp .env.example .env")
        return False

    print(f"✅ .env file exists: {env_path}")

    required_vars = [
        ("EMAIL_SENDER", "Sender email address"),
        ("EMAIL_PASSWORD", "SMTP password"),
        ("EMAIL_SMTP_SERVER", "SMTP server"),
        ("EMAIL_SMTP_PORT", "SMTP port"),
    ]

    optional_vars = [
        ("ATTACK_THRESHOLD_PERCENTAGE", "Alert threshold"),
        ("RECEIVER_EMAIL", "Alert recipient"),
        ("WEEKLY_REPORT_DAY", "Weekly report day"),
        ("WEEKLY_REPORT_TIME", "Weekly report time"),
    ]

    all_ok = True

    print("\n📌 Required variables:")
    for var, description in required_vars:
        value = os.getenv(var)
        if value:
            masked = value[: len(value) // 2] + "*" * (len(value) // 2)
            print(f"  ✅ {var:30} = {masked}")
        else:
            print(f"  ❌ {var:30} - NOT SET")
            all_ok = False

    print("\n📌 Optional variables:")
    for var, description in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var:30} = {value}")
        else:
            print(f"  ⚠️  {var:30} - using default")

    return all_ok


def test_email_connection():
    """Test SMTP connection."""
    print_section("Testing Email Connection")

    try:
        from email_notifier import EmailNotifier

        notifier = EmailNotifier()

        if not notifier.configured:
            print("❌ Email notifier not configured properly")
            print("   Check .env file for EMAIL_SENDER and EMAIL_PASSWORD")
            return False

        print(f"Sender: {notifier.sender_email}")
        print(f"SMTP Server: {notifier.smtp_server}:{notifier.smtp_port}")
        print(f"Threshold: {notifier.threshold}%")

        print("\n🧪 Testing SMTP connection...")

        if notifier.test_connection():
            print("✅ Email connection successful!")
            return True
        else:
            print("❌ Email connection failed!")
            return False

    except Exception as e:
        print(f"❌ Error testing email: {str(e)}")
        return False


def test_alerts_file():
    """Test if alerts file can be found/created."""
    print_section("Testing Alerts File")

    alerts_paths = [
        Path("data/outputs/alerts.csv"),
        Path("data/alerts.csv"),
        Path("alerts.csv"),
    ]

    for alerts_path in alerts_paths:
        if alerts_path.exists():
            size = alerts_path.stat().st_size
            print(f"✅ Found alerts file: {alerts_path} ({size} bytes)")
            return True

    print("❌ No alerts.csv found!")
    print("   Run detector first: python src/detector.py")
    print("   Then alerts will be generated at: data/outputs/alerts.csv")
    return False


def test_detector_script():
    """Test if detector.py exists."""
    print_section("Testing Detector Script")

    detector_path = Path("src/detector.py")

    if detector_path.exists():
        print(f"✅ Detector script found: {detector_path}")
        return True
    else:
        print(f"❌ Detector script not found: {detector_path}")
        return False


def test_email_modules():
    """Test if email modules can be imported."""
    print_section("Testing Email Modules")

    modules = [
        ("email_notifier", "Core email functionality"),
        ("email_scheduler", "Scheduler for weekly reports"),
        ("email_server", "Background monitoring server"),
        ("email_api", "Flask REST API (optional)"),
    ]

    all_ok = True
    for module, description in modules:
        try:
            __import__(module)
            print(f"✅ {module:20} - {description}")
        except ImportError as e:
            if module == "email_api":
                print(f"⚠️  {module:20} - {description} (Flask not installed)")
            else:
                print(f"❌ {module:20} - Import failed: {str(e)}")
                all_ok = False

    return all_ok


def test_dashboard():
    """Test if dashboard exists."""
    print_section("Testing Dashboard")

    dashboard_path = Path("dashboard.py")

    if dashboard_path.exists():
        print(f"✅ Dashboard found: {dashboard_path}")
        print("   Run with: streamlit run dashboard.py")
        return True
    else:
        print(f"❌ Dashboard not found: {dashboard_path}")
        return False


def test_directory_structure():
    """Verify directory structure."""
    print_section("Testing Directory Structure")

    dirs = [
        ("src", "Source code directory"),
        ("data", "Data directory"),
        ("data/outputs", "Alert outputs directory"),
        ("docs", "Documentation directory"),
    ]

    all_ok = True
    for directory, description in dirs:
        dir_path = Path(directory)
        if dir_path.exists():
            print(f"✅ {directory:20} - {description}")
        else:
            print(f"❌ {directory:20} - NOT FOUND")
            if directory == "data/outputs":
                print(f"   Create with: mkdir -p {directory}")
                all_ok = False

    return all_ok


def show_next_steps(all_ok):
    """Show next steps based on test results."""
    print_header("Next Steps")

    if not all_ok:
        print("⚠️  Some tests failed. Please fix issues above before proceeding.\n")
        print("Common fixes:")
        print("  1. Install missing packages: pip install -r requirements.txt")
        print("  2. Create .env file: cp .env.example .env")
        print("  3. Fill in email credentials in .env")
        print("  4. Create directories: mkdir -p data/outputs")
        return

    print("✅ All tests passed! Ready to use email notifications.\n")
    print("Quick start:")
    print("  1. Configure email via dashboard:")
    print("     streamlit run dashboard.py")
    print("     → Go to 'Email Settings' tab")
    print("\n  2. Start email server (in background):")
    print("     python src/email_server.py")
    print("\n  3. Run detector to generate alerts:")
    print("     python src/detector.py")
    print("\n  4. Watch for emails!")
    print("\nDocumentation:")
    print("  • Quick start: QUICKSTART_EMAIL.md")
    print("  • Full guide: INTEGRATION_GUIDE.md")
    print("  • Reference: docs/EMAIL_NOTIFICATIONS.md")


def main():
    """Run all tests."""
    print_header("NetPulse-Shield Email Setup Validator")

    results = {
        "Package Imports": test_imports(),
        ".env Configuration": test_env_file(),
        "Detector Script": test_detector_script(),
        "Directory Structure": test_directory_structure(),
        "Email Modules": test_email_modules(),
        "Dashboard": test_dashboard(),
        "Email Connection": test_email_connection(),
        "Alerts File": test_alerts_file(),
    }

    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name}")

    print(f"\nResult: {passed}/{total} tests passed")

    all_ok = all(results.values())

    if all_ok:
        print("🎉 All tests passed!\n")
    else:
        print("⚠️  Some tests failed. See above for details.\n")

    show_next_steps(all_ok)

    print_header("")


if __name__ == "__main__":
    main()
