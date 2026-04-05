import requests
import sys
import json
from datetime import datetime

class SIPROAPITester:
    def __init__(self, base_url="https://sipro-dev-env.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if 'data' in response_data:
                        print(f"   Response: {type(response_data['data'])} with {len(response_data['data']) if isinstance(response_data['data'], list) else 'object'}")
                except:
                    pass
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text[:200]}")

            return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test login and get token"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION")
        print("="*50)
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@sipro.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            print(f"   Token received: {self.token[:20]}...")
            return True
        return False

    def test_dashboard(self):
        """Test dashboard endpoint - Phase A Foundation"""
        print("\n" + "="*50)
        print("TESTING DASHBOARD - PHASE A FOUNDATION")
        print("="*50)
        
        success, response = self.run_test(
            "Dashboard Data",
            "GET",
            "dashboard",
            200
        )
        
        if success and response.get('data'):
            data = response['data']
            # Check for required Phase A fields
            required_fields = ['lead_stages', 'my_leads', 'unassigned_leads', 'my_appointments']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                print(f"❌ Missing required dashboard fields: {missing_fields}")
                return False
            
            # Check lead_stages structure
            if 'lead_stages' in data:
                stages = data['lead_stages']
                expected_stages = ['acquisition', 'nurturing', 'appointment', 'booking', 'recycle']
                for stage in expected_stages:
                    if stage not in stages:
                        print(f"❌ Missing stage in lead_stages: {stage}")
                        return False
                print(f"✅ Lead stages found: {stages}")
            
            print(f"✅ Dashboard API returns required Phase A fields")
        
        return success

    def test_projects(self):
        """Test projects endpoints"""
        print("\n" + "="*50)
        print("TESTING PROJECTS")
        print("="*50)
        
        # List projects
        success1, response = self.run_test(
            "List Projects",
            "GET",
            "projects",
            200
        )
        
        # Test with search
        success2, _ = self.run_test(
            "Search Projects",
            "GET",
            "projects?search=Grand",
            200
        )
        
        return success1 and success2

    def test_units(self):
        """Test units endpoints"""
        print("\n" + "="*50)
        print("TESTING UNITS")
        print("="*50)
        
        # List units
        success1, response = self.run_test(
            "List Units",
            "GET",
            "units",
            200
        )
        
        # Test with filters
        success2, _ = self.run_test(
            "Filter Units by Status",
            "GET",
            "units?status=available",
            200
        )
        
        return success1 and success2

    def test_leads(self):
        """Test CRM/leads endpoints - Phase A Foundation"""
        print("\n" + "="*50)
        print("TESTING CRM/LEADS - PHASE A FOUNDATION")
        print("="*50)
        
        # List all leads
        success1, response = self.run_test(
            "List All Leads",
            "GET",
            "leads",
            200
        )
        
        # Test stage filtering - key Phase A feature
        success2, acq_response = self.run_test(
            "Filter Leads by Stage: Acquisition",
            "GET",
            "leads?stage=acquisition",
            200
        )
        
        success3, nur_response = self.run_test(
            "Filter Leads by Stage: Nurturing", 
            "GET",
            "leads?stage=nurturing",
            200
        )
        
        success4, apt_response = self.run_test(
            "Filter Leads by Stage: Appointment",
            "GET", 
            "leads?stage=appointment",
            200
        )
        
        success5, bkg_response = self.run_test(
            "Filter Leads by Stage: Booking",
            "GET",
            "leads?stage=booking", 
            200
        )
        
        success6, rec_response = self.run_test(
            "Filter Leads by Stage: Recycle",
            "GET",
            "leads?stage=recycle",
            200
        )
        
        # Test lead pipeline
        success7, pipeline_response = self.run_test(
            "Get Lead Pipeline",
            "GET",
            "leads/pipeline",
            200
        )
        
        if success7 and pipeline_response.get('data'):
            pipeline = pipeline_response['data']
            if 'stages' in pipeline:
                stages = pipeline['stages']
                print(f"✅ Pipeline stages: {stages}")
                # Verify expected stage counts from review request
                expected_counts = {
                    'acquisition': 4, 'nurturing': 4, 'appointment': 4, 
                    'booking': 0, 'recycle': 8
                }
                for stage, expected in expected_counts.items():
                    actual = stages.get(stage, 0)
                    print(f"   {stage}: {actual} (expected: {expected})")
        
        # Create a test lead with stage
        test_lead_data = {
            "name": f"Test Lead {datetime.now().strftime('%H%M%S')}",
            "phone": f"+6281{datetime.now().strftime('%H%M%S')}",
            "email": f"test{datetime.now().strftime('%H%M%S')}@test.com",
            "source": "manual",
            "stage": "acquisition",
            "notes": "Test lead created by automated test"
        }
        
        success8, lead_response = self.run_test(
            "Create Lead with Stage",
            "POST",
            "leads",
            200,
            data=test_lead_data
        )
        
        return all([success1, success2, success3, success4, success5, success6, success7, success8])

    def test_deals(self):
        """Test deals endpoints"""
        print("\n" + "="*50)
        print("TESTING DEALS")
        print("="*50)
        
        # List deals
        success1, response = self.run_test(
            "List Deals",
            "GET",
            "deals",
            200
        )
        
        # Test with filters
        success2, _ = self.run_test(
            "Filter Deals by Status",
            "GET",
            "deals?status=active",
            200
        )
        
        return success1 and success2

    def test_siteplan(self):
        """Test siteplan endpoints"""
        print("\n" + "="*50)
        print("TESTING SITEPLAN")
        print("="*50)
        
        # Get siteplan for first project (assuming proj-001 exists from seed data)
        success1, response = self.run_test(
            "Get Siteplan",
            "GET",
            "siteplan/proj-001",
            200
        )
        
        # Test different view modes
        success2, _ = self.run_test(
            "Siteplan Construction View",
            "GET",
            "siteplan/proj-001?view_mode=construction",
            200
        )
        
        return success1 and success2

    def test_whatsapp(self):
        """Test WhatsApp endpoints (MOCKED)"""
        print("\n" + "="*50)
        print("TESTING WHATSAPP (MOCKED)")
        print("="*50)
        
        # List messages
        success1, response = self.run_test(
            "List WhatsApp Messages",
            "GET",
            "whatsapp/messages",
            200
        )
        
        # Send test message (mocked)
        test_message = {
            "recipient_phone": "+628123456789",
            "recipient_name": "Test User",
            "message": "Test message from automated test",
            "message_type": "notification"
        }
        
        success2, _ = self.run_test(
            "Send WhatsApp Message (MOCKED)",
            "POST",
            "whatsapp/send",
            200,
            data=test_message
        )
        
        return success1 and success2

    def test_dev_report(self):
        """Test development report endpoints"""
        print("\n" + "="*50)
        print("TESTING DEV REPORT")
        print("="*50)
        
        # Get dev report
        success1, response = self.run_test(
            "Get Dev Report",
            "GET",
            "dev-report",
            200
        )
        
        return success1

    def test_lead_import(self):
        """Test lead import functionality"""
        print("\n" + "="*50)
        print("TESTING LEAD IMPORT")
        print("="*50)
        
        # Test lead import
        import_data = {
            "leads": [
                {
                    "name": f"Import Test {datetime.now().strftime('%H%M%S')}",
                    "phone": f"+6281{datetime.now().strftime('%H%M%S')}",
                    "email": f"import{datetime.now().strftime('%H%M%S')}@test.com",
                    "notes": "Imported via automated test"
                }
            ],
            "source": "csv_import",
            "campaign": "Test Campaign"
        }
        
        success, response = self.run_test(
            "Import Leads",
            "POST",
            "leads/import",
            200,
            data=import_data
        )
        
        return success

    def test_finance(self):
        """Test Finance Module APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING FINANCE MODULE (PHASE 2)")
        print("="*50)
        
        # Test finance summary
        success1, response = self.run_test(
            "Finance Summary",
            "GET",
            "finance/summary",
            200
        )
        
        # Test billing schedules
        success2, _ = self.run_test(
            "List Billing Schedules",
            "GET",
            "finance/billing",
            200
        )
        
        # Test payments
        success3, _ = self.run_test(
            "List Payments",
            "GET",
            "finance/payments",
            200
        )
        
        return success1 and success2 and success3

    def test_construction(self):
        """Test Construction Module APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING CONSTRUCTION MODULE (PHASE 2)")
        print("="*50)
        
        # Test construction summary
        success1, response = self.run_test(
            "Construction Summary",
            "GET",
            "construction/summary",
            200
        )
        
        # Test construction units
        success2, _ = self.run_test(
            "List Construction Units",
            "GET",
            "construction/units",
            200
        )
        
        return success1 and success2

    def test_notifications(self):
        """Test Notification Center APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING NOTIFICATION CENTER (PHASE 2)")
        print("="*50)
        
        # Test notifications list
        success1, response = self.run_test(
            "List Notifications",
            "GET",
            "notifications",
            200
        )
        
        # Test auto follow-up rules
        success2, _ = self.run_test(
            "List Auto Follow-Up Rules",
            "GET",
            "notifications/auto-rules",
            200
        )
        
        # Test create notification
        test_notification = {
            "title": "Test Notification",
            "message": "This is a test notification from automated test",
            "type": "info",
            "target_user": "all"
        }
        
        success3, _ = self.run_test(
            "Create Notification",
            "POST",
            "notifications",
            200,
            data=test_notification
        )
        
        return success1 and success2 and success3

    def test_appointments(self):
        """Test Appointment Calendar APIs (Phase 2)"""
        print("\n" + "="*50)
        print("TESTING APPOINTMENT CALENDAR (PHASE 2)")
        print("="*50)
        
        # Test appointments calendar
        current_month = datetime.now().strftime('%Y-%m')
        success1, response = self.run_test(
            "Get Appointment Calendar",
            "GET",
            f"appointments/calendar?month={current_month}",
            200
        )
        
        # Test appointments list
        success2, _ = self.run_test(
            "List Appointments",
            "GET",
            "appointments",
            200
        )
        
        return success1 and success2

def main():
    print("🚀 Starting SIPRO API Testing (Phase 2)...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📋 Testing Phase 1 + Phase 2 features (Finance, Construction, Notifications, Appointments)")
    
    # Setup
    tester = SIPROAPITester()
    
    # Run authentication test first
    if not tester.test_login():
        print("\n❌ Authentication failed, stopping tests")
        return 1

    # Run all API tests
    test_results = []
    test_results.append(("Dashboard", tester.test_dashboard()))
    test_results.append(("Projects", tester.test_projects()))
    test_results.append(("Units", tester.test_units()))
    test_results.append(("CRM/Leads", tester.test_leads()))
    test_results.append(("Deals", tester.test_deals()))
    test_results.append(("Siteplan", tester.test_siteplan()))
    test_results.append(("WhatsApp", tester.test_whatsapp()))
    test_results.append(("Dev Report", tester.test_dev_report()))
    test_results.append(("Lead Import", tester.test_lead_import()))
    
    # Phase 2 Features
    test_results.append(("Finance Module", tester.test_finance()))
    test_results.append(("Construction Module", tester.test_construction()))
    test_results.append(("Notification Center", tester.test_notifications()))
    test_results.append(("Appointment Calendar", tester.test_appointments()))

    # Print final results
    print("\n" + "="*60)
    print("📊 FINAL TEST RESULTS")
    print("="*60)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
    
    print(f"\n📈 Overall: {tester.tests_passed}/{tester.tests_run} tests passed")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 Backend API testing completed successfully!")
        return 0
    else:
        print("⚠️  Some API tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())